# login_service.py
import streamlit as st
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime
from services.company_service import (
    load_companies,
    save_companies,
    verify_company_admin,
    add_admin,
    hash_password
)

def hash_password_sqlite(password):
    """SQLite用のパスワードハッシュ化（main.pyと同じ形式）"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(company_id, username, password):
    """
    ユーザーログイン処理（従来の企業ID・ユーザー名方式）
    
    Args:
        company_id (str): 会社ID
        username (str): ユーザー名
        password (str): パスワード
        
    Returns:
        tuple: (成功したかどうか, メッセージ)
    """
    # テストモードの場合はスーパー管理者ログイン
    from config.settings import is_test_mode
    if is_test_mode() and company_id == "admin" and username == "admin" and password == "admin":
        # セッション情報を確実に保存
        st.session_state["is_logged_in"] = True
        st.session_state["is_super_admin"] = True
        st.session_state["company_id"] = None
        st.session_state["company_name"] = "スーパー管理者"
        st.session_state["username"] = username
        # URLパラメータにログイン状態を追加
        st.query_params.logged_in = "true"
        return True, "スーパー管理者としてログインしました"
    
    # 企業管理者の認証
    success, message = verify_company_admin(company_id, username, password)
    
    if success:
        # セッション情報を確実に保存（辞書形式のアクセスを使用）
        st.session_state["is_logged_in"] = True
        st.session_state["is_super_admin"] = False
        st.session_state["company_id"] = company_id  # 会社IDを明示的に保存
        st.session_state["company_name"] = message   # 会社名
        st.session_state["username"] = username
        # URLパラメータにログイン状態を追加
        st.query_params.logged_in = "true"
        return True, f"{message}の管理者としてログインしました"
    
    return False, message

def login_user_by_email(email, password, db_name):
    """
    メールアドレスとパスワードでのログイン処理（SQLiteから認証）
    
    Args:
        email (str): メールアドレス
        password (str): パスワード
        db_name (str): データベースファイルのパス
        
    Returns:
        tuple: (成功したかどうか, メッセージ, 会社ID)
    """
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        
        # メールアドレスとパスワードで検索（認証済みのユーザーのみ）
        c.execute("""
            SELECT company_id, company_name, name, email 
            FROM users 
            WHERE email = ? AND password = ? AND is_verified = 1
        """, (email, hash_password_sqlite(password)))
        
        user = c.fetchone()
        conn.close()
        
        if user:
            company_id, company_name, user_name, user_email = user
            
            # セッション情報を設定
            st.session_state["is_logged_in"] = True
            st.session_state["is_super_admin"] = False
            st.session_state["company_id"] = company_id  # 会社名を会社IDとして使用
            st.session_state["company_name"] = company_name
            st.session_state["username"] = user_name
            st.session_state["user_email"] = user_email
            
            # URLパラメータにログイン状態を追加
            st.query_params.logged_in = "true"
            
            return True, f"{company_name}の管理者として", company_name
        else:
            return False, "メールアドレスまたはパスワードが間違っているか、メール認証が完了していません", None
            
    except Exception as e:
        return False, f"データベースエラー: {e}", None

def logout_user():
    """
    ユーザーログアウト処理
    """
    # セッション情報の削除
    for key in ["is_logged_in", "is_super_admin", "company_id", "company_name", "username", "user_email"]:
        if key in st.session_state:
            del st.session_state[key]
    
    # URLパラメータからログイン状態を削除
    if "logged_in" in st.query_params:
        # 直接削除はできないため、新しいパラメータセットを作成
        current_params = dict(st.query_params)
        if "logged_in" in current_params:
            del current_params["logged_in"]
        # 他のパラメータは維持
        st.query_params.update(**current_params)
    
    return True, "ログアウトしました"

def is_logged_in():
    """
    ログイン状態かどうかを確認
    
    Returns:
        bool: ログイン状態ならTrue
    """
    # 両方のソースからログイン状態を確認
    session_logged_in = "is_logged_in" in st.session_state and st.session_state["is_logged_in"] is True
    param_logged_in = st.query_params.get("logged_in") == "true"
    
    # どちらかがTrueならログイン中と見なす
    return session_logged_in or param_logged_in

def is_super_admin():
    """
    スーパー管理者かどうかを確認
    
    Returns:
        bool: スーパー管理者ならTrue
    """
    return is_logged_in() and "is_super_admin" in st.session_state and st.session_state["is_super_admin"] is True

def get_current_company_id():
    """
    現在ログイン中の会社IDを取得
    
    Returns:
        str: 会社ID
    """
    if is_logged_in():
        # まずcompany_idをチェック
        if "company_id" in st.session_state and st.session_state["company_id"]:
            return st.session_state["company_id"]
        
        # なければselected_companyをチェック
        if "selected_company" in st.session_state:
            # selected_companyの値をcompany_idにも設定して一貫性を保つ
            company_id = st.session_state["selected_company"]
            st.session_state["company_id"] = company_id
            return company_id
    
    # URLパラメータから取得
    current_company = st.query_params.get("company")
    if current_company:
        # 見つかった値をセッションにも保存
        st.session_state["company_id"] = current_company
        return current_company
    
    return None

def admin_management_page():
    """
    管理者アカウント管理ページ（会社管理者用）
    """
    st.header("管理者アカウント管理")
    
    # スーパー管理者の場合は全社表示
    if is_super_admin():
        st.warning("スーパー管理者モードでは、この機能は使用できません")
        return
    
    # 会社情報の取得
    company_id = get_current_company_id()
    if not company_id:
        st.error("会社情報が見つかりません")
        return
    
    companies = load_companies()
    if company_id not in companies:
        st.error("会社情報が見つかりません")
        return
    
    # 管理者一覧を表示
    st.subheader("管理者一覧")
    
    admin_data = []
    for username, admin_info in companies[company_id]["admins"].items():
        admin_data.append({
            "ユーザー名": username,
            "メールアドレス": admin_info.get("email", ""),
            "作成日時": admin_info.get("created_at", "")
        })
    
    if admin_data:
        st.dataframe(pd.DataFrame(admin_data))
    else:
        st.info("管理者アカウントがありません")
    
    # 新規管理者追加フォーム
    st.subheader("新規管理者追加")
    with st.form("add_admin_form"):
        new_username = st.text_input("ユーザー名")
        new_password = st.text_input("パスワード", type="password")
        new_email = st.text_input("メールアドレス")
        submit = st.form_submit_button("管理者を追加")
        
        if submit:
            if not new_username or not new_password:
                st.error("ユーザー名とパスワードを入力してください")
            else:
                success, message = add_admin(company_id, new_username, new_password, new_email)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    
    # 管理者アカウント削除機能
    st.subheader("管理者アカウント削除")
    
    # 自分以外の管理者を取得
    current_username = st.session_state.get("username", "")
    other_admins = [username for username in companies[company_id]["admins"] if username != current_username]
    
    if not other_admins:
        st.info("削除可能な管理者アカウントがありません")
        return
    
    with st.form("delete_admin_form"):
        username_to_delete = st.selectbox(
            "削除する管理者", 
            other_admins
        )
        
        delete_submit = st.form_submit_button("削除")
        
        if delete_submit and username_to_delete:
            # 最後の管理者アカウントは削除できないようにする
            admin_count = len(companies[company_id]["admins"])
            
            if admin_count <= 1:
                st.error("最後の管理者アカウントは削除できません")
            else:
                # 管理者を削除
                del companies[company_id]["admins"][username_to_delete]
                save_companies(companies)
                st.success(f"管理者 '{username_to_delete}' を削除しました")
                st.rerun()