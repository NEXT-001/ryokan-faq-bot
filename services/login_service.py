# login_service.py
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from services.company_service import (
    load_companies,
    save_companies,
    verify_company_admin,
    add_admin
)
from core.database import update_company_admin_password_in_db, verify_company_admin_exists, get_company_admins_from_db
from utils.auth_utils import hash_password

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
    
    # 管理者情報を表示
    st.subheader("管理者情報")
    
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
    
    # パスワード変更フォーム
    st.subheader("パスワード変更")
    
    # 管理者選択（自分も含む）
    admin_list = list(companies[company_id]["admins"].keys())
    
    with st.form("change_password_form"):
        selected_admin = st.selectbox(
            "パスワードを変更する管理者", 
            admin_list
        )
        
        new_password = st.text_input("新しいパスワード", type="password")
        confirm_password = st.text_input("パスワード確認", type="password")
        
        change_password_submit = st.form_submit_button("パスワードを変更")
        
        if change_password_submit:
            if not new_password:
                st.error("新しいパスワードを入力してください")
            elif new_password != confirm_password:
                st.error("パスワードが一致しません")
            else:
                try:
                    print(f"[ADMIN_PAGE] パスワード変更開始")
                    print(f"[ADMIN_PAGE] 会社ID: {company_id}")
                    print(f"[ADMIN_PAGE] 対象管理者: {selected_admin}")
                    print(f"[ADMIN_PAGE] 新しいパスワード長: {len(new_password)}")
                    
                    # データベースの管理者存在確認
                    db_admin_exists = verify_company_admin_exists(company_id)
                    print(f"[ADMIN_PAGE] DB管理者存在確認: {db_admin_exists}")
                    
                    # 変更前のパスワードをハッシュ化してログ出力
                    hashed_new_password = hash_password(new_password)
                    print(f"[ADMIN_PAGE] ハッシュ化されたパスワード: {hashed_new_password[:20]}...")
                    
                    # JSONファイルのパスワードを変更
                    print(f"[ADMIN_PAGE] JSONファイル更新開始")
                    companies[company_id]["admins"][selected_admin]["password"] = hashed_new_password
                    json_success = save_companies(companies)
                    print(f"[ADMIN_PAGE] JSONファイル更新結果: {json_success}")
                    
                    # データベースのパスワードを変更
                    print(f"[ADMIN_PAGE] データベース更新開始")
                    print(f"[ADMIN_PAGE] update_company_admin_password_in_db({company_id}, {new_password[:3]}***)")
                    db_success = update_company_admin_password_in_db(company_id, new_password)
                    print(f"[ADMIN_PAGE] データベース更新結果: {db_success}")
                    
                    # 更新後の確認（デバッグ用）
                    if db_success:
                        print(f"[ADMIN_PAGE] データベース更新後の確認実行")
                        # 更新後の管理者情報を確認
                        updated_admins = get_company_admins_from_db(company_id)
                        print(f"[ADMIN_PAGE] 更新後の管理者数: {len(updated_admins)}")
                        for admin_name, admin_info in updated_admins.items():
                            print(f"[ADMIN_PAGE] 管理者: {admin_name}, パスワード: {admin_info['password'][:20]}...")
                    
                    if json_success and db_success:
                        st.success(f"管理者 '{selected_admin}' のパスワードを変更しました（JSON・DB両方更新完了）")
                        print(f"[ADMIN_PAGE] パスワード変更完了: 両方成功")
                        st.rerun()
                    elif json_success and not db_success:
                        st.warning(f"管理者 '{selected_admin}' のパスワードを変更しました（JSONファイルのみ更新、DB更新に失敗）")
                        print(f"[ADMIN_PAGE] パスワード変更完了: JSONのみ成功")
                        st.rerun()
                    elif not json_success and db_success:
                        st.warning(f"管理者 '{selected_admin}' のパスワードを変更しました（DBのみ更新、JSONファイル更新に失敗）")
                        print(f"[ADMIN_PAGE] パスワード変更完了: DBのみ成功")
                        st.rerun()
                    else:
                        st.error("パスワード変更に失敗しました（JSON・DB両方とも更新失敗）")
                        print(f"[ADMIN_PAGE] パスワード変更失敗: 両方失敗")
                        
                except Exception as e:
                    print(f"[ADMIN_PAGE] パスワード変更エラー: {str(e)}")
                    import traceback
                    print(f"[ADMIN_PAGE] エラー詳細: {traceback.format_exc()}")
                    st.error(f"パスワード変更中にエラーが発生しました: {str(e)}")