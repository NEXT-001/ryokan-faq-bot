"""
認証検証ユーティリティ
utils/auth_validation.py

ログイン処理の整合性チェックと不正アクセス防止
"""
import streamlit as st
from typing import Tuple, Optional
from core.database import fetch_one
from config.unified_config import UnifiedConfig


def validate_company_access(company_id: str, user_email: Optional[str] = None) -> Tuple[bool, str]:
    """
    企業アクセスの妥当性を検証
    
    Args:
        company_id (str): 企業ID
        user_email (str, optional): ユーザーメールアドレス
        
    Returns:
        Tuple[bool, str]: (有効かどうか, メッセージ)
    """
    try:
        # 1. 企業の存在確認
        company_query = "SELECT id, name FROM companies WHERE id = %s"
        company = fetch_one(company_query, (company_id,))
        
        if not company:
            UnifiedConfig.log_warning(f"存在しない企業へのアクセス試行: {company_id}")
            return False, f"企業ID「{company_id}」は存在しません"
        
        # 2. ユーザーが指定されている場合、ユーザーと企業の関連をチェック
        if user_email:
            user_query = "SELECT company_id FROM users WHERE email = %s"
            user = fetch_one(user_query, (user_email,))
            
            if user:
                # PostgreSQL RealDictCursor対応
                user_company_id = user['company_id'] if hasattr(user, 'get') else user[1]
                if user_company_id != company_id:
                    UnifiedConfig.log_warning(f"不正な企業アクセス: ユーザー {user_email} が企業 {company_id} にアクセス試行")
                    return False, f"この企業へのアクセス権限がありません"
        
        return True, "アクセス許可"
        
    except Exception as e:
        UnifiedConfig.log_error(f"企業アクセス検証エラー: {e}")
        return False, "検証エラーが発生しました"


def redirect_to_correct_company(user_email: str) -> Optional[str]:
    """
    ユーザーの正しい企業IDを取得してリダイレクト
    
    Args:
        user_email (str): ユーザーメールアドレス
        
    Returns:
        Optional[str]: 正しい企業ID、またはNone
    """
    try:
        user_query = "SELECT company_id, name FROM users WHERE email = %s"
        user = fetch_one(user_query, (user_email,))
        
        if user:
            # PostgreSQL RealDictCursor対応
            correct_company_id = user['company_id'] if hasattr(user, 'get') else user[0]
            UnifiedConfig.log_info(f"ユーザー {user_email} を正しい企業 {correct_company_id} にリダイレクト")
            return correct_company_id
        
        return None
        
    except Exception as e:
        UnifiedConfig.log_error(f"リダイレクト処理エラー: {e}")
        return None


def handle_invalid_company_access(company_id: str, user_email: Optional[str] = None):
    """
    無効な企業アクセスを処理
    
    Args:
        company_id (str): 無効な企業ID
        user_email (str, optional): ユーザーメールアドレス
    """
    st.error(f"⚠️ 企業ID「{company_id}」は存在しないか、アクセス権限がありません")
    
    # ユーザーが指定されている場合、正しい企業にリダイレクト
    if user_email:
        correct_company = redirect_to_correct_company(user_email)
        if correct_company:
            st.info(f"あなたの企業「{correct_company}」の管理画面に移動してください")
            admin_url = f"?mode=admin&company={correct_company}&logged_in=true"
            st.markdown(f"[正しい管理画面に移動]({admin_url})")
        else:
            st.info("メールアドレスでログインし直してください")
            st.markdown("[ログインページに戻る](?)")
    else:
        st.info("有効な企業IDを指定してアクセスしてください")
        st.markdown("[トップページに戻る](?)")


def validate_session_integrity():
    """
    セッションの整合性を検証
    
    Returns:
        bool: セッションが有効かどうか
    """
    try:
        # セッション状態の基本チェック
        if not hasattr(st.session_state, 'is_logged_in') or not st.session_state.is_logged_in:
            return True  # ログインしていない状態は正常
        
        # ログイン状態の場合、企業IDとユーザー情報の整合性をチェック
        company_id = getattr(st.session_state, 'company_id', None)
        user_email = getattr(st.session_state, 'user_email', None)
        
        if company_id and user_email:
            valid, message = validate_company_access(company_id, user_email)
            if not valid:
                # セッションをクリア
                clear_invalid_session()
                st.error(f"セッションの整合性エラー: {message}")
                st.rerun()
                return False
        
        return True
        
    except Exception as e:
        UnifiedConfig.log_error(f"セッション整合性チェックエラー: {e}")
        return False


def clear_invalid_session():
    """無効なセッション情報をクリア"""
    session_keys = [
        'is_logged_in', 
        'is_super_admin', 
        'company_id', 
        'company_name',
        'username', 
        'user_email'
    ]
    
    for key in session_keys:
        if key in st.session_state:
            del st.session_state[key]
    
    UnifiedConfig.log_info("無効なセッション情報をクリアしました")


def secure_company_access_wrapper(func):
    """
    企業アクセスを安全にラップするデコレータ
    
    Args:
        func: ラップする関数（第一引数がcompany_idである必要がある）
    """
    def wrapper(company_id, *args, **kwargs):
        # 企業アクセスの妥当性を検証
        user_email = getattr(st.session_state, 'user_email', None)
        valid, message = validate_company_access(company_id, user_email)
        
        if not valid:
            handle_invalid_company_access(company_id, user_email)
            return
        
        # セッション整合性をチェック
        if not validate_session_integrity():
            return
        
        # 有効な場合は元の関数を実行
        return func(company_id, *args, **kwargs)
    
    return wrapper