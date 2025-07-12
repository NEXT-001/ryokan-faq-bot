"""
アプリケーション設定管理
config/app_config.py
"""
import os
import streamlit as st
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()


class AppConfig:
    """アプリケーション設定クラス"""
    
    # データベース設定
    DB_NAME = os.path.join("data", "faq_database.db")
    
    # メール設定
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    VERIFICATION_URL = "http://localhost:8501"
    
    # API設定
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
    
    # テストモード設定
    TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
    
    @classmethod
    def is_test_mode(cls):
        """テストモードかどうかを判定"""
        return cls.TEST_MODE
    
    @classmethod
    def has_api_keys(cls):
        """APIキーが設定されているかどうかを判定"""
        return bool(cls.ANTHROPIC_API_KEY and cls.VOYAGE_API_KEY)
    
    @classmethod
    def ensure_data_directory(cls):
        """dataディレクトリの存在を確保"""
        os.makedirs("data", exist_ok=True)


def get_url_params():
    """URLパラメータを取得する"""
    # verifyページかどうかをチェック（tokenパラメータの存在）
    if "token" in st.query_params:
        return "verify", None, False
    
    # モードの取得（デフォルトはuser）
    mode = st.query_params.get("mode", "user")
    if mode not in ["admin", "user", "reg"]:
        mode = "user"
    
    # 会社IDの取得（regモードの場合は無視）
    if mode == "reg":
        company_id = None
    else:
        company_id = st.query_params.get("company", "demo-company")
    
    # ログイン状態も取得
    logged_in = st.query_params.get("logged_in", "false")
    
    return mode, company_id, logged_in == "true"


def configure_page(mode):
    """モードに応じてページ設定を行う"""
    if mode == "admin":
        # 管理モードの場合はサイドバーを展開
        st.set_page_config(
            page_title="FAQチャットボットシステム - 管理画面",
            page_icon="💬",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    elif mode == "reg":
        # 登録モードの場合はサイドバーを非表示
        st.set_page_config(
            page_title="FAQチャットボットシステム - 登録",
            page_icon="💬",
            layout="centered",
            initial_sidebar_state="collapsed"
        )
    else:
        # ユーザーモードの場合はサイドバーを非表示
        st.set_page_config(
            page_title="FAQチャットボット",
            page_icon="💬",
            layout="wide",
            initial_sidebar_state="collapsed"
        )