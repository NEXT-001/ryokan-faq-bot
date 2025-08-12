"""
完全登録ページ（メールリンクからアクセス）
pages/complete_registration_page.py

メールで受信したリンクから本登録を完了するページ
"""
import streamlit as st
from services.simplified_registration_service import SimplifiedRegistrationService
from services.enhanced_location_service import EnhancedLocationService
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


def complete_registration_page():
    """完全登録ページ（mode=complete_reg&token=xxx）"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    # IPアドレス制限チェック
    is_allowed, message, country_code = check_ip_restriction()
    
    if not is_allowed:
        display_ip_restriction_error()
        return
    
    # URLパラメータからトークンを取得
    token = st.query_params.get("token")
    
    if not token:
        st.error("❌ 無効な登録リンクです。")
        st.markdown("[🔙 登録ページに戻る](?mode=reg)")
        return
    
    # トークンを検証
    is_valid, email = SimplifiedRegistrationService.verify_registration_token(token)
    
    if not is_valid:
        st.error("❌ 登録リンクが無効または期限切れです。")
        st.markdown("登録リンクの有効期限は24時間です。新しい登録リンクをお取りください。")
        st.markdown("[🔙 新規登録](?mode=reg)")
        return
    
    st.title("FAQチャットボットシステム")
    st.subheader("本登録フォーム")
    
    st.success(f"📧 メール認証完了: {email}")
    st.markdown("下記のフォームに必要事項を入力して登録を完了してください。")
    
    # 住所情報を保存するためのセッション変数初期化
    if 'address_info' not in st.session_state:
        st.session_state.address_info = {}
    
    with st.form("complete_registration_form"):
        st.markdown("### 📋 基本情報")
        
        company_name = st.text_input(
            "会社名（チャットボット画面に表示されるので、旅館名などにしてください）", 
            placeholder="例: ○○旅館"
        )
        
        contact_name = st.text_input(
            "担当者名", 
            placeholder="例: 田中太郎"
        )
        
        st.markdown("### 🔒 パスワード設定")
        password = st.text_input(
            "パスワード", 
            type="password", 
            placeholder="8文字以上を推奨",
            help="英数字を含む8文字以上のパスワードを設定してください"
        )
        
        confirm_password = st.text_input(
            "パスワード（確認用）", 
            type="password", 
            placeholder="上記と同じパスワードを入力"
        )
        
        st.markdown("### 📍 会社所在地")
        st.markdown("郵便番号から住所を自動取得できます。")
        
        postal_code = st.text_input(
            "郵便番号", 
            placeholder="例: 123-4567", 
            help="ハイフンありなしどちらでも可"
        )
        
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
        prefecture = st.text_input(
            "都道府県", 
            value=st.session_state.address_info.get('prefecture', ''), 
            placeholder="例: 東京都"
        )
        
        city = st.text_input(
            "市区町村", 
            value=st.session_state.address_info.get('city', ''), 
            placeholder="例: 千代田区"
        )
        
        address = st.text_input(
            "番地・建物名", 
            value=st.session_state.address_info.get('address', ''), 
            placeholder="例: 1-1-1 ○○ビル"
        )
        
        submitted = st.form_submit_button("🚀 登録を完了する", type="primary", use_container_width=True)

    if submitted:
        # 入力値検証
        if not all([company_name, contact_name, password, confirm_password, postal_code]):
            st.warning("⚠️ すべての必須項目を入力してください。")
            return
        
        # 完全登録を実行
        success, message = SimplifiedRegistrationService.complete_registration(
            token=token,
            company_name=company_name,
            name=contact_name,
            password=password,
            confirm_password=confirm_password,
            postal_code=postal_code,
            prefecture=prefecture,
            city=city,
            address=address
        )
        
        if success:
            st.success("🎉 登録が完了しました！")
            st.balloons()
            
            # 成功メッセージから会社IDを抽出
            if "会社ID:" in message:
                company_id = message.split("会社ID: ")[1]
                
                st.markdown("---")
                st.markdown("### 📋 登録完了情報")
                st.markdown(f"**メールアドレス:** {email}")
                st.markdown(f"**会社名:** {company_name}")
                st.markdown(f"**担当者:** {contact_name}")
                st.markdown(f"**会社ID:** `{company_id}`")
                
                if postal_code or prefecture or city or address:
                    st.markdown("### 📍 登録住所")
                    if postal_code:
                        st.markdown(f"**郵便番号:** {postal_code}")
                    if prefecture:
                        st.markdown(f"**都道府県:** {prefecture}")
                    if city:
                        st.markdown(f"**市区町村:** {city}")
                    if address:
                        st.markdown(f"**番地・建物名:** {address}")
                
                st.markdown("---")
                st.markdown("### 🚀 次のステップ")
                st.markdown(f"[📊 管理画面にログイン](?mode=admin&company={company_id})")
                st.markdown(f"[💬 FAQチャットボットを試す](?mode=user&company={company_id})")
            else:
                st.info("💡 管理画面からログインしてFAQの設定を行ってください。")
                
        else:
            st.error(f"❌ {message}")
    
    # フッターリンク
    st.markdown("---")
    st.markdown("### その他")
    st.markdown("[🏠 ホームページ](?)")
    st.markdown("[❓ よくある質問](?mode=user&company=demo-company)")