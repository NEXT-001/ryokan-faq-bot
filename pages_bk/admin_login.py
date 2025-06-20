"""
管理者ログイン画面（main.py対応版）
pages/admin_login.py
"""
import streamlit as st
from services.company_service import verify_company_admin_by_email

def show_login_form():
    """ログインフォームを表示"""
    st.title("🔐 管理者ログイン")
    
    # ログインフォーム
    with st.form("admin_login_form"):
        st.subheader("管理者認証")
        
        # 前回登録した企業情報があれば自動入力
        default_company_id = st.session_state.get('registered_company_id', 'demo-company')
        default_email = st.session_state.get('registered_admin_email', 'admin@example.com')
        
        company_id = st.text_input(
            "企業ID:",
            value=default_company_id,
            help="企業IDを入力してください"
        )
        
        email = st.text_input(
            "メールアドレス:",
            value=default_email,
            help="管理者のメールアドレスを入力してください"
        )
        
        password = st.text_input(
            "パスワード:",
            type="password",
            value="admin123" if company_id == "demo-company" else "",
            help="パスワードを入力してください"
        )
        
        submitted = st.form_submit_button("🚪 ログイン", type="primary", use_container_width=True)
        
        if submitted:
            if not company_id or not email or not password:
                st.error("❌ すべての項目を入力してください")
                return
            
            # 認証処理
            print(f"[ADMIN_LOGIN] 認証開始 - Company: {company_id}, Email: {email}")
            
            try:
                success, result = verify_company_admin_by_email(company_id, email, password)
                
                if success:
                    # ログイン成功
                    print(f"[ADMIN_LOGIN] 認証成功 - {result}")
                    
                    # セッション状態を設定
                    st.session_state.admin_logged_in = True
                    st.session_state.company_id = company_id
                    st.session_state.admin_email = email
                    
                    # resultが辞書の場合（メール認証）
                    if isinstance(result, dict):
                        st.session_state.company_name = result.get("company_name", "不明な企業")
                        st.session_state.admin_username = result.get("username", "管理者")
                    else:
                        # resultが文字列の場合（従来の認証）
                        st.session_state.company_name = result
                        st.session_state.admin_username = "管理者"
                    
                    st.success(f"✅ ログインに成功しました！")
                    st.success(f"🏢 企業: {st.session_state.company_name}")
                    
                    # ダッシュボードへリダイレクト
                    st.info("📊 管理者ダッシュボードに移動します...")
                    
                    # ページ遷移
                    if st.button("📊 ダッシュボードに移動", type="primary", use_container_width=True):
                        st.session_state.page = "admin"
                        st.rerun()
                    
                    # 自動リダイレクト
                    st.session_state.page = "admin"
                    st.rerun()
                    
                else:
                    # ログイン失敗
                    print(f"[ADMIN_LOGIN] 認証失敗 - {result}")
                    st.error(f"❌ ログインに失敗しました: {result}")
                    
            except Exception as e:
                print(f"[ADMIN_LOGIN] ログインエラー: {e}")
                st.error(f"❌ ログイン処理でエラーが発生しました: {str(e)}")
    
    # デモ情報
    with st.expander("🔍 デモアカウント情報"):
        st.info("""
        **デモ企業でのテスト用ログイン情報:**
        - 企業ID: `demo-company`
        - メールアドレス: `admin@example.com`
        - パスワード: `admin123`
        """)
    
    # 新規企業登録のリンク
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏢 新規企業登録", use_container_width=True):
            st.session_state.page = "company_registration"
            st.rerun()
    
    with col2:
        if st.button("🏠 トップページに戻る", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()

def admin_login_page(company_id=None):
    """管理者ログインページのメイン関数（main.py用）"""
    # company_idが渡された場合はセッションに保存
    if company_id and 'company_id' not in st.session_state:
        st.session_state.company_id = company_id
    # 既にログインしている場合はダッシュボードにリダイレクト
    if st.session_state.get('admin_logged_in', False):
        st.success("✅ 既にログインしています")
        st.info("📊 管理者ダッシュボードに移動します...")
        
        if st.button("📊 ダッシュボードに移動", type="primary", use_container_width=True):
            st.session_state.page = "admin"
            st.rerun()
        
        # 自動リダイレクト
        st.session_state.page = "admin"
        st.rerun()
    else:
        show_login_form()

# 後方互換性のため
def main():
    """直接実行時のメイン関数"""
    admin_login_page()

if __name__ == "__main__":
    main()