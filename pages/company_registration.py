"""
企業登録ページ（main.py対応版）
pages/company_registration.py
"""
import streamlit as st
import re
from services.company_service import add_company, company_exists_in_db

def validate_email(email):
    """メールアドレスの形式チェック"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_company_id(company_id):
    """企業IDの形式チェック"""
    # 英数字とハイフンのみ、3-20文字
    pattern = r'^[a-zA-Z0-9-]{3,20}$'
    return re.match(pattern, company_id) is not None

def show_registration_form():
    """企業登録フォーム"""
    st.title("🏢 新規企業登録")
    st.markdown("FAQシステムを利用するための企業情報を登録してください")
    
    with st.form("company_registration_form"):
        st.subheader("📝 企業情報")
        
        # 企業ID
        company_id = st.text_input(
            "企業ID *",
            placeholder="例: my-hotel-2024",
            help="英数字とハイフン(-)のみ、3-20文字で入力してください。この IDでログインします。",
            max_chars=20
        )
        
        # 企業名
        company_name = st.text_input(
            "企業名 *",
            placeholder="例: 山田旅館",
            help="正式な企業名を入力してください",
            max_chars=100
        )
        
        st.subheader("👤 管理者情報")
        
        # 管理者ユーザー名
        admin_username = st.text_input(
            "管理者ユーザー名 *",
            placeholder="例: admin",
            help="管理者のユーザー名を設定してください（英数字のみ）",
            max_chars=50
        )
        
        # 管理者メールアドレス
        admin_email = st.text_input(
            "管理者メールアドレス *",
            placeholder="例: admin@my-hotel.com",
            help="管理者のメールアドレスを入力してください",
            max_chars=100
        )
        
        # パスワード
        admin_password = st.text_input(
            "管理者パスワード *",
            type="password",
            help="8文字以上のパスワードを設定してください",
            max_chars=100
        )
        
        # パスワード確認
        password_confirm = st.text_input(
            "パスワード確認 *",
            type="password",
            help="同じパスワードを再度入力してください",
            max_chars=100
        )
        
        # 利用規約
        st.subheader("📋 利用規約")
        
        with st.expander("利用規約を確認する"):
            st.markdown("""
            ### 旅館FAQ自動応答システム 利用規約
            
            **第1条（サービスの提供）**
            - 本システムは、FAQ管理および自動応答機能を提供します
            - サービスの利用は無料です
            
            **第2条（利用者の責任）**
            - 登録情報は正確に入力してください
            - パスワードの管理は利用者の責任です
            - 不正利用は禁止します
            
            **第3条（データの取り扱い）**
            - 登録されたFAQデータは適切に管理されます
            - データの外部への開示は行いません
            - バックアップは定期的に実施されます
            
            **第4条（サービスの変更・停止）**
            - システムの改善のため、予告なく機能を変更することがあります
            - 重大な障害時には一時的にサービスを停止することがあります
            
            **第5条（免責事項）**
            - システムの利用により生じた損害について、運営者は責任を負いません
            - データの消失に備え、定期的なバックアップを推奨します
            """)
        
        agree_terms = st.checkbox("利用規約に同意します *")
        
        # 送信ボタン
        submitted = st.form_submit_button("🏢 企業を登録", type="primary", use_container_width=True)
        
        if submitted:
            # バリデーション
            errors = []
            
            # 必須項目チェック
            if not company_id.strip():
                errors.append("企業IDを入力してください")
            elif not validate_company_id(company_id.strip()):
                errors.append("企業IDは英数字とハイフン(-)のみ、3-20文字で入力してください")
            
            if not company_name.strip():
                errors.append("企業名を入力してください")
            
            if not admin_username.strip():
                errors.append("管理者ユーザー名を入力してください")
            elif not re.match(r'^[a-zA-Z0-9_-]{3,50}$', admin_username.strip()):
                errors.append("管理者ユーザー名は英数字、アンダースコア、ハイフンのみ使用可能です")
            
            if not admin_email.strip():
                errors.append("管理者メールアドレスを入力してください")
            elif not validate_email(admin_email.strip()):
                errors.append("正しいメールアドレス形式で入力してください")
            
            if not admin_password:
                errors.append("管理者パスワードを入力してください")
            elif len(admin_password) < 8:
                errors.append("パスワードは8文字以上で設定してください")
            
            if admin_password != password_confirm:
                errors.append("パスワードと確認用パスワードが一致しません")
            
            if not agree_terms:
                errors.append("利用規約に同意してください")
            
            # エラーがある場合は表示
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
                return
            
            # 企業IDの重複チェック
            try:
                if company_exists_in_db(company_id.strip()):
                    st.error("❌ この企業IDは既に使用されています。別のIDを選択してください。")
                    return
            except Exception as e:
                st.error(f"❌ 企業ID確認エラー: {e}")
                return
            
            # 企業登録実行
            try:
                with st.spinner("🔄 企業を登録中..."):
                    success, message = add_company(
                        company_id=company_id.strip(),
                        company_name=company_name.strip(),
                        admin_username=admin_username.strip(),
                        admin_password=admin_password,
                        admin_email=admin_email.strip()
                    )
                
                if success:
                    st.success("✅ 企業登録が完了しました！")
                    st.success(f"🏢 企業名: {company_name}")
                    st.success(f"🆔 企業ID: {company_id}")
                    st.success(f"👤 管理者: {admin_username}")
                    
                    st.info("📝 登録情報をメモして、管理者ログインページに移動してください")
                    
                    # 登録情報表示
                    with st.expander("📋 登録情報の確認"):
                        st.code(f"""
登録情報:
企業ID: {company_id}
企業名: {company_name}
管理者ユーザー名: {admin_username}
管理者メールアドレス: {admin_email}
                        """)
                    
                    # ログインページへのリンク
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("🔐 管理者ログインに移動", type="primary", use_container_width=True):
                            # セッションに登録情報を保存（ログインフォーム用）
                            st.session_state.registered_company_id = company_id
                            st.session_state.registered_admin_email = admin_email
                            st.session_state.page = "admin_login"
                            st.rerun()
                    
                    with col2:
                        if st.button("🏠 トップページに戻る", use_container_width=True):
                            st.session_state.page = "chat"
                            st.rerun()
                    
                    st.balloons()
                
                else:
                    st.error(f"❌ 企業登録に失敗しました: {message}")
                    
            except Exception as e:
                st.error(f"❌ 登録処理でエラーが発生しました: {str(e)}")

def show_registration_guide():
    """登録ガイド"""
    st.header("📖 登録ガイド")
    
    with st.expander("💡 企業IDについて"):
        st.markdown("""
        **企業IDは以下の条件で設定してください:**
        - 英数字とハイフン(-)のみ使用可能
        - 3文字以上20文字以下
        - 他の企業と重複しないユニークなID
        - ログイン時に使用するため、覚えやすいものを推奨
        
        **例:**
        - `yamada-hotel`
        - `sakura-ryokan-2024`
        - `tokyo-inn`
        """)
    
    with st.expander("🔒 パスワードについて"):
        st.markdown("""
        **セキュアなパスワードの設定を推奨します:**
        - 8文字以上
        - 英数字を組み合わせる
        - 特殊文字(!@#$%など)の使用を推奨
        - 他のサービスと同じパスワードは避ける
        
        **例:**
        - `MyHotel2024!`
        - `Secure@Pass123`
        """)
    
    with st.expander("📧 メールアドレスについて"):
        st.markdown("""
        **管理者メールアドレスは以下の用途で使用されます:**
        - ログイン認証
        - システム通知の受信
        - パスワードリセット（将来実装予定）
        
        **注意点:**
        - 実際に受信可能なメールアドレスを入力してください
        - 企業の代表メールまたは管理者個人のメールを推奨
        """)

def show_demo_info():
    """デモ情報"""
    st.header("🎯 デモ機能のご案内")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏨 デモ企業で体験")
        st.info("""
        **すぐに機能を試したい方は:**
        
        デモ企業のアカウントで
        システムの機能をお試しいただけます
        
        **ログイン情報:**
        - 企業ID: `demo-company`
        - メール: `admin@example.com`
        - パスワード: `admin123`
        """)
        
        if st.button("🔍 デモ企業でFAQ検索を試す", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
        
        if st.button("🔐 デモ管理者でログイン", use_container_width=True):
            st.session_state.page = "admin_login"
            st.rerun()
    
    with col2:
        st.subheader("⭐ 主な機能")
        st.markdown("""
        **FAQ検索機能:**
        - 自然言語での質問に対応
        - リアルタイム検索
        - 検索履歴の保存
        
        **管理者ダッシュボード:**
        - FAQ管理（追加・編集・削除）
        - 一括CSV/Excel登録
        - 検索履歴分析
        - データエクスポート
        
        **企業管理:**
        - マルチテナント対応
        - 管理者認証システム
        - データの分離管理
        """)

def company_registration_page(company_id=None):
    """企業登録ページのメイン関数（main.py用）"""
    # company_idが渡された場合はセッションに保存
    if company_id and 'company_id' not in st.session_state:
        st.session_state.company_id = company_id
    # タブで画面を分割
    tab1, tab2, tab3 = st.tabs(["📝 企業登録", "📖 登録ガイド", "🎯 デモ機能"])
    
    with tab1:
        show_registration_form()
    
    with tab2:
        show_registration_guide()
    
    with tab3:
        show_demo_info()
    
    # フッター
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🏠 トップページに戻る", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
    
    with col2:
        if st.button("🔐 管理者ログイン", use_container_width=True):
            st.session_state.page = "admin_login"
            st.rerun()
    
    with col3:
        if st.button("🔍 FAQ検索を試す", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()

# 後方互換性のため
def main():
    """直接実行時のメイン関数"""
    company_registration_page()

if __name__ == "__main__":
    main()