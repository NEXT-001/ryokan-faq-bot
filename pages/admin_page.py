"""
管理者ページ
pages/admin_page.py
"""
import streamlit as st
from services.login_service import is_logged_in, logout_user, is_super_admin
from services.company_service import get_company_name, get_company_list
from admin_faq_management import faq_management_page, faq_preview_page
from line_settings import line_settings_page
from services.login_service import admin_management_page
from services.payment_service import payment_management_page
from services.history_service import show_history
from utils.db_utils import login_user_by_email


def hide_sidebar_navigation():
    """
    Streamlitのデフォルトページナビゲーションを非表示にする
    （管理モードのサイドバーは保持）
    """
    st.markdown("""
        <style>
            /* サイドバーのページナビゲーションのみを非表示（サイドバー自体は保持） */
            .css-1d391kg {display: none !important;}
            .css-17lntkn {display: none !important;}
            .css-pkbazv {display: none !important;}
            
            /* 新しいStreamlitバージョン対応 */
            [data-testid="stSidebarNav"] {display: none !important;}
            [data-testid="stSidebarNavItems"] {display: none !important;}
            [data-testid="stSidebarNavLink"] {display: none !important;}
            
            /* ナビゲーションリンク全般を非表示 */
            div[data-testid="stSidebar"] nav {display: none !important;}
            div[data-testid="stSidebar"] ul {display: none !important;}
            div[data-testid="stSidebar"] li {display: none !important;}
            div[data-testid="stSidebar"] a[href*="main"] {display: none !important;}
            div[data-testid="stSidebar"] a[href*="verify"] {display: none !important;}
            
            /* より具体的なナビゲーション要素のみを非表示 */
            .stSidebar .css-1544g2n {display: none !important;}
            .stSidebar .css-10trblm {display: none !important;}
            
            /* Streamlit最新版のナビゲーション要素 */
            [class*="navigation"] {display: none !important;}
            [class*="nav-link"] {display: none !important;}
            [class*="sidebar-nav"] {display: none !important;}
            
            /* 最新版対応 - ナビゲーション部分のみ */
            .st-emotion-cache-1cypcdb {display: none !important;}
            .st-emotion-cache-pkbazv {display: none !important;}
            .st-emotion-cache-1rs6os {display: none !important;}
            .st-emotion-cache-16txtl3 {display: none !important;}
        </style>
    """, unsafe_allow_html=True)


def admin_page(company_id):
    """管理者ページ（mode=admin）"""
    # サイドバーのページナビゲーションのみを非表示（サイドバー自体は保持）
    hide_sidebar_navigation()
    
    # サイドバーを確実に表示するための設定
    st.markdown("""
        <style>
            /* サイドバー自体は表示する */
            [data-testid="stSidebar"] {
                display: block !important;
            }
            section[data-testid="stSidebar"] {
                display: block !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    try:
        # ログイン状態をチェック
        if not is_logged_in():
            login_page(company_id)
            return
        
        # 管理者ダッシュボードを表示
        admin_dashboard(company_id)
    except Exception as e:
        st.error(f"管理者ページの読み込み中にエラーが発生しました: {e}")
        st.info("必要なモジュールが見つからない可能性があります。")
        
        # 基本的なログイン画面を表示
        st.title("💬 管理者ログイン")
        st.info("システムの一部機能が利用できません。")
        st.markdown(f"[💬 FAQ AIチャットボットに戻る](?mode=user&company={company_id})")


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
        
        admin_submit = st.form_submit_button("ログイン")
        
        if admin_submit:
            # メールアドレスでのログインを優先
            if admin_email and admin_password:
                try:
                    # SQLiteからメールアドレス認証
                    success, message, user_company_id, company_name, user_name, user_email = login_user_by_email(admin_email, admin_password)
                    if success:
                        # セッション情報を設定
                        st.session_state["is_logged_in"] = True
                        st.session_state["is_super_admin"] = False
                        st.session_state["company_id"] = user_company_id
                        st.session_state["company_name"] = company_name
                        st.session_state["username"] = user_name
                        st.session_state["user_email"] = user_email
                        
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
            else:
                st.error("メールアドレスとパスワードを入力してください")
    
    # 他のページへのリンク
    st.markdown("---")
    st.markdown("### その他")
    st.markdown(f"[💬 FAQチャットボットを利用する](?mode=user&company={company_id or 'demo-company'})")
    st.markdown("[📝 新規登録](?mode=reg)")


def admin_dashboard(company_id):
    """管理者ダッシュボード"""
    from config.settings import is_test_mode
    
    try:
        # スーパー管理者かどうかを確認
        is_super = is_super_admin()
        
        # 会社名を取得
        if is_super:
            company_name = "スーパー管理者"
        else:
            company_name = get_company_name(company_id) or "不明な会社"
        
        # タイトル表示
        st.title(f"💬 {company_name} - 管理画面")
        
        # テストモード表示
        if is_test_mode():
            st.info("📝 テストモードで実行中です")
        
        # サイドバーのナビゲーション
        with st.sidebar:
            st.header(f"ようこそ、{st.session_state.get('username', '')}さん")
            
            # メニュー
            if is_super:
                # スーパー管理者メニュー
                admin_page_option = st.radio(
                    "管理メニュー",
                    ["企業管理", "FAQデモ"]
                )
            else:
                # 企業管理者メニュー
                admin_page_option = st.radio(
                    "管理メニュー",
                    ["FAQ管理", "FAQ履歴", "LINE通知設定", "管理者設定", "FAQプレビュー", "決済管理"]
                )
            
            st.markdown("---")
            
            # ログアウト機能
            logout_btn = st.button("ログアウト")
            if logout_btn:
                logout_user()
                
                # ログアウト後はログイン画面に戻る
                st.query_params.mode = "admin"
                st.query_params.company = company_id
                # logged_inパラメータを削除
                if "logged_in" in st.query_params:
                    del st.query_params["logged_in"]
                
                st.success("ログアウトしました。")
                st.rerun()
            
            # ユーザーモードへのリンク
            user_url = f"?mode=user&company={company_id}"
            st.markdown(f"[お客様向けページを表示]({user_url})")
        
        # 選択したページを表示
        if is_super:
            # スーパー管理者ページ
            if admin_page_option == "企業管理":
                super_admin_company_management()
            elif admin_page_option == "FAQデモ":
                # 企業選択
                companies = get_company_list()
                company_options = {company["name"]: company["id"] for company in companies}
                
                selected_company_name = st.selectbox("企業を選択", list(company_options.keys()))
                selected_company_id = company_options[selected_company_name]
                
                # プレビュー表示
                faq_preview_page(selected_company_id)
        else:
            # 企業管理者ページ
            if admin_page_option == "FAQ管理":
                faq_management_page()
            elif admin_page_option == "FAQ履歴":
                show_history(company_id)
            elif admin_page_option == "LINE通知設定":
                line_settings_page(company_id)
            elif admin_page_option == "管理者設定":
                admin_management_page()
            elif admin_page_option == "FAQプレビュー":
                faq_preview_page(company_id)
            elif admin_page_option == "決済管理":
                payment_management_page(company_id)
                
    except Exception as e:
        st.error(f"管理機能の読み込み中にエラーが発生しました: {e}")
        st.markdown(f"[💬 FAQチャットボットに戻る](?mode=user&company={company_id})")


def super_admin_company_management():
    """スーパー管理者の企業管理ページ"""
    import pandas as pd
    from services.company_service import add_company
    
    st.header("企業管理")
    
    try:
        # 企業一覧を表示
        companies = get_company_list()
        
        if companies:
            st.subheader("登録企業一覧")
            
            # 企業データをシンプルに表示
            company_data = []
            for company in companies:
                company_data.append({
                    "ID": company["id"],
                    "名前": company["name"],
                    "管理者数": company["admin_count"],
                    "作成日時": company["created_at"]
                })
            
            # シンプルなデータフレーム表示
            company_df = pd.DataFrame(company_data)
            st.dataframe(company_df)
            
            # 企業切り替え
            st.subheader("企業切り替え")
            
            for company in companies:
                # ログイン状態を維持
                admin_url = f"?mode=admin&company={company['id']}&logged_in=true"
                user_url = f"?mode=user&company={company['id']}"
                st.markdown(f"**{company['name']}**: [管理者として表示]({admin_url}) | [ユーザーとして表示]({user_url})")
        else:
            st.info("登録企業がありません。")
        
        # 新規企業追加フォーム
        st.subheader("新規企業登録")
        with st.form("add_company_form"):
            company_id = st.text_input("企業ID (英数字のみ)")
            company_name = st.text_input("企業名")
            admin_username = st.text_input("管理者ユーザー名")
            admin_password = st.text_input("管理者パスワード", type="password")
            admin_email = st.text_input("管理者メールアドレス")
            
            submit = st.form_submit_button("企業を登録")
            
            if submit:
                if not company_id or not company_name or not admin_username or not admin_password:
                    st.error("すべての必須項目を入力してください。")
                else:
                    # IDが英数字のみかチェック
                    if not company_id.isalnum():
                        st.error("企業IDは英数字のみで入力してください。")
                    else:
                        success, message = add_company(company_id, company_name, admin_username, admin_password, admin_email)
                        if success:
                            st.success(message)
                            # 直接URLを提供してリンクとして表示
                            admin_url = f"?mode=admin&company={company_id}&logged_in=true"
                            st.markdown(f"新しい企業の管理画面を表示するには[ここをクリック]({admin_url})")
                        else:
                            st.error(message)
    except Exception as e:
        st.error(f"企業管理機能でエラーが発生しました: {e}")