# pages/registration.py - 登録ページ（フロー修正版）
import streamlit as st
import uuid
import traceback
from components.ui_utils import hide_entire_sidebar
from core.database import init_db, register_user_to_db, delete_user_by_email
from core.company_manager import generate_unique_company_id, create_company_folder_structure, validate_company_id
from services.email_service import send_verification_email

# pages/registration.py の register_user 関数を強化
def register_user(company_name, name, email, password):
    """ユーザーを仮登録（トークン確認強化版）"""
    token = str(uuid.uuid4())
    
    try:
        print(f"[REGISTRATION START] 登録開始")
        print(f"  - 会社名: {company_name}")
        print(f"  - 担当者名: {name}")
        print(f"  - メールアドレス: {email}")
        print(f"  - 生成されたトークン: {token}")
        print(f"  - トークン長: {len(token)}")
        
        # 1. 会社IDを自動生成（改良版）
        company_id = generate_unique_company_id(company_name)
        print(f"[COMPANY ID GENERATED] {company_name} -> {company_id}")
        
        # 2. 会社IDの妥当性チェック
        is_valid, validation_message = validate_company_id(company_id)
        if not is_valid:
            print(f"[COMPANY ID ERROR] {validation_message}")
            return False, f"会社ID生成エラー: {validation_message}", None
        
        # 3. データベースに登録（生成された会社IDを使用）
        print(f"[DATABASE] データベース登録を試行中: company_id={company_id}, token={token}")
        db_result = register_user_to_db(company_id, company_name, name, email, password, token)
        print(f"[DATABASE] 登録結果: {db_result}")
        
        if not db_result:
            print(f"[REGISTRATION ERROR] データベース登録に失敗: {email}")
            return False, "データベース登録に失敗しました。メールアドレスが既に使用されている可能性があります。", None
        
        # 4. データベース登録後の確認
        print(f"[VERIFICATION] データベース登録後の確認中...")
        try:
            import sqlite3
            from utils.constants import DB_NAME
            
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT verify_token FROM users WHERE email = ?", (email,))
            saved_token_result = c.fetchone()
            conn.close()
            
            if saved_token_result:
                saved_token = saved_token_result[0]
                print(f"[VERIFICATION] 保存されたトークン: {saved_token}")
                print(f"[VERIFICATION] トークン一致: {saved_token == token}")
                
                if saved_token != token:
                    print(f"[VERIFICATION ERROR] トークン不一致が検出されました")
                    return False, "データベースへのトークン保存に問題があります。", None
            else:
                print(f"[VERIFICATION ERROR] 登録されたユーザーが見つかりません")
                return False, "ユーザー登録の確認に失敗しました。", None
                
        except Exception as e:
            print(f"[VERIFICATION ERROR] 確認処理でエラー: {e}")
            return False, f"登録確認エラー: {e}", None
        
        # 5. 会社フォルダ構造を作成（生成された会社IDを使用）
        print(f"[FOLDER] フォルダ構造作成を試行中: company_id={company_id}")
        folder_success = create_company_folder_structure(company_id, company_name)
        print(f"[FOLDER] フォルダ作成結果: {folder_success}")
        
        if not folder_success:
            print(f"[WARNING] フォルダ構造の作成に失敗しましたが、登録は継続します")
        
        # 6. メール送信（正しいトークンを使用）
        print(f"[EMAIL] メール送信を試行中: token={token}")
        email_result = send_verification_email(email, token)
        print(f"[EMAIL] メール送信結果: {email_result}")
        
        if email_result:
            print(f"[REGISTRATION SUCCESS] Company: {company_name} ({company_id}), User: {name}, Email: {email}, Token: {token}")
            
            # 最終確認として認証リンクを表示
            from utils.constants import VERIFICATION_URL
            verification_link = f"{VERIFICATION_URL}?token={token}"
            print(f"[REGISTRATION SUCCESS] 認証リンク: {verification_link}")
            
            return True, "登録が完了しました", company_id
        else:
            # メール送信に失敗した場合は登録を削除
            print(f"[EMAIL ERROR] メール送信失敗、登録データを削除中...")
            delete_result = delete_user_by_email(email)
            print(f"[CLEANUP] データ削除結果: {delete_result}")
            return False, "メール送信に失敗しました。しばらく後に再度お試しください。", None
            
    except Exception as e:
        print(f"[REGISTRATION ERROR] 予期しないエラー: {e}")
        print(f"[TRACEBACK] {traceback.format_exc()}")
        return False, f"システムエラーが発生しました: {str(e)}", None
    
def get_preview_company_id(company_name):
    """プレビュー用の会社ID生成（実際の登録では使用しない）"""
    try:
        if not company_name or len(company_name.strip()) == 0:
            return "company_preview"
        
        # 簡易プレビュー（実際の生成とは異なる場合がある）
        import re
        import time
        clean_name = re.sub(r'[^a-zA-Z0-9\-_]', '', company_name.lower())
        if len(clean_name) < 2:
            clean_name = "company"
        
        timestamp = str(int(time.time()))[-6:]
        preview_id = f"{clean_name}_{timestamp}"
        return preview_id
    except:
        return "company_preview"

