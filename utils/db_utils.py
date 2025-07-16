"""
データベース関連のユーティリティ関数（統合サービスへのプロキシ）
utils/db_utils.py

注意: このファイルは後方互換性のために残されています。
新しいコードでは以下を直接使用してください:
- core/database.py: データベース操作
- services/auth_service.py: 認証関連
"""
import os
from core.database import get_db_path as core_get_db_path, initialize_database
from services.auth_service import AuthService

# 後方互換性のための関数エイリアス

def get_db_path():
    """データベースファイルのパスを取得（プロキシ）"""
    return core_get_db_path()

def init_db():
    """データベースを初期化（プロキシ）"""
    return initialize_database()

def register_user(company_name, name, email, password):
    """ユーザーを仮登録（プロキシ）"""
    return AuthService.register_user(company_name, name, email, password)

def verify_user_token(token):
    """メール認証トークンを検証（プロキシ）"""
    return AuthService.verify_user_token(token)

def cleanup_expired_tokens():
    """期限切れの認証トークンを削除（プロキシ）"""
    return AuthService.cleanup_expired_tokens()

def login_user_by_email(email, password):
    """メールアドレスとパスワードでのログイン（プロキシ）"""
    return AuthService.login_user_by_email(email, password)

def send_verification_email(email, token):
    """認証メールを送信（プロキシ）"""
    return AuthService._send_verification_email(email, token)
