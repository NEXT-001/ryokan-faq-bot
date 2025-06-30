# core/auth.py - 認証・セッション管理
import streamlit as st
from core.database import authenticate_user_by_email

def login_user_by_email(email, password):
    """
    メールアドレスとパスワードでのログイン処理
    
    Args:
        email (str): メールアドレス
        password (str): パスワード
        
    Returns:
        tuple: (成功したかどうか, メッセージ, 会社ID)
    """
    success, user_data = authenticate_user_by_email(email, password)
    
    if success:
        # セッション情報を設定
        st.session_state["is_logged_in"] = True
        st.session_state["is_super_admin"] = False
        st.session_state["company_id"] = user_data['company_id']
        st.session_state["company_name"] = user_data['company_name']
        st.session_state["username"] = user_data['username']
        st.session_state["user_email"] = user_data['email']
        
        # URLパラメータにログイン状態を追加
        st.query_params.logged_in = "true"
        
        return True, f"{user_data['company_name']}の管理者として", user_data['company_id']
    else:
        return False, "メールアドレスまたはパスワードが間違っているか、メール認証が完了していません", None

def logout_user():
    """ユーザーログアウト処理"""
    # セッション情報の削除
    for key in ["is_logged_in", "is_super_admin", "company_id", "company_name", "username", "user_email"]:
        if key in st.session_state:
            del st.session_state[key]
    
    # URLパラメータからログイン状態を削除
    if "logged_in" in st.query_params:
        current_params = dict(st.query_params)
        if "logged_in" in current_params:
            del current_params["logged_in"]
        st.query_params.update(**current_params)
    
    return True, "ログアウトしました"

def is_logged_in():
    """ログイン状態かどうかを確認"""
    session_logged_in = "is_logged_in" in st.session_state and st.session_state["is_logged_in"] is True
    param_logged_in = st.query_params.get("logged_in") == "true"
    return session_logged_in or param_logged_in

def is_super_admin():
    """スーパー管理者かどうかを確認"""
    return is_logged_in() and "is_super_admin" in st.session_state and st.session_state["is_super_admin"] is True

def get_current_company_id():
    """現在ログイン中の会社IDを取得"""
    if is_logged_in():
        if "company_id" in st.session_state and st.session_state["company_id"]:
            return st.session_state["company_id"]
        
        if "selected_company" in st.session_state:
            company_id = st.session_state["selected_company"]
            st.session_state["company_id"] = company_id
            return company_id
    
    # URLパラメータから取得
    current_company = st.query_params.get("company")
    if current_company:
        st.session_state["company_id"] = current_company
        return current_company
    
    return None