def registration_page():
    """登録ページ（mode=reg）- フロー修正版"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    st.title("FAQチャットボットシステム")
    st.subheader("14日間無料お試し登録")
    
    # データベース初期化
    print("[DB INIT] データベース初期化中...")
    try:
        init_db()
        print("[DB INIT] データベース初期化完了")
    except Exception as e:
        print(f"[DB INIT ERROR] {e}")
        st.error(f"データベース初期化エラー: {e}")
        return
    
    st.info("📝 会社IDは会社名から自動で生成されます（一意性保証）")
    
    with st.form("register_form"):
        company = st.text_input("会社名", placeholder="例: 株式会社サンプル")
        name = st.text_input("担当者名", placeholder="例: 田中太郎")
        email = st.text_input("メールアドレス", placeholder="例: tanaka@sample.com")
        password = st.text_input("パスワード", type="password", placeholder="8文字以上を推奨")
        
        # 会社ID生成プレビュー（プレビュー専用）
        if company:
            try:
                preview_id = get_preview_company_id(company)
                st.caption(f"💡 生成される会社ID（例）: `{preview_id}` ✅")
                st.caption("※実際の会社IDは登録時に重複チェックを行い決定されます")
            except Exception as e:
                st.caption(f"❌ プレビュー生成エラー: {e}")
        
        submitted = st.form_submit_button("登録")

    if submitted:
        print(f"[FORM SUBMIT] フォーム送信されました")
        print(f"  - company: '{company}'")
        print(f"  - name: '{name}'")
        print(f"  - email: '{email}'")
        print(f"  - password length: {len(password) if password else 0}")
        
        if company and name and email and password:
            # パスワードの長さチェック
            if len(password) < 6:
                st.warning("パスワードは6文字以上で入力してください。")
                return
            
            # 登録処理実行
            with st.spinner("登録処理中..."):
                success, message, actual_company_id = register_user(company, name, email, password)
                
            if success and actual_company_id:
                # 成功時の表示
                st.success("✅ 仮登録が完了しました。認証メールをご確認ください。")
                st.info("📧 お送りしたメールのリンクをクリックして、登録を完了してください。")
                
                # 実際に生成された会社IDを表示
                st.markdown("---")
                st.markdown("### 📋 登録情報")
                st.markdown(f"**会社名:** {company}")
                st.markdown(f"**会社ID:** `{actual_company_id}`")
                st.markdown(f"**担当者:** {name}")
                st.markdown(f"**メールアドレス:** {email}")
                
                # 管理者用情報
                st.markdown("---")
                st.markdown("### 📝 重要な情報")
                st.info(f"""
                **保存してください:**
                - 会社ID: `{actual_company_id}`
                - メールアドレス: {email}
                
                これらの情報はログイン時に必要です。
                """)
                
                # フォルダ作成確認
                import os
                from utils.constants import DATA_DIR
                folder_path = os.path.join(DATA_DIR, actual_company_id)
                if os.path.exists(folder_path):
                    st.success(f"✅ 会社フォルダが作成されました: `{folder_path}`")
                else:
                    st.warning(f"⚠️ 会社フォルダの作成に失敗しました: `{folder_path}`")
                
                st.markdown("---")
                st.markdown("**メールが届かない場合は、迷惑メールフォルダもご確認ください。**")
            else:
                st.error(f"登録に失敗しました: {message}")
                
                # デバッグ情報を表示（テストモードの場合）
                try:
                    from config.settings import is_test_mode
                    if is_test_mode():
                        st.markdown("---")
                        st.markdown("### 🔧 デバッグ情報")
                        st.write("コンソールログを確認してください。詳細なエラー情報が出力されています。")
                        
                        # データベース状態確認ボタン
                        if st.button("データベース状態を確認"):
                            from core.database import check_database_integrity
                            check_database_integrity()
                            st.info("データベース状態をコンソールに出力しました。")
                            
                            # 登録されたユーザー情報を表示
                            from core.database import get_all_registered_users
                            users = get_all_registered_users()
                            if users:
                                st.write("登録済みユーザー:")
                                for user in users:
                                    st.write(f"- ID: {user[0]}, 名前: {user[1]}, メール: {user[3]}")
                except:
                    pass
        else:
            st.warning("すべての項目を入力してください。")
            print(f"[FORM ERROR] 必須項目が未入力")
    
    # 他のページへのリンク
    st.markdown("---")
    st.markdown("### 既にアカウントをお持ちの方")
    st.markdown("[🔐 管理者ログイン](?mode=admin)")
    st.markdown("[💬 FAQチャットボットを試す](?mode=user&company_id={actual_company_id})")

if __name__ == "__main__":
    # テスト実行
    test_names = ["TEST", "株式会社テスト", "ABC Company"]
    for name in test_names:
        company_id = generate_unique_company_id(name)
        print(f"'{name}' -> '{company_id}'")