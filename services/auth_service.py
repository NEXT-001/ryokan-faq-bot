"""
統合認証サービス
services/auth_service.py

ログイン、認証、ユーザー管理の統合モジュール
"""
import streamlit as st
import sqlite3
import smtplib
import uuid
import os
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from utils.auth_utils import hash_password
from core.database import (
    get_db_path, authenticate_user_by_email, register_user_to_db,
    delete_user_by_email, get_company_admins_from_db, company_exists_in_db,
    get_company_from_db
)
from services.company_service import verify_company_admin
from utils.company_utils import generate_company_id, create_company_folder_structure
from config.unified_config import UnifiedConfig


class AuthService:
    """統合認証サービスクラス"""
    
    @staticmethod
    def login_user_traditional(company_id, username, password):
        """
        従来の企業ID・ユーザー名方式でのログイン
        
        Args:
            company_id (str): 会社ID
            username (str): ユーザー名
            password (str): パスワード
            
        Returns:
            tuple: (成功したかどうか, メッセージ)
        """
        # テストモードの場合はスーパー管理者ログイン
        from config.unified_config import UnifiedConfig
        if UnifiedConfig.is_test_mode() and company_id == "admin" and username == "admin" and password == "admin":
            AuthService._set_session_data(
                is_logged_in=True,
                is_super_admin=True,
                company_id=None,
                company_name="スーパー管理者",
                username=username
            )
            return True, "スーパー管理者としてログインしました"
        
        # 企業管理者の認証
        success, message = verify_company_admin(company_id, username, password)
        
        if success:
            AuthService._set_session_data(
                is_logged_in=True,
                is_super_admin=False,
                company_id=company_id,
                company_name=message,
                username=username
            )
            return True, f"{message}の管理者としてログインしました"
        
        return False, message

    @staticmethod
    def login_user_by_email(email, password):
        """
        メールアドレスとパスワードでのログイン
        
        Args:
            email (str): メールアドレス
            password (str): パスワード
            
        Returns:
            tuple: (成功したかどうか, メッセージ, 会社ID, 会社名, ユーザー名, メールアドレス)
        """
        try:
            print(f"[AUTH_SERVICE] ログイン試行: {email}")
            
            # データベースから認証
            success, user_data = authenticate_user_by_email(email, password)
            
            if success:
                company_id = user_data["company_id"]
                company_name = user_data["company_name"]
                user_name = user_data["name"]
                user_email = user_data["email"]
                
                # セッション情報を設定
                AuthService._set_session_data(
                    is_logged_in=True,
                    is_super_admin=False,
                    company_id=company_id,
                    company_name=company_name,
                    username=user_name,
                    user_email=user_email
                )
                
                print(f"[AUTH_SERVICE] ログイン成功: {company_name} - {user_name}")
                return True, f"{company_name}の管理者として", company_id, company_name, user_name, user_email
            else:
                print(f"[AUTH_SERVICE] ログイン失敗: {email}")
                return False, "メールアドレスまたはパスワードが間違っているか、メール認証が完了していません", None, None, None, None
                
        except Exception as e:
            print(f"[AUTH_SERVICE] ログインエラー: {e}")
            return False, f"認証エラー: {e}", None, None, None, None

    @staticmethod
    def register_user(company_name, name, email, password, location_info=None):
        """
        ユーザーを仮登録
        
        Args:
            company_name (str): 会社名
            name (str): ユーザー名
            email (str): メールアドレス
            password (str): パスワード
            location_info (dict): 住所情報（postal_code, prefecture, city, address）
            
        Returns:
            bool: 登録成功したかどうか
        """
        try:
            # 1. 会社IDを自動生成
            company_id = generate_company_id(company_name)
            print(f"[AUTH_SERVICE] 会社ID生成: {company_name} -> {company_id}")
            
            # 2. 認証トークンを生成
            token = str(uuid.uuid4())
            
            # 3. データベースに仮登録
            db_name = get_db_path()
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            
            # テーブル構造を確認
            c.execute("PRAGMA table_info(users)")
            columns_info = c.fetchall()
            existing_columns = [column[1] for column in columns_info]
            
            # 必要なカラムが存在するかチェック
            required_columns = ['company_id', 'company_name', 'verify_token']
            missing_columns = [col for col in required_columns if col not in existing_columns]
            
            if missing_columns:
                print(f"[AUTH_SERVICE] 不足カラム: {missing_columns}")
                conn.close()
                # データベースを再初期化
                from core.database import initialize_database
                initialize_database()
                # 再接続
                conn = sqlite3.connect(db_name)
                c = conn.cursor()
            
            # 登録処理を実行
            c.execute("""
                INSERT INTO users (company_id, company_name, name, email, password, created_at, is_verified, verify_token) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (company_id, company_name, name, email, hash_password(password), 
                  datetime.now().isoformat(), 0, token))
            
            conn.commit()
            conn.close()
            
            # 4. 会社フォルダ構造を作成
            folder_success = create_company_folder_structure(company_id, company_name, password, email, location_info)
            if not folder_success:
                print(f"[AUTH_SERVICE] フォルダ構造作成失敗（登録は継続）")
            
            # 5. メール送信
            if AuthService._send_verification_email(email, token):
                print(f"[AUTH_SERVICE] 登録成功: {company_name} ({company_id}) - {name}")
                return True
            else:
                # メール送信失敗時は登録を削除
                conn = sqlite3.connect(db_name)
                c = conn.cursor()
                c.execute("DELETE FROM users WHERE email = ?", (email,))
                conn.commit()
                conn.close()
                return False
                
        except sqlite3.IntegrityError:
            print(f"[AUTH_SERVICE] メールアドレス重複: {email}")
            return False
        except Exception as e:
            print(f"[AUTH_SERVICE] 登録エラー: {e}")
            return False

    @staticmethod
    def verify_user_token(token):
        """
        メール認証トークンを検証
        
        Args:
            token (str): 認証トークン
            
        Returns:
            tuple: (成功したかどうか, 会社ID, メールアドレス)
        """
        db_name = get_db_path()
        
        try:
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            
            # 有効期限をチェックしてトークンを検証
            expiry_time = datetime.now() - timedelta(hours=UnifiedConfig.TOKEN_EXPIRY_HOURS)
            c.execute("""
                SELECT id, company_id, email, created_at 
                FROM users 
                WHERE verify_token = ? AND is_verified = 0
            """, (token,))
            user = c.fetchone()

            if user:
                user_id, company_id, email, created_at = user
                created_datetime = datetime.fromisoformat(created_at)
                
                # トークンの有効期限をチェック
                if created_datetime < expiry_time:
                    conn.close()
                    return False, None, None  # トークンが期限切れ
                
                # 有効なトークンの場合、認証を完了してトークンを削除
                c.execute("UPDATE users SET is_verified = 1, verify_token = NULL WHERE id = ?", (user_id,))
                conn.commit()
                conn.close()
                return True, company_id, email
            
            conn.close()
            return False, None, None
            
        except Exception as e:
            print(f"[AUTH_SERVICE] トークン検証エラー: {e}")
            return False, None, None

    @staticmethod
    def cleanup_expired_tokens():
        """期限切れの認証トークンを削除（データベースロック対応版）"""
        try:
            from core.database import get_cursor
            
            # 有効期限を過ぎたトークンを検索
            expiry_time = datetime.now() - timedelta(hours=UnifiedConfig.TOKEN_EXPIRY_HOURS)
            
            from core.database import DB_TYPE
            
            with get_cursor() as cursor:
                # 期限切れの未認証ユーザーを削除
                if DB_TYPE == "postgresql":
                    # PostgreSQLでcreated_atがtextの場合に対応
                    query = """
                        DELETE FROM users 
                        WHERE is_verified = 0 
                        AND verify_token IS NOT NULL 
                        AND created_at < %s
                    """
                    cursor.execute(query, (expiry_time.isoformat(),))
                else:
                    query = """
                        DELETE FROM users 
                        WHERE is_verified = 0 
                        AND verify_token IS NOT NULL 
                        AND created_at < ?
                    """
                    cursor.execute(query, (expiry_time.isoformat(),))
                
                deleted_count = cursor.rowcount
                
                if deleted_count > 0:
                    print(f"[AUTH_SERVICE] 期限切れトークン {deleted_count} 件を削除")
                
                return deleted_count
            
        except Exception as e:
            print(f"[AUTH_SERVICE] トークンクリーンアップエラー: {e}")
            return 0

    @staticmethod
    def logout_user():
        """ユーザーログアウト処理"""
        # セッション情報の削除
        for key in ["is_logged_in", "is_super_admin", "company_id", "company_name", "username", "user_email"]:
            if key in st.session_state:
                del st.session_state[key]
        
        # URLパラメータからログイン状態を削除
        if "logged_in" in st.query_params:
            current_params = dict(st.query_params)
            if "logged_in" in current_params:
                del current_params["logged_in"]
            st.query_params.update(**current_params)
        
        return True, "ログアウトしました"

    @staticmethod
    def is_logged_in():
        """ログイン状態かどうかを確認"""
        session_logged_in = "is_logged_in" in st.session_state and st.session_state["is_logged_in"] is True
        param_logged_in = st.query_params.get("logged_in") == "true"
        return session_logged_in or param_logged_in

    @staticmethod
    def is_super_admin():
        """スーパー管理者かどうかを確認"""
        return (AuthService.is_logged_in() and 
                "is_super_admin" in st.session_state and 
                st.session_state["is_super_admin"] is True)

    @staticmethod
    def get_current_company_id():
        """現在ログイン中の会社IDを取得"""
        if AuthService.is_logged_in():
            # まずcompany_idをチェック
            if "company_id" in st.session_state and st.session_state["company_id"]:
                return st.session_state["company_id"]
            
            # なければselected_companyをチェック
            if "selected_company" in st.session_state:
                company_id = st.session_state["selected_company"]
                st.session_state["company_id"] = company_id
                return company_id
        
        # URLパラメータから取得
        current_company = st.query_params.get("company")
        if current_company:
            st.session_state["company_id"] = current_company
            return current_company
        
        return None

    @staticmethod
    def _set_session_data(is_logged_in=False, is_super_admin=False, company_id=None, 
                         company_name=None, username=None, user_email=None):
        """セッションデータを設定"""
        st.session_state["is_logged_in"] = is_logged_in
        st.session_state["is_super_admin"] = is_super_admin
        st.session_state["company_id"] = company_id
        st.session_state["company_name"] = company_name
        st.session_state["username"] = username
        if user_email:
            st.session_state["user_email"] = user_email
        
        # URLパラメータにログイン状態を追加
        if is_logged_in:
            st.query_params.logged_in = "true"

    @staticmethod
    def _send_verification_email(email, token):
        """認証メールを送信"""
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")
        verification_url = "http://localhost:8501"
        
        if not smtp_user or not smtp_pass:
            print("[AUTH_SERVICE] メール設定が不完全です")
            return False
            
        msg = MIMEText(
            f"以下のリンクをクリックして登録を完了してください:\n"
            f"{verification_url}?token={token}"
        )
        msg["Subject"] = "【FAQシステム】メールアドレス認証のお願い"
        msg["From"] = smtp_user
        msg["To"] = email

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"[AUTH_SERVICE] メール送信エラー: {e}")
            return False


# 後方互換性のための関数エイリアス
def login_user(company_id, username, password):
    """後方互換性のためのエイリアス"""
    return AuthService.login_user_traditional(company_id, username, password)

def login_user_by_email(email, password):
    """後方互換性のためのエイリアス"""
    return AuthService.login_user_by_email(email, password)

def logout_user():
    """後方互換性のためのエイリアス"""
    return AuthService.logout_user()

def is_logged_in():
    """後方互換性のためのエイリアス"""
    return AuthService.is_logged_in()

def is_super_admin():
    """後方互換性のためのエイリアス"""
    return AuthService.is_super_admin()

def get_current_company_id():
    """後方互換性のためのエイリアス"""
    return AuthService.get_current_company_id()

def register_user(company_name, name, email, password, location_info=None):
    """後方互換性のためのエイリアス"""
    return AuthService.register_user(company_name, name, email, password, location_info)

def verify_user_token(token):
    """後方互換性のためのエイリアス"""
    return AuthService.verify_user_token(token)

def cleanup_expired_tokens():
    """後方互換性のためのエイリアス"""
    return AuthService.cleanup_expired_tokens()
