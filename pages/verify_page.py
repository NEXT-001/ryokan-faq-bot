"""
メール認証ページ
pages/verify_page.py
"""
import streamlit as st
from utils.db_utils import verify_user_token


def hide_entire_sidebar():
    """サイドバー全体を非表示にする"""
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            .css-1d391kg {
                display: none;
            }
            /* メインコンテンツを全幅に */
            .css-18e3th9 {
                padding-left: 1rem;
            }
            .css-1d391kg {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)


def verify_page():
    """メール認証ページ（token パラメータ）"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    st.title("📧 メール認証")
    
    # クエリパラメータからトークン取得
    token = st.query_params.get("token")
    
    if token:
        verified, company_id, email = verify_user_token(token)
        if verified:
            st.success("✅ 認証完了")
            st.info(f"メールアドレス（{email}）の認証が完了しました！")
            st.markdown("### 次のステップ")
            st.markdown("1. 下記のボタンをクリックしてログイン画面に移動してください")
            
            # ログイン画面へのリンクボタン
            if st.button("🔐 ログイン画面に移動", type="primary"):
                # URLパラメータをクリアしてログイン画面に移動
                st.query_params.clear()
                st.query_params.mode = "admin"
                st.query_params.company = company_id
                # 認証されたメールアドレスをパラメータとして渡す
                st.query_params.verified_email = email
                st.rerun()
                
        else:
            st.error("❌ 認証失敗")
            st.warning("このトークンは無効、または既に認証済みです。")
            
            # ホームに戻るボタン
            if st.button("🏠 FAQチャットボットに戻る"):
                st.query_params.clear()
                st.rerun()
    else:
        st.warning("⚠️ トークンが見つかりません")
        st.info("メールのリンクが正しいか確認してください。")
        
        # ホームに戻るボタン
        if st.button("🏠 FAQチャットボットに戻る"):
            st.query_params.clear()
            st.rerun()