# pages/verification.py - メール認証ページ（デバッグ強化版）
import streamlit as st
from components.ui_utils import hide_entire_sidebar
from core.database import verify_user_token

def debug_token_in_database(token):
    """データベース内のトークンをデバッグ表示"""
    try:
        import sqlite3
        from utils.constants import DB_NAME
        
        print(f"[TOKEN DEBUG] 検索対象トークン: {token}")
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # 全ユーザーのトークン情報を表示
        c.execute("SELECT id, email, verify_token, is_verified, created_at FROM users")
        all_users = c.fetchall()
        
        print(f"[TOKEN DEBUG] データベース内の全ユーザー:")
        for user in all_users:
            user_id, email, db_token, verified, created = user
            print(f"  - ID:{user_id} Email:{email} Verified:{verified}")
            print(f"    Token: {db_token}")
            print(f"    Created: {created}")
            print(f"    Token Match: {db_token == token}")
            print("    ---")
        
        # 完全一致検索
        c.execute("SELECT id, email, verify_token FROM users WHERE verify_token = ?", (token,))
        exact_match = c.fetchone()
        print(f"[TOKEN DEBUG] 完全一致結果: {exact_match}")
        
        # 部分一致検索（トークンの一部で検索）
        if len(token) > 10:
            partial_token = token[:10]
            c.execute("SELECT id, email, verify_token FROM users WHERE verify_token LIKE ?", (f"%{partial_token}%",))
            partial_matches = c.fetchall()
            print(f"[TOKEN DEBUG] 部分一致結果 ({partial_token}): {partial_matches}")
        
        conn.close()
        
    except Exception as e:
        print(f"[TOKEN DEBUG ERROR] {e}")

def verification_page():
    """メール認証ページ（token パラメータ）- デバッグ強化版"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    st.title("📧 メール認証")
    
    # クエリパラメータからトークン取得
    token = st.query_params.get("token")
    
    print(f"[VERIFY PAGE] 受信したトークン: {token}")
    
    if token:
        # デバッグ情報を出力
        debug_token_in_database(token)
        
        # トークン検証
        verified, email = verify_user_token(token)
        
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
                st.query_params.company = "demo-company"
                st.rerun()
                
        else:
            st.error("❌ 認証失敗")
            st.warning("このトークンは無効、または既に認証済みです。")
            
            # デバッグ情報を表示（テストモードの場合）
            try:
                from config.settings import is_test_mode
                if is_test_mode():
                    st.markdown("---")
                    st.markdown("### 🔧 デバッグ情報")
                    st.write(f"受信したトークン: `{token}`")
                    
                    # データベース状態確認ボタン
                    if st.button("データベース内のトークンを確認"):
                        debug_token_in_database(token)
                        st.info("詳細なトークン情報をコンソールに出力しました。")
                        
                        # Streamlit上でも表示
                        import sqlite3
                        from utils.constants import DB_NAME
                        
                        try:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("SELECT email, verify_token, is_verified FROM users ORDER BY created_at DESC LIMIT 5")
                            recent_users = c.fetchall()
                            conn.close()
                            
                            st.write("最近登録されたユーザーのトークン情報:")
                            for user in recent_users:
                                email, db_token, verified = user
                                st.write(f"- {email}: 認証済み={verified}")
                                if db_token:
                                    st.write(f"  トークン: `{db_token}`")
                                    st.write(f"  一致: {db_token == token}")
                                else:
                                    st.write(f"  トークン: なし")
                        except Exception as e:
                            st.error(f"データベース読み込みエラー: {e}")
                        
            except:
                pass
            
            # ホームに戻るボタン
            if st.button("🏠 ホームページに戻る"):
                st.query_params.clear()
                st.rerun()
    else:
        st.warning("⚠️ トークンが見つかりません")
        st.info("メールのリンクが正しいか確認してください。")
        
        # ホームに戻るボタン
        if st.button("🏠 ホームページに戻る"):
            st.query_params.clear()
            st.rerun()