"""
認証システム統一修正
auth_system_fix.py

管理者ページでverify_company_adminを使用するように修正
"""
import os
import time
import shutil

def create_fixed_admin_dashboard():
    """正しい認証システムを使用する管理者ページを作成"""
    
    content = '''"""
修正版管理者ダッシュボード
pages/admin_dashboard.py

正しくverify_company_adminを使用します
"""
import streamlit as st
import pandas as pd
import os
from services.company_service import verify_company_admin, get_company_info
from utils.constants import get_data_path

def admin_page(company_id):
    """管理者ページのメイン関数"""
    
    # セッション状態の初期化
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    if "admin_company_id" not in st.session_state:
        st.session_state.admin_company_id = None
    
    # ログイン状態を確認
    if not st.session_state.admin_logged_in or st.session_state.admin_company_id != company_id:
        show_admin_login(company_id)
    else:
        show_admin_dashboard(company_id)

def show_admin_login(company_id):
    """管理者ログイン画面を表示"""
    
    st.title("🔐 管理者ログイン")
    st.info(f"企業ID: **{company_id}**")
    
    # 重要な注意事項
    st.warning("⚠️ ユーザー名での認証です（メールアドレスではありません）")
    
    with st.container():
        st.subheader("ログイン情報を入力してください")
        
        with st.form("admin_login_form", clear_on_submit=False):
            username = st.text_input(
                "ユーザー名",
                value="admin",  # デフォルト値を設定
                help="管理者のユーザー名（メールアドレスではありません）"
            )
            
            password = st.text_input(
                "パスワード",
                type="password",
                help="管理者のパスワード"
            )
            
            login_submitted = st.form_submit_button(
                "ログイン",
                use_container_width=True,
                type="primary"
            )
            
            if login_submitted:
                # 🔥 重要: verify_company_adminを使用
                handle_admin_login_correct(company_id, username, password)
    
    # デモアカウント情報
    with st.expander("📋 デモアカウント情報", expanded=True):
        st.success("""
        **デモ用ログイン情報:**
        - **企業ID**: demo-company
        - **ユーザー名**: admin
        - **パスワード**: admin123
        
        ⚠️ メールアドレスではありません！
        """)

def handle_admin_login_correct(company_id, username, password):
    """正しい認証システムを使用したログイン処理"""
    
    # 🔥 正しいログメッセージ
    print(f"[ADMIN_LOGIN] 認証開始 - Company: {company_id}, Username: {username}")
    
    if not username or not password:
        st.error("ユーザー名とパスワードを入力してください")
        return
    
    st.info("認証中...")
    
    try:
        # 🔥 重要: verify_company_adminを使用（authenticate_user_by_emailではない）
        success, message = verify_company_admin(company_id, username, password)
        
        print(f"[ADMIN_LOGIN] 認証結果: success={success}, message={message}")
        
        if success:
            # ログイン成功
            st.session_state.admin_logged_in = True
            st.session_state.admin_company_id = company_id
            st.session_state.admin_username = username
            st.session_state.company_name = message
            
            print(f"[ADMIN_LOGIN] ログイン成功: {username} @ {company_id}")
            st.success(f"ログイン成功: {message}")
            st.rerun()
            
        else:
            # ログイン失敗
            print(f"[ADMIN_LOGIN] ログイン失敗: {message}")
            st.error(f"ログイン失敗: {message}")
            
            # 詳細なデバッグ情報
            with st.expander("🔧 詳細情報"):
                st.write("**入力情報:**")
                st.write(f"- 企業ID: `{company_id}`")
                st.write(f"- ユーザー名: `{username}`")
                st.write(f"- パスワード長: {len(password)}")
                st.write(f"- エラー: {message}")
                
                # 設定ファイルの確認
                settings_file = os.path.join(get_data_path(company_id), "settings.json")
                st.write(f"**設定ファイル:** `{settings_file}`")
                st.write(f"**存在:** {os.path.exists(settings_file)}")
                
                if os.path.exists(settings_file):
                    import json
                    try:
                        with open(settings_file, 'r', encoding='utf-8') as f:
                            settings = json.load(f)
                        
                        admins = settings.get('admins', {})
                        st.write(f"**利用可能な管理者:** {list(admins.keys())}")
                        
                    except Exception as e:
                        st.write(f"**設定読み込みエラー:** {e}")
    
    except Exception as e:
        print(f"[ADMIN_LOGIN] エラー: {e}")
        st.error(f"認証エラー: {str(e)}")
        
        import traceback
        with st.expander("🔧 エラー詳細"):
            st.code(traceback.format_exc())

def show_admin_dashboard(company_id):
    """管理者ダッシュボードを表示"""
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        company_name = st.session_state.get("company_name", "不明")
        st.title(f"📊 管理者ダッシュボード")
        st.caption(f"企業: {company_name} | ユーザー: {st.session_state.get('admin_username')}")
    
    with col2:
        if st.button("ログアウト", type="secondary"):
            # セッションクリア
            for key in ["admin_logged_in", "admin_company_id", "admin_username", "company_name"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("ログアウトしました")
            st.rerun()
    
    # ダッシュボードコンテンツ
    st.subheader("📈 概要")
    
    company_info = get_company_info(company_id)
    if company_info:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("FAQ数", company_info.get("faq_count", 0))
        with col2:
            st.metric("管理者数", company_info.get("admin_count", 0))
        with col3:
            st.metric("作成日", company_info.get("created_at", "不明")[:10])
    
    st.success("✅ 正しい認証システム (verify_company_admin) を使用しています")
'''
    
    return content

def apply_fix():
    """修正を適用"""
    
    print("=== 認証システム統一修正 ===")
    
    # バックアップ作成
    admin_file = "pages/admin_dashboard.py"
    if os.path.exists(admin_file):
        backup_file = f"{admin_file}.backup_{int(time.time())}"
        shutil.copy2(admin_file, backup_file)
        print(f"💾 バックアップ作成: {backup_file}")
    
    # 新しいファイルを作成
    new_content = create_fixed_admin_dashboard()
    
    with open(admin_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ {admin_file} を修正しました")
    print(f"\n📝 次のステップ:")
    print(f"1. Streamlitアプリを再起動: streamlit run main.py")
    print(f"2. 管理者ページにアクセス")
    print(f"3. ユーザー名: admin, パスワード: admin123 でログイン")

if __name__ == "__main__":
    apply_fix()