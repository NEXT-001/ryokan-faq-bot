"""
アプリケーションルーター
core/app_router.py
"""
import streamlit as st
from config.unified_config import UnifiedConfig
from pages.user_page import user_page
from pages.admin_page import admin_page
from pages.registration_page import registration_page
from pages.verify_page import verify_page
from utils.db_utils import cleanup_expired_tokens


def hide_sidebar_navigation():
    """
    Streamlitのデフォルトページナビゲーションを非表示にする
    """
    st.markdown("""
        <style>
            /* サイドバーのページナビゲーションのみを非表示 */
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
            
            /* 最新版対応 - ナビゲーション部分のみ */
            .st-emotion-cache-1cypcdb {display: none !important;}
            .st-emotion-cache-pkbazv {display: none !important;}
            .st-emotion-cache-1rs6os {display: none !important;}
            .st-emotion-cache-16txtl3 {display: none !important;}
        </style>
    """, unsafe_allow_html=True)


def show_debug_info():
    """デバッグ情報を表示する（テストモード時のみ）"""
    if UnifiedConfig.is_test_mode():
        with st.expander("🔧 デバッグ情報"):
            # セッション状態
            st.write("セッション状態:")
            for key, value in st.session_state.items():
                if key not in ["conversation_history"]:
                    st.write(f"- {key}: {value}")
            
            # 環境変数の状態
            st.write("環境変数:")
            st.write(f"- TEST_MODE: {UnifiedConfig.TEST_MODE}")
            st.write(f"- HAS_API_KEYS: {UnifiedConfig.has_api_keys()}")
            
            # モード切替リンク
            test_company = "demo-company"
            st.write("モード切替リンク:")
            st.markdown(f"- [ユーザーモード](?mode=user&company={test_company})")
            st.markdown(f"- [管理者モード](?mode=admin&company={test_company})")
            st.markdown(f"- [登録モード](?mode=reg)")
            
            # セッションリセットボタン
            if st.button("セッションをリセット"):
                # セッションだけクリアして、URLはそのまま
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("セッションをリセットしました。")


def route_application():
    """アプリケーションのルーティングメイン処理"""
    # 期限切れトークンの定期クリーンアップ（アプリ起動時に実行）
    cleanup_expired_tokens()
    
    # URLパラメータを取得
    mode, company_id, url_logged_in = UnifiedConfig.get_url_params()
    
    # ページ設定を動的に調整
    UnifiedConfig.configure_page(mode)
    
    # ページナビゲーションを非表示
    hide_sidebar_navigation()
    
    # セッション状態の初期化
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    # 会社IDをセッションに保存（regモード以外）
    if company_id:
        st.session_state.selected_company = company_id
    
    # URLのログイン状態からセッション状態を復元
    if url_logged_in and "is_logged_in" not in st.session_state:
        st.session_state["is_logged_in"] = True
    
    # データディレクトリを確保
    UnifiedConfig.ensure_data_directory()
    
    # APIキーのロード（エラーハンドリング付き）
    try:
        UnifiedConfig.load_anthropic_client()
    except ValueError as e:
        st.error(f"エラー: {e}")
        st.info("APIキーが設定されていないため、テストモードで実行します")
        # テストモードを有効化
        import os
        os.environ["TEST_MODE"] = "true"
        UnifiedConfig.TEST_MODE = True
    except:
        # APIキーが設定されていない場合はテストモードを有効化
        import os
        os.environ["TEST_MODE"] = "true"
        UnifiedConfig.TEST_MODE = True
    
    # デバッグ情報表示（テストモード時のみ）
    show_debug_info()
    
    # モードに応じた表示
    if mode == "verify":
        # メール認証ページ（tokenパラメータがある場合）
        verify_page()
    elif mode == "reg":
        # 登録ページ
        registration_page()
    elif mode == "admin":
        # 管理者ページ
        admin_page(company_id)
    else:
        # ユーザーページ（デフォルト）
        user_page(company_id)
