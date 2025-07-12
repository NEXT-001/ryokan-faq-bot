"""
認証関連のユーティリティ関数
utils/auth_utils.py
"""
import hashlib


def hash_password(password):
    """
    パスワードをハッシュ化する
    
    Args:
        password (str): ハッシュ化するパスワード
        
    Returns:
        str: ハッシュ化されたパスワード
    """
    return hashlib.sha256(password.encode()).hexdigest()