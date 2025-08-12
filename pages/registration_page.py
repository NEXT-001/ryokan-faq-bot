"""
シンプル登録ページ（メールアドレスのみ）
pages/registration_page.py
"""
import streamlit as st
from services.simplified_registration_service import SimplifiedRegistrationService
from config.unified_config import UnifiedConfig
from utils.ip_restriction import check_ip_restriction, display_ip_restriction_error


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


def registration_page():
    """登録ページ（mode=reg）- シンプル2ステップ登録版"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    # IPアドレス制限チェック
    is_allowed, message, country_code = check_ip_restriction()
    
    if not is_allowed:
        # アクセスが制限されている場合
        display_ip_restriction_error()
        return
    else:
        # デバッグ情報（開発時のみ表示）
        try:
            if country_code and st.secrets.get("DEBUG_MODE", False):
                st.info(f"🌍 アクセス許可: {country_code}")
        except:
            # secrets.tomlが存在しない場合はスキップ
            pass
    
    st.title("FAQチャットボットシステム")
    st.subheader("14日間無料お試し登録")
    
    st.markdown("""
    ### 🚀 簡単2ステップで登録
    
    **ステップ1:** メールアドレスを入力して登録リンクを受信  
    **ステップ2:** 受信したメールのリンクから詳細情報を入力
    """)
    
    st.markdown("---")
    
    # シンプルなメールアドレス入力フォーム
    with st.form("simple_registration_form"):
        st.markdown("### 📧 メールアドレスを入力してください")
        email = st.text_input(
            "メールアドレス", 
            placeholder="例: tanaka@example.com",
            help="こちらのメールアドレスに本登録用のリンクをお送りします"
        )
        
        submitted = st.form_submit_button("📤 登録リンクを送信", type="primary", use_container_width=True)

    if submitted:
        if email and email.strip():
            # ユーザーのIPアドレスを取得（セッション情報から）
            user_ip = st.session_state.get('user_ip')
            
            # 登録リンクを送信
            success, message = SimplifiedRegistrationService.send_registration_link(email.strip(), user_ip)
            
            if success:
                st.success("✅ 登録リンクをお送りしました！")
                st.info(f"📧 {email} にメールをお送りしました。")
                st.markdown("""
                ### 📝 次のステップ
                1. メールボックスを確認してください
                2. 「本登録はこちらから」のリンクをクリック
                3. 会社情報とパスワードを入力して登録完了
                
                **※ メールが届かない場合は迷惑メールフォルダもご確認ください**  
                **※ 登録リンクは24時間有効です**
                """)
            else:
                st.error(f"❌ {message}")
        else:
            st.warning("📧 メールアドレスを入力してください。")
    
    # 他のページへのリンク
    st.markdown("---")
    st.markdown("### 既にアカウントをお持ちの方")
    st.markdown("[🔐 管理者ログイン](?mode=admin)")
    st.markdown("[💬 FAQチャットボットを試す](?mode=user&company=demo-company)")