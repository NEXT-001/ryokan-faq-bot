"""
ログインサービス（統合認証サービスへのプロキシ）
services/login_service.py

注意: このファイルは後方互換性のために残されています。
新しいコードでは services/auth_service.py を直接使用してください。
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from services.auth_service import AuthService
from services.company_service import load_companies, add_admin
from core.database import update_company_admin_password_in_db, verify_company_admin_exists, get_company_admins_from_db
from utils.auth_utils import hash_password

# 統合認証サービスへの委譲

def login_user_by_email(email, password, db_name=None):
    """後方互換性のためのプロキシ関数（db_nameパラメータは無視）"""
    result = AuthService.login_user_by_email(email, password)
    # 元の戻り値形式に合わせる
    if len(result) == 6:
        success, message, company_id, company_name, user_name, user_email = result
        if success:
            return True, message, company_name
        else:
            return False, message, None
    return False, "認証エラー", None

def logout_user():
    """後方互換性のためのプロキシ関数"""
    return AuthService.logout_user()

def is_logged_in():
    """後方互換性のためのプロキシ関数"""
    return AuthService.is_logged_in()

def is_super_admin():
    """後方互換性のためのプロキシ関数"""
    return AuthService.is_super_admin()

def get_current_company_id():
    """後方互換性のためのプロキシ関数"""
    return AuthService.get_current_company_id()

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
    
    # タブで機能を分ける
    tab1, tab2, tab3 = st.tabs(["会社名変更", "ユーザー名変更", "パスワード変更"])
    
    with tab1:
        # 会社名変更フォーム
        st.subheader("会社名変更")
        
        current_company_name = st.session_state.get('company_name', companies[company_id]["name"])
        st.info(f"現在の会社名: {current_company_name}")
        
        with st.form("change_company_name_form"):
            new_company_name = st.text_input("新しい会社名", value=current_company_name)
            
            change_company_name_submit = st.form_submit_button("会社名を変更")
            
            if change_company_name_submit:
                if not new_company_name:
                    st.error("会社名を入力してください")
                elif new_company_name == current_company_name:
                    st.info("会社名に変更はありません")
                else:
                    try:
                        from core.database import update_company_name_in_db
                        
                        # データベースを更新
                        db_success = update_company_name_in_db(company_id, new_company_name)
                        
                        if db_success:
                            st.session_state["company_name"] = new_company_name
                            st.success(f"会社名を '{new_company_name}' に変更しました")
                            st.rerun()
                        else:
                            st.error("会社名の変更に失敗しました")
                            
                    except Exception as e:
                        st.error(f"会社名変更中にエラーが発生しました: {str(e)}")
    
    with tab2:
        # ユーザー名変更フォーム
        st.subheader("ユーザー名変更")
        
        current_username = st.session_state.get('username', '')
        st.info(f"現在のユーザー名: {current_username}")
        
        with st.form("change_username_form"):
            new_username = st.text_input("新しいユーザー名", value=current_username)
            
            change_username_submit = st.form_submit_button("ユーザー名を変更")
            
            if change_username_submit:
                if not new_username:
                    st.error("ユーザー名を入力してください")
                elif new_username == current_username:
                    st.info("ユーザー名に変更はありません")
                else:
                    try:
                        from core.database import update_username_in_db
                        
                        # データベースを更新
                        db_success = update_username_in_db(company_id, current_username, new_username)
                        
                        if db_success:
                            st.session_state["username"] = new_username
                            st.success(f"ユーザー名を '{new_username}' に変更しました")
                            st.rerun()
                        else:
                            st.error("ユーザー名の変更に失敗しました")
                            
                    except Exception as e:
                        st.error(f"ユーザー名変更中にエラーが発生しました: {str(e)}")
    
    with tab3:
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
                    
                    if db_success:
                        st.success(f"管理者 '{selected_admin}' のパスワードを変更しました")
                        print(f"[ADMIN_PAGE] パスワード変更完了: 成功")
                        st.rerun()
                    else:
                        st.error("パスワード変更に失敗しました")
                        print(f"[ADMIN_PAGE] パスワード変更失敗")
                        
                except Exception as e:
                    print(f"[ADMIN_PAGE] パスワード変更エラー: {str(e)}")
                    import traceback
                    print(f"[ADMIN_PAGE] エラー詳細: {traceback.format_exc()}")
                    st.error(f"パスワード変更中にエラーが発生しました: {str(e)}")
