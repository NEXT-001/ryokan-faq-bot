"""
Streamlit最適化ユーティリティ
utils/streamlit_optimization.py

Streamlitアプリケーションのパフォーマンスとユーザビリティを改善
"""
import streamlit as st
import time
from functools import wraps
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from config.unified_config import UnifiedConfig


class StreamlitOptimizer:
    """Streamlit最適化クラス"""
    
    @staticmethod
    def configure_page_optimizations():
        """ページ最適化の設定"""
        # ページ設定の最適化
        st.set_page_config(
            page_title="FAQ Bot - Optimized",
            page_icon="🤖",
            layout="wide",
            initial_sidebar_state="collapsed",
            menu_items={
                'Get Help': None,
                'Report a bug': None,
                'About': "FAQ Bot System - Optimized for Performance"
            }
        )
        
        # パフォーマンス向上のためのCSS
        st.markdown("""
        <style>
        /* パフォーマンス最適化CSS */
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* 読み込みインジケーターのスタイリング */
        .loading-indicator {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        /* フォーム最適化 */
        .stForm {
            border: 1px solid #e0e0e0;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* レスポンシブ設計 */
        @media (max-width: 768px) {
            .stApp {
                padding: 10px;
            }
        }
        
        /* エラーメッセージのスタイリング */
        .error-message {
            background-color: #ffebee;
            border-left: 4px solid #f44336;
            padding: 12px;
            margin: 10px 0;
        }
        
        /* 成功メッセージのスタイリング */
        .success-message {
            background-color: #e8f5e8;
            border-left: 4px solid #4caf50;
            padding: 12px;
            margin: 10px 0;
        }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def add_loading_state(message: str = "処理中..."):
        """ローディング状態の表示"""
        return st.empty().markdown(f"""
        <div class="loading-indicator">
            <div>🔄 {message}</div>
        </div>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def performance_monitor(func: Callable) -> Callable:
        """パフォーマンス監視デコレータ"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 遅いfunction（2秒以上）の警告
                if execution_time > 2.0:
                    if UnifiedConfig.should_log_debug():
                        st.warning(f"⚠️ 処理時間が長くなっています: {func.__name__} ({execution_time:.2f}秒)")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                UnifiedConfig.log_error(f"Function {func.__name__} failed after {execution_time:.2f}s")
                UnifiedConfig.log_debug(f"Error details: {str(e)}")
                raise
        
        return wrapper
    
    @staticmethod
    def cache_with_ttl(ttl_seconds: int = 300):
        """TTL付きキャッシュデコレータ"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # キャッシュキーの生成
                cache_key = f"{func.__name__}_{hash(str(args) + str(kwargs))}"
                current_time = datetime.now()
                
                # セッション状態でキャッシュ管理
                if 'cache' not in st.session_state:
                    st.session_state.cache = {}
                
                # キャッシュの確認
                if cache_key in st.session_state.cache:
                    cached_data, cached_time = st.session_state.cache[cache_key]
                    if current_time - cached_time < timedelta(seconds=ttl_seconds):
                        return cached_data
                
                # キャッシュミス時の実行
                result = func(*args, **kwargs)
                st.session_state.cache[cache_key] = (result, current_time)
                
                return result
            
            return wrapper
        return decorator
    
    @staticmethod
    def optimize_form_submission():
        """フォーム送信の最適化"""
        # 重複送信防止
        if 'form_submitted' not in st.session_state:
            st.session_state.form_submitted = False
        
        # セッションタイムアウト管理
        if 'last_activity' not in st.session_state:
            st.session_state.last_activity = datetime.now()
        
        current_time = datetime.now()
        if current_time - st.session_state.last_activity > timedelta(minutes=30):
            st.warning("⏰ セッションがタイムアウトしました。ページを更新してください。")
            st.stop()
        
        st.session_state.last_activity = current_time
    
    @staticmethod
    def add_progress_tracking():
        """進捗追跡の追加"""
        if 'progress_data' not in st.session_state:
            st.session_state.progress_data = {
                'step': 0,
                'total_steps': 0,
                'current_action': ''
            }
        
        return st.session_state.progress_data
    
    @staticmethod
    def show_progress(current_step: int, total_steps: int, action: str):
        """進捗表示"""
        progress_value = current_step / total_steps if total_steps > 0 else 0
        
        # 進捗バーの表示
        progress_bar = st.progress(progress_value)
        status_text = st.empty()
        status_text.text(f"{action} ({current_step}/{total_steps})")
        
        return progress_bar, status_text
    
    @staticmethod
    def enhanced_error_handling():
        """強化されたエラーハンドリング"""
        
        def error_handler(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # ユーザーフレンドリーなエラーメッセージ
                    error_type = type(e).__name__
                    
                    if "ConnectionError" in error_type:
                        st.error("🌐 接続エラーが発生しました。インターネット接続を確認してください。")
                    elif "TimeoutError" in error_type or "timeout" in str(e).lower():
                        st.error("⏱️ 処理がタイムアウトしました。しばらく待ってから再試行してください。")
                    elif "ValidationError" in error_type:
                        st.error("📝 入力内容に問題があります。フォームを確認してください。")
                    else:
                        st.error("❌ 予期しないエラーが発生しました。")
                    
                    # デバッグ情報（開発環境のみ）
                    if UnifiedConfig.DEBUG_MODE:
                        st.exception(e)
                    
                    # エラーログの記録
                    UnifiedConfig.log_error(f"Streamlit function error: {func.__name__}")
                    UnifiedConfig.log_debug(f"Error details: {str(e)}")
                    
                    # エラー回復の提案
                    with st.expander("🔧 トラブルシューティング"):
                        st.markdown("""
                        **試してみてください:**
                        1. ページを再読み込みする
                        2. ブラウザのキャッシュを削除する
                        3. 別のブラウザで試す
                        4. 時間をおいて再度アクセスする
                        """)
            
            return wrapper
        
        return error_handler
    
    @staticmethod
    def add_accessibility_features():
        """アクセシビリティ機能の追加"""
        
        # スクリーンリーダー対応
        st.markdown("""
        <style>
        /* スクリーンリーダー対応 */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0,0,0,0);
            white-space: nowrap;
            border: 0;
        }
        
        /* フォーカス可視化 */
        button:focus, input:focus, select:focus, textarea:focus {
            outline: 2px solid #007acc;
            outline-offset: 2px;
        }
        
        /* 高コントラスト対応 */
        @media (prefers-contrast: high) {
            * {
                border-color: #000;
                color: #000;
                background-color: #fff;
            }
        }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def add_mobile_optimizations():
        """モバイル最適化"""
        
        st.markdown("""
        <style>
        /* モバイル最適化 */
        @media (max-width: 768px) {
            .stTextInput > div > div > input {
                font-size: 16px; /* iOSのズームイン防止 */
            }
            
            .stButton > button {
                width: 100%;
                margin: 10px 0;
                min-height: 44px; /* タッチターゲットサイズ */
            }
            
            .stSelectbox > div > div {
                min-height: 44px;
            }
        }
        
        /* タッチフレンドリー要素 */
        .touch-friendly {
            min-height: 44px;
            min-width: 44px;
            padding: 12px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # ビューポート設定の確認
        st.markdown("""
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0">
        """, unsafe_allow_html=True)


class FormValidator:
    """フォームバリデーター"""
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """メールアドレスの検証"""
        import re
        
        if not email:
            return False, "メールアドレスを入力してください"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "有効なメールアドレスを入力してください"
        
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """パスワードの検証"""
        if not password:
            return False, "パスワードを入力してください"
        
        if len(password) < 6:
            return False, "パスワードは6文字以上で入力してください"
        
        return True, ""
    
    @staticmethod
    def validate_company_name(company_name: str) -> tuple[bool, str]:
        """会社名の検証"""
        if not company_name:
            return False, "会社名を入力してください"
        
        if len(company_name.strip()) < 2:
            return False, "会社名は2文字以上で入力してください"
        
        return True, ""
    
    @staticmethod
    def validate_form_data(data: Dict[str, Any]) -> Dict[str, str]:
        """フォームデータ全体の検証"""
        errors = {}
        
        # 会社名
        if 'company' in data:
            valid, message = FormValidator.validate_company_name(data['company'])
            if not valid:
                errors['company'] = message
        
        # メールアドレス
        if 'email' in data:
            valid, message = FormValidator.validate_email(data['email'])
            if not valid:
                errors['email'] = message
        
        # パスワード
        if 'password' in data:
            valid, message = FormValidator.validate_password(data['password'])
            if not valid:
                errors['password'] = message
        
        return errors


def apply_optimizations():
    """全ての最適化を適用"""
    optimizer = StreamlitOptimizer()
    
    # ページ最適化
    optimizer.configure_page_optimizations()
    
    # アクセシビリティ機能
    optimizer.add_accessibility_features()
    
    # モバイル最適化
    optimizer.add_mobile_optimizations()
    
    # フォーム最適化
    optimizer.optimize_form_submission()
    
    return optimizer


# グローバル最適化の適用
def initialize_streamlit_optimizations():
    """Streamlit最適化の初期化"""
    try:
        optimizer = apply_optimizations()
        UnifiedConfig.log_info("Streamlit optimizations applied successfully")
        return optimizer
    except Exception as e:
        UnifiedConfig.log_error("Failed to apply Streamlit optimizations")
        UnifiedConfig.log_debug(f"Optimization error: {str(e)}")
        return None