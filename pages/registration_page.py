"""
登録ページ
pages/registration_page.py
"""
import streamlit as st
from utils.db_utils import init_db, register_user


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
    """登録ページ（mode=reg）- 会社ID自動生成版"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    st.title("FAQチャットボットシステム")
    st.subheader("14日間無料お試し登録")
    
    # データベース初期化
    init_db()
    
    with st.form("register_form"):
        company = st.text_input("会社名（チャットボット画面に表示されるので、旅館名などにしてください。）", placeholder="例: ○○旅館")
        name = st.text_input("担当者名", placeholder="例: 田中太郎")
        email = st.text_input("メールアドレス", placeholder="例: tanaka@sample.com")
        password = st.text_input("パスワード", type="password", placeholder="8文字以上を推奨")
        
        submitted = st.form_submit_button("登録")

    if submitted:
        if company and name and email and password:
            # パスワードの長さチェック
            if len(password) < 6:
                st.warning("パスワードは6文字以上で入力してください。")
                return
            
            success = register_user(company, name, email, password)
            if success:
                st.success("✅ 仮登録が完了しました。認証メールをご確認ください。")
                st.info("📧 お送りしたメールのリンクをクリックして、登録を完了してください。")
                
                # 登録情報を表示
                st.markdown("---")
                st.markdown("### 📋 登録情報")
                st.markdown(f"**会社名:** {company}")
                st.markdown(f"**担当者:** {name}")
                st.markdown(f"**メールアドレス:** {email}")
                
                st.markdown("---")
                st.markdown("**メールが届かない場合は、迷惑メールフォルダもご確認ください。**")
            else:
                st.error("このメールアドレスは既に登録されているか、システムエラーが発生しました。")
        else:
            st.warning("すべての項目を入力してください。")
    
    # 他のページへのリンク
    st.markdown("---")
    st.markdown("### 既にアカウントをお持ちの方")
    st.markdown("[🔐 管理者ログイン](?mode=admin)")
    st.markdown("[💬 FAQチャットボットを試す](?mode=user&company=demo-company)")