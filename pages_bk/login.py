# pages/login.py - ログインページ
import streamlit as st
from core.auth import login_user_by_email, is_logged_in
from services.login_service import login_user
from services.company_service import get_company_name

def login_page(company_id):
    """ログインページ"""
    st.title("💬 FAQ AIチャットボット - ログイン")
    
    # 会社名を表示
    try:
        company_name = get_company_name(company_id)
        if company_name:
            st.header(f"企業: {company_name}")
    except:
        pass
    
    # ログインフォーム（メールアドレス認証用に修正）
    with st.form("admin_login_form"):
        st.subheader("管理者ログイン")
        
        # メールアドレス欄を追加
        admin_email = st.text_input("メールアドレス", placeholder="example@company.com")
        admin_password = st.text_input("パスワード", type="password")
        
        # 既存の企業管理者ログイン用のオプション（折りたたみ式で提供）
        with st.expander("従来の企業ID・ユーザー名でのログイン"):
            admin_company_id = st.text_input("企業ID", value=company_id or '')
            admin_username = st.text_input("ユーザー名")
            st.caption("※ 従来の管理者アカウントでログインする場合にご利用ください")
        
        admin_submit = st.form_submit_button("ログイン")
        
        if admin_submit:
            # メールアドレスでのログインを優先
            if admin_email and admin_password:
                try:
                    # SQLiteからメールアドレス認証
                    success, message, user_company_id = login_user_by_email(admin_email, admin_password)
                    if success:
                        st.success(f"{message} ログインしました。")
                        
                        # URLパラメータを更新してページを再読み込み
                        st.query_params.mode = "admin"
                        st.query_params.company = user_company_id
                        st.query_params.logged_in = "true"
                        
                        st.success("管理者ページに移動しています...")
                        st.rerun()
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"ログイン処理でエラーが発生しました: {e}")
            
            # 従来の企業ID・ユーザー名でのログイン
            elif admin_company_id and admin_username and admin_password:
                try:
                    # 従来のログイン処理
                    success, message = login_user(admin_company_id, admin_username, admin_password)
                    if success:
                        st.success(f"{message} ログインしました。")
                        
                        # URLパラメータを更新してページを再読み込み
                        st.query_params.mode = "admin"
                        st.query_params.company = admin_company_id
                        st.query_params.logged_in = "true"
                        
                        st.success("管理者ページに移動しています...")
                        st.rerun()
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"ログイン処理でエラーが発生しました: {e}")
            else:
                st.error("メールアドレスとパスワード、または企業ID・ユーザー名・パスワードを入力してください")
    
    # 他のページへのリンク
    st.markdown("---")
    st.markdown("### その他")
    st.markdown(f"[💬 FAQチャットボットを利用する](?mode=user&company_id={company_id or 'demo-company'})")
    st.markdown("[📝 新規登録](?mode=reg)")