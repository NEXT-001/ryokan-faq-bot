import streamlit as st
import os
import json
import hashlib
import pandas as pd
from datetime import datetime

# ユーザー情報ファイルのパス
USERS_FILE = "data/users.json"

def hash_password(password):
    """パスワードをハッシュ化する"""
    return hashlib.sha256(password.encode()).hexdigest()

def load_users():
    """ユーザー情報を読み込む"""
    if not os.path.exists("data"):
        os.makedirs("data")
    
    if not os.path.exists(USERS_FILE):
        # デフォルト管理者アカウントを作成
        default_admin = {
            "admin": {
                "password": hash_password("admin123"),
                "role": "admin",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        }
        with open(USERS_FILE, 'w') as f:
            json.dump(default_admin, f)
    
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    """ユーザー情報を保存する"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def add_user(username, password, role="admin"):
    """新しいユーザーを追加する（管理者のみ追加可能）"""
    users = load_users()
    
    if username in users:
        return False, "このユーザー名は既に使用されています"
    
    users[username] = {
        "password": hash_password(password),
        "role": role,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    save_users(users)
    return True, "ユーザーを追加しました"

def verify_user(username, password):
    """ユーザーの認証を行う"""
    users = load_users()
    
    if username not in users:
        return False, "ユーザー名が見つかりません"
    
    if users[username]["password"] != hash_password(password):
        return False, "パスワードが間違っています"
    
    return True, users[username]["role"]

def is_admin():
    """現在のユーザーが管理者かどうかを確認する"""
    if "user_role" in st.session_state:
        return st.session_state.user_role == "admin"
    return False

def user_management_page():
    """ユーザー管理ページを表示する（管理者のみ）"""
    if not is_admin():
        st.warning("この機能にアクセスする権限がありません")
        return
    
    st.header("管理者アカウント管理")
    
    # ユーザー一覧を表示
    users = load_users()
    user_data = []
    for username, details in users.items():
        if details["role"] == "admin":  # 管理者のみ表示
            user_data.append({
                "ユーザー名": username,
                "作成日時": details["created_at"]
            })
    
    if user_data:
        st.dataframe(pd.DataFrame(user_data))
    else:
        st.info("管理者アカウントがありません")
    
    # 新規管理者追加フォーム
    st.subheader("新規管理者追加")
    with st.form("add_user_form"):
        new_username = st.text_input("ユーザー名")
        new_password = st.text_input("パスワード", type="password")
        submit = st.form_submit_button("管理者を追加")
        
        if submit:
            if not new_username or not new_password:
                st.error("ユーザー名とパスワードを入力してください")
            else:
                success, message = add_user(new_username, new_password, "admin")
                if success:
                    st.success(message)
                else:
                    st.error(message)
    
    # 管理者アカウント削除機能
    st.subheader("管理者アカウント削除")
    with st.form("delete_user_form"):
        username_to_delete = st.selectbox(
            "削除するユーザー", 
            [username for username, details in users.items() 
             if details["role"] == "admin" and username != st.session_state.username]
        )
        
        delete_submit = st.form_submit_button("削除")
        
        if delete_submit and username_to_delete:
            # 最後の管理者アカウントは削除できないようにする
            admin_count = sum(1 for details in users.values() if details["role"] == "admin")
            
            if admin_count <= 1:
                st.error("最後の管理者アカウントは削除できません")
            else:
                del users[username_to_delete]
                save_users(users)
                st.success(f"ユーザー '{username_to_delete}' を削除しました")
                st.rerun()