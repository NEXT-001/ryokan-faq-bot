"""
シンプルな2段階登録サービス（PostgreSQL対応）
services/simplified_registration_service.py
"""
import os
import re
import uuid
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Tuple, Optional, Dict

from core.database import (
    execute_query, fetch_dict_one, fetch_dict, DB_TYPE,
    get_cursor, save_company_to_db
)
from utils.auth_utils import hash_password
from config.unified_config import UnifiedConfig


class SimplifiedRegistrationService:
    """シンプルな2段階登録サービス"""
    
    @staticmethod
    def send_registration_link(email: str, user_ip: str = None) -> Tuple[bool, str]:
        """
        Step 1: メールアドレスのみで登録リンクを送信
        
        Args:
            email (str): 登録用メールアドレス
            user_ip (str): ユーザーのIPアドレス
            
        Returns:
            tuple: (成功フラグ, メッセージ)
        """
        try:
            # 1. メールアドレス形式チェック
            if not SimplifiedRegistrationService._is_valid_email(email):
                return False, "有効なメールアドレスを入力してください"
            
            # 2. 既存ユーザーチェック
            if SimplifiedRegistrationService._email_exists(email):
                return False, "このメールアドレスは既に登録されています"
            
            # 3. 登録トークンを生成
            token = str(uuid.uuid4())
            
            # 4. 仮登録データをDBに保存（24時間有効）
            success = SimplifiedRegistrationService._save_temp_registration(email, token, user_ip)
            if not success:
                return False, "データベースエラーが発生しました"
            
            # 5. 登録リンク付きメールを送信
            success = SimplifiedRegistrationService._send_email_with_link(email, token)
            if success:
                return True, f"登録リンクを{email}に送信しました。メールをご確認ください。"
            else:
                return False, "メール送信に失敗しました"
                
        except Exception as e:
            print(f"[REGISTRATION] 登録リンク送信エラー: {e}")
            return False, "システムエラーが発生しました"
    
    @staticmethod
    def verify_registration_token(token: str) -> Tuple[bool, Optional[str]]:
        """
        登録トークンの検証
        
        Args:
            token (str): 登録トークン
            
        Returns:
            tuple: (有効フラグ, メールアドレス)
        """
        try:
            param_format = "%s" if DB_TYPE == "postgresql" else "?"
            query = f"SELECT email, created_at FROM temp_registrations WHERE token = {param_format} AND is_used = 0"
            
            result = fetch_dict_one(query, (token,))
            if not result:
                return False, None
            
            # トークン有効期限チェック（24時間）
            created_at = result['created_at']
            if isinstance(created_at, str):
                created_datetime = datetime.fromisoformat(created_at)
            else:
                created_datetime = created_at
                
            expiry_time = datetime.now() - timedelta(hours=24)
            if created_datetime < expiry_time:
                return False, None  # 期限切れ
                
            return True, result['email']
            
        except Exception as e:
            print(f"[REGISTRATION] トークン検証エラー: {e}")
            return False, None
    
    @staticmethod
    def complete_registration(
        token: str,
        company_name: str,
        name: str,
        password: str,
        confirm_password: str,
        postal_code: str,
        prefecture: str,
        city: str,
        address: str
    ) -> Tuple[bool, str]:
        """
        Step 2: 完全な登録を完了
        
        Args:
            token (str): 登録トークン
            company_name (str): 会社名
            name (str): 担当者名
            password (str): パスワード
            confirm_password (str): 確認用パスワード
            postal_code (str): 郵便番号
            prefecture (str): 都道府県
            city (str): 市区町村
            address (str): 番地・建物名
            
        Returns:
            tuple: (成功フラグ, メッセージ)
        """
        try:
            # 1. トークン検証
            is_valid, email = SimplifiedRegistrationService.verify_registration_token(token)
            if not is_valid:
                return False, "登録リンクが無効または期限切れです"
            
            # 2. 入力値検証
            validation_error = SimplifiedRegistrationService._validate_registration_data(
                company_name, name, password, confirm_password, postal_code
            )
            if validation_error:
                return False, validation_error
            
            # 3. 会社IDを生成（8文字以上、重複なし）
            company_id = SimplifiedRegistrationService._generate_unique_company_id(company_name)
            
            # 4. データベース登録（トランザクション）
            success = SimplifiedRegistrationService._save_complete_registration(
                company_id, company_name, name, email, password,
                postal_code, prefecture, city, address, token
            )
            
            if success:
                return True, f"登録が完了しました。会社ID: {company_id}"
            else:
                return False, "登録処理中にエラーが発生しました"
                
        except Exception as e:
            print(f"[REGISTRATION] 完全登録エラー: {e}")
            return False, "システムエラーが発生しました"
    
    # =============================================================================
    # Private Methods
    # =============================================================================
    
    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """メールアドレス形式チェック"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def _email_exists(email: str) -> bool:
        """既存ユーザーチェック"""
        try:
            param_format = "%s" if DB_TYPE == "postgresql" else "?"
            query = f"SELECT COUNT(*) as count FROM users WHERE email = {param_format}"
            result = fetch_dict_one(query, (email,))
            return result['count'] > 0 if result else False
        except Exception as e:
            print(f"[REGISTRATION] メールアドレス重複チェックエラー: {e}")
            return True  # エラー時は重複ありとして安全側に倒す
    
    @staticmethod
    def _save_temp_registration(email: str, token: str, user_ip: str) -> bool:
        """仮登録データをDBに保存"""
        try:
            # temp_registrations テーブルが存在しない場合は作成
            SimplifiedRegistrationService._ensure_temp_table_exists()
            
            param_format = "%s" if DB_TYPE == "postgresql" else "?"
            
            if DB_TYPE == "postgresql":
                query = f"""
                    INSERT INTO temp_registrations (email, token, user_ip, created_at, is_used)
                    VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                """
                created_at = datetime.now()
            else:
                query = f"""
                    INSERT INTO temp_registrations (email, token, user_ip, created_at, is_used)
                    VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format})
                """
                created_at = datetime.now().isoformat()
            
            execute_query(query, (email, token, user_ip, created_at, 0))
            return True
            
        except Exception as e:
            print(f"[REGISTRATION] 仮登録保存エラー: {e}")
            return False
    
    @staticmethod
    def _ensure_temp_table_exists():
        """temp_registrations テーブル作成"""
        try:
            with get_cursor() as cursor:
                if DB_TYPE == "postgresql":
                    create_table_sql = """
                        CREATE TABLE IF NOT EXISTS temp_registrations (
                            id SERIAL PRIMARY KEY,
                            email TEXT NOT NULL,
                            token TEXT UNIQUE NOT NULL,
                            user_ip TEXT,
                            created_at TIMESTAMP NOT NULL,
                            is_used INTEGER DEFAULT 0
                        )
                    """
                else:
                    create_table_sql = """
                        CREATE TABLE IF NOT EXISTS temp_registrations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            email TEXT NOT NULL,
                            token TEXT UNIQUE NOT NULL,
                            user_ip TEXT,
                            created_at TEXT NOT NULL,
                            is_used INTEGER DEFAULT 0
                        )
                    """
                cursor.execute(create_table_sql)
                
        except Exception as e:
            print(f"[REGISTRATION] テーブル作成エラー: {e}")
    
    @staticmethod
    def _send_email_with_link(email: str, token: str) -> bool:
        """登録リンク付きメールを送信"""
        try:
            smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_username = os.getenv('SMTP_USERNAME')
            smtp_password = os.getenv('SMTP_PASSWORD')
            
            if not all([smtp_username, smtp_password]):
                print("[REGISTRATION] SMTP設定が不完全です")
                return False
            
            # 登録リンクURL生成
            base_url = UnifiedConfig.BASE_URL
            registration_link = f"{base_url}?mode=complete_reg&token={token}"
            
            # メール内容
            subject = "【14日間無料お試し】本登録のお手続き"
            
            html_body = f"""
            <html>
            <body>
                <h2>14日間無料お試し登録</h2>
                <p>ご登録いただきありがとうございます。</p>
                <p>下記のリンクから本登録をお済ませください：</p>
                <p><a href="{registration_link}" style="background-color: #4CAF50; color: white; padding: 14px 20px; text-decoration: none; border-radius: 4px;">本登録はこちらから</a></p>
                <p>※このリンクは24時間有効です。</p>
                <p>リンクが開けない場合は、下記URLをブラウザにコピーしてください：</p>
                <p>{registration_link}</p>
            </body>
            </html>
            """
            
            text_body = f"""
14日間無料お試し登録

ご登録いただきありがとうございます。
下記のリンクから本登録をお済ませください：

{registration_link}

※このリンクは24時間有効です。
            """
            
            # メール作成
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_username
            msg['To'] = email
            
            text_part = MIMEText(text_body, 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # メール送信
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            print(f"[REGISTRATION] 登録リンクメール送信完了: {email}")
            return True
            
        except Exception as e:
            print(f"[REGISTRATION] メール送信エラー: {e}")
            return False
    
    @staticmethod
    def _validate_registration_data(
        company_name: str,
        name: str,
        password: str,
        confirm_password: str,
        postal_code: str
    ) -> Optional[str]:
        """登録データの検証"""
        
        if not company_name or not company_name.strip():
            return "会社名を入力してください"
        
        if not name or not name.strip():
            return "担当者名を入力してください"
        
        if len(password) < 8:
            return "パスワードは8文字以上で入力してください"
        
        if password != confirm_password:
            return "パスワードが一致しません"
        
        if not re.match(r'^\d{3}-?\d{4}$', postal_code):
            return "郵便番号を正しい形式で入力してください（例：123-4567）"
        
        return None
    
    @staticmethod
    def _generate_unique_company_id(company_name: str) -> str:
        """ユニークな会社IDを生成（8文字以上）"""
        try:
            # ベースIDを生成
            clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
            
            if clean_name and len(clean_name) >= 3:
                base_id = f"company_{clean_name[:10]}"
            else:
                base_id = f"company_{str(uuid.uuid4())[:8]}"
            
            # 既存IDチェック
            param_format = "%s" if DB_TYPE == "postgresql" else "?"
            
            counter = 1
            unique_id = base_id
            while True:
                query = f"SELECT COUNT(*) as count FROM companies WHERE id = {param_format}"
                result = fetch_dict_one(query, (unique_id,))
                
                if not result or result['count'] == 0:
                    break
                    
                unique_id = f"{base_id}_{counter:06d}"
                counter += 1
            
            # 8文字以上を保証
            if len(unique_id) < 8:
                unique_id += f"_{str(uuid.uuid4())[:4]}"
            
            return unique_id
            
        except Exception as e:
            print(f"[REGISTRATION] 会社ID生成エラー: {e}")
            return f"company_{str(uuid.uuid4())[:8]}"
    
    @staticmethod
    def _save_complete_registration(
        company_id: str,
        company_name: str,
        name: str,
        email: str,
        password: str,
        postal_code: str,
        prefecture: str,
        city: str,
        address: str,
        token: str
    ) -> bool:
        """完全な登録をデータベースに保存"""
        try:
            param_format = "%s" if DB_TYPE == "postgresql" else "?"
            
            # 1. companiesテーブルに登録
            company_success = save_company_to_db(
                company_id=company_id,
                company_name=company_name,
                prefecture=prefecture,
                city=city,
                address=address,
                postal_code=postal_code
            )
            
            if not company_success:
                return False
            
            # 2. usersテーブルに登録（認証済み状態で）
            if DB_TYPE == "postgresql":
                user_query = f"""
                    INSERT INTO users (company_id, company_name, name, email, password, created_at, is_verified)
                    VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format}, 1)
                """
                created_at = datetime.now()
            else:
                user_query = f"""
                    INSERT INTO users (company_id, company_name, name, email, password, created_at, is_verified)
                    VALUES ({param_format}, {param_format}, {param_format}, {param_format}, {param_format}, {param_format}, 1)
                """
                created_at = datetime.now().isoformat()
            
            execute_query(user_query, (
                company_id, company_name, name, email,
                hash_password(password), created_at
            ))
            
            # 3. temp_registrations のトークンを使用済みにマーク
            temp_update_query = f"UPDATE temp_registrations SET is_used = 1 WHERE token = {param_format}"
            execute_query(temp_update_query, (token,))
            
            print(f"[REGISTRATION] 完全登録完了: {company_id} - {email}")
            return True
            
        except Exception as e:
            print(f"[REGISTRATION] 完全登録保存エラー: {e}")
            return False