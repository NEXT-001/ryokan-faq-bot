"""
登録ページ
pages/registration_page.py
"""
import streamlit as st
from utils.db_utils import init_db, register_user
from services.enhanced_location_service import EnhancedLocationService


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
    
    # 住所情報を保存するためのセッション変数初期化
    if 'address_info' not in st.session_state:
        st.session_state.address_info = {}
    
    with st.form("register_form"):
        company = st.text_input("会社名（チャットボット画面に表示されるので、旅館名などにしてください。）", placeholder="例: ○○旅館")
        name = st.text_input("担当者名", placeholder="例: 田中太郎")
        email = st.text_input("メールアドレス", placeholder="例: tanaka@sample.com")
        password = st.text_input("パスワード", type="password", placeholder="8文字以上を推奨")
        
        # 郵便番号と住所情報
        st.markdown("### 📍 会社所在地")
        postal_code = st.text_input("郵便番号", placeholder="例: 100-0001", help="ハイフンありなしどちらでも可")
        
        # 郵便番号から住所自動取得ボタン
        if st.form_submit_button("📍 郵便番号から住所を取得", type="secondary"):
            if postal_code:
                location_service = EnhancedLocationService()
                address_data = location_service.get_address_from_postal_code(postal_code)
                if address_data:
                    st.session_state.address_info = address_data
                    st.success(f"住所を取得しました: {address_data.get('prefecture', '')} {address_data.get('city', '')} {address_data.get('address', '')}")
                else:
                    st.error("郵便番号から住所を取得できませんでした。手動で入力してください。")
            else:
                st.warning("郵便番号を入力してください。")
        
        # 住所情報表示（自動取得または手動入力）
        prefecture = st.text_input("都道府県", value=st.session_state.address_info.get('prefecture', ''), placeholder="例: 東京都")
        city = st.text_input("市区町村", value=st.session_state.address_info.get('city', ''), placeholder="例: 千代田区")
        address = st.text_input("番地・建物名", value=st.session_state.address_info.get('address', ''), placeholder="例: 1-1-1 ○○ビル")
        
        submitted = st.form_submit_button("登録")

    if submitted:
        if company and name and email and password:
            # パスワードの長さチェック
            if len(password) < 6:
                st.warning("パスワードは6文字以上で入力してください。")
                return
            
            # 住所情報をまとめる
            location_info = {
                'postal_code': postal_code,
                'prefecture': prefecture,
                'city': city,
                'address': address
            }
            
            success = register_user(company, name, email, password, location_info)
            if success:
                st.success("✅ 仮登録が完了しました。認証メールをご確認ください。")
                st.info("📧 お送りしたメールのリンクをクリックして、登録を完了してください。")
                
                # 登録情報を表示
                st.markdown("---")
                st.markdown("### 📋 登録情報")
                st.markdown(f"**会社名:** {company}")
                st.markdown(f"**担当者:** {name}")
                st.markdown(f"**メールアドレス:** {email}")
                
                # 住所情報も表示
                if postal_code or prefecture or city or address:
                    st.markdown("### 📍 会社所在地")
                    if postal_code:
                        st.markdown(f"**郵便番号:** {postal_code}")
                    if prefecture:
                        st.markdown(f"**都道府県:** {prefecture}")
                    if city:
                        st.markdown(f"**市区町村:** {city}")
                    if address:
                        st.markdown(f"**番地・建物名:** {address}")
                
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