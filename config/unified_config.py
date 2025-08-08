"""
統一設定管理システム
config/unified_config.py

このファイルは以下の重複していた設定管理を統一します：
- config/settings.py
- config/app_config.py  
- utils/constants.py の設定関連部分
"""
import os
import streamlit as st
from dotenv import load_dotenv
import anthropic

# 環境変数を読み込み
load_dotenv()


class UnifiedConfig:
    """統一設定管理クラス"""
    
    # ===== アプリケーション基本情報 =====
    APP_NAME = "FAQ Bot"
    APP_VERSION = "1.0.0"
    APP_DESCRIPTION = "FAQ自動応答システム"
    
    # ===== ディレクトリパス =====
    DATA_DIR = "data"
    COMPANIES_DIR = os.path.join(DATA_DIR, "companies")
    UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
    LOGS_DIR = os.path.join(DATA_DIR, "logs")
    BACKUP_DIR = os.path.join(DATA_DIR, "backups")
    
    # ===== データベース設定 =====
    DB_NAME = "faq_database.db"
    DB_PATH = os.path.join(DATA_DIR, DB_NAME)
    
    # ===== API設定 =====
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
    DEFAULT_API_TIMEOUT = 30
    MAX_RETRY_ATTEMPTS = 3
    
    # ===== メール設定 =====
    SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@example.com")
    
    # ===== テストモード・ログレベル設定 =====
    TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # DEBUG, INFO, WARNING, ERROR
    ENABLE_DEBUG_LOGS = os.getenv("ENABLE_DEBUG_LOGS", "false").lower() == "true"
    
    # ===== URL設定 =====
    BASE_URL = os.getenv("BASE_URL", "http://localhost:8501")
    
    # ===== デフォルト値 =====
    DEFAULT_COMPANY_ID = "demo-company"
    DEFAULT_MODE = "user"
    DEFAULT_ADMIN_USERNAME = "admin"
    DEFAULT_ADMIN_PASSWORD = "admin123"
    DEFAULT_ADMIN_EMAIL = "admin@example.com"
    
    # ===== ファイル名定数 =====
    FAQ_FILE = "faq.csv"
    COMPANIES_FILE = "companies.json"
    CHAT_HISTORY_FILE = "chat_history.json"
    USER_DATA_FILE = "users.json"
    
    # ===== セキュリティ設定 =====
    PASSWORD_MIN_LENGTH = 6
    SESSION_KEY_LENGTH = 32
    TOKEN_EXPIRY_HOURS = 24
    VERIFICATION_TOKEN_LENGTH = 32
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    
    # ===== ファイルアップロード設定 =====
    MAX_FILE_SIZE_MB = 10
    SUPPORTED_FILE_TYPES = [".csv", ".json", ".txt"]
    ALLOWED_EXTENSIONS = {'csv', 'txt', 'json'}
    
    # ===== UI設定 =====
    SIDEBAR_WIDTH = 300
    PAGE_TITLE_MAX_LENGTH = 50
    COMPANY_NAME_MAX_LENGTH = 100
    ITEMS_PER_PAGE = 20
    MAX_DISPLAY_LENGTH = 100
    MAX_CHAT_HISTORY = 100
    SESSION_TIMEOUT_MINUTES = 30
    
    # ===== データベーステーブル名 =====
    TABLE_USERS = "users"
    TABLE_COMPANIES = "companies"
    TABLE_FAQ = "faq_data"
    TABLE_CHAT_HISTORY = "chat_history"
    
    @classmethod
    def is_test_mode(cls):
        """テストモードかどうかを判定"""
        return cls.TEST_MODE
    
    @classmethod
    def is_debug_mode(cls):
        """デバッグモードかどうかを判定"""
        return cls.DEBUG_MODE
    
    @classmethod
    def should_log_debug(cls):
        """デバッグログを出力すべきかを判定"""
        return cls.ENABLE_DEBUG_LOGS or cls.DEBUG_MODE
    
    @classmethod
    def log_debug(cls, message):
        """条件付きデバッグログ出力"""
        if cls.should_log_debug():
            print(f"[DEBUG] {message}")
    
    @classmethod
    def log_info(cls, message):
        """情報ログ出力"""
        print(f"[INFO] {message}")
    
    @classmethod
    def log_warning(cls, message):
        """警告ログ出力"""
        print(f"[WARNING] {message}")
    
    @classmethod
    def log_error(cls, message):
        """エラーログ出力"""
        print(f"[ERROR] {message}")
    
    @classmethod
    def use_advanced_logging(cls):
        """高度なログシステムを使用するかどうか"""
        return os.getenv("USE_ADVANCED_LOGGING", "true").lower() == "true"
    
    @classmethod
    def has_api_keys(cls):
        """APIキーが設定されているかどうかを判定"""
        return bool(cls.ANTHROPIC_API_KEY and cls.VOYAGE_API_KEY)
    
    @classmethod
    def has_anthropic_key(cls):
        """Anthropic APIキーが設定されているかどうかを判定"""
        return bool(cls.ANTHROPIC_API_KEY)
    
    @classmethod
    def has_voyage_key(cls):
        """Voyage APIキーが設定されているかどうかを判定"""
        return bool(cls.VOYAGE_API_KEY)
    
    @classmethod
    def has_email_config(cls):
        """メール設定が完了しているかどうかを判定"""
        return bool(cls.SMTP_USER and cls.SMTP_PASS)
    
    @classmethod
    def ensure_data_directory(cls):
        """dataディレクトリの存在を確保"""
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.COMPANIES_DIR, exist_ok=True)
        os.makedirs(cls.UPLOAD_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.BACKUP_DIR, exist_ok=True)
    
    @classmethod
    def get_data_path(cls, company_id=None):
        """
        会社IDに基づいたデータディレクトリのパスを取得する
        
        Args:
            company_id (str, optional): 会社ID
            
        Returns:
            str: データディレクトリのパス
        """
        if company_id:
            company_path = os.path.join(cls.COMPANIES_DIR, company_id)
            os.makedirs(company_path, exist_ok=True)
            return company_path
        return cls.DATA_DIR
    
    @classmethod
    def get_company_folder_path(cls, company_id):
        """会社フォルダのパスを取得"""
        company_path = os.path.join(cls.COMPANIES_DIR, company_id)
        os.makedirs(company_path, exist_ok=True)
        return company_path
    
    @classmethod
    def get_faq_file_path(cls, company_id):
        """FAQファイルのパスを取得"""
        return os.path.join(cls.get_data_path(company_id), cls.FAQ_FILE)
    
    @classmethod
    def get_db_path(cls, company_id=None):
        """データベースファイルのパスを取得"""
        if company_id:
            return os.path.join(cls.get_data_path(company_id), cls.DB_NAME)
        return cls.DB_PATH
    
    @classmethod
    def get_url_params(cls):
        """URLパラメータを取得する"""
        try:
            # verifyページかどうかをチェック（tokenパラメータの存在）
            if "token" in st.query_params:
                return "verify", None, False
            
            # モードの取得（デフォルトはuser）
            mode = st.query_params.get("mode", cls.DEFAULT_MODE)
            if mode not in ["admin", "user", "reg"]:
                mode = cls.DEFAULT_MODE
            
            # 会社IDの取得（regモードの場合は無視）
            if mode == "reg":
                company_id = None
            else:
                company_id = st.query_params.get("company", cls.DEFAULT_COMPANY_ID)
            
            # ログイン状態も取得
            logged_in = st.query_params.get("logged_in", "false") == "true"
            
            return mode, company_id, logged_in
        except Exception as e:
            print(f"URLパラメータ取得エラー: {e}")
            return cls.DEFAULT_MODE, cls.DEFAULT_COMPANY_ID, False
    
    @classmethod
    def configure_page(cls, mode):
        """モードに応じてページ設定を行う"""
        if mode == "verify":
            config = {
                "page_title": "メール認証 - FAQ Bot",
                "page_icon": "📧",
                "layout": "centered",
                "initial_sidebar_state": "collapsed"
            }
        elif mode == "reg":
            config = {
                "page_title": "企業登録 - FAQ Bot",
                "page_icon": "🏢",
                "layout": "centered",
                "initial_sidebar_state": "collapsed"
            }
        elif mode == "admin":
            config = {
                "page_title": "管理者ページ - FAQ Bot",
                "page_icon": "⚙️",
                "layout": "wide",
                "initial_sidebar_state": "expanded"
            }
        else:
            config = {
                "page_title": "FAQ Bot",
                "page_icon": "🤖",
                "layout": "wide",
                "initial_sidebar_state": "collapsed"
            }
        
        try:
            st.set_page_config(**config)
        except Exception as e:
            print(f"ページ設定エラー: {e}")
    
    @classmethod
    def load_anthropic_client(cls):
        """
        Anthropicクライアントを作成して返す
        
        Returns:
            anthropic.Anthropic or None: クライアントまたはNone（テストモード時）
        """
        if cls.is_test_mode():
            print("テストモードで実行中 - APIキーは不要です")
            return None
        
        # Streamlit Secretsを安全に確認
        api_key = None
        try:
            if hasattr(st, 'secrets') and isinstance(st.secrets, dict) and 'ANTHROPIC_API_KEY' in st.secrets:
                api_key = st.secrets['ANTHROPIC_API_KEY']
        except Exception as e:
            print(f"Streamlit Secretsの読み込みエラー: {e}")
        
        # Secretsからキーが取得できなかった場合は環境変数を確認
        if not api_key:
            api_key = cls.ANTHROPIC_API_KEY
        
        # APIキーが存在するか確認
        if not api_key:
            print("APIキーが設定されていないため、自動的にテストモードを有効化しました")
            os.environ["TEST_MODE"] = "true"
            cls.TEST_MODE = True
            return None
        
        # Anthropicクライアントを作成して返す
        try:
            client = anthropic.Anthropic(api_key=api_key)
            return client
        except Exception as e:
            print(f"Anthropicクライアント作成エラー: {e}")
            os.environ["TEST_MODE"] = "true"
            cls.TEST_MODE = True
            return None
    
    @classmethod
    def validate_company_id(cls, company_id):
        """会社IDの妥当性をチェック"""
        if not company_id:
            return False
        
        # 長さチェック
        if len(company_id) > 50:
            return False
        
        # 文字種チェック（英数字、ハイフン、アンダースコアのみ）
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', company_id):
            return False
        
        return True
    
    @classmethod
    def validate_email(cls, email):
        """メールアドレスの妥当性をチェック"""
        if not email:
            return False
        
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @classmethod
    def generate_verification_url(cls, token):
        """認証用URLを生成"""
        return f"{cls.BASE_URL}/?mode=verify&token={token}"
    
    @classmethod
    def generate_admin_url(cls, company_id):
        """管理者用URLを生成"""
        return f"{cls.BASE_URL}/?mode=admin&company={company_id}"
    
    @classmethod
    def generate_user_url(cls, company_id):
        """ユーザー用URLを生成"""
        return f"{cls.BASE_URL}/?mode=user&company={company_id}"


# 後方互換性のためのエイリアス
AppConfig = UnifiedConfig

# よく使用される関数のショートカット
get_url_params = UnifiedConfig.get_url_params
configure_page = UnifiedConfig.configure_page
is_test_mode = UnifiedConfig.is_test_mode
get_data_path = UnifiedConfig.get_data_path
load_api_key = UnifiedConfig.load_anthropic_client  # 旧関数名との互換性
