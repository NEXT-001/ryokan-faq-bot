"""
定数とユーティリティ関数
utils/constants.py
"""
import os
import streamlit as st

# ディレクトリパス定数
DATA_DIR = "data"
COMPANIES_DIR = os.path.join(DATA_DIR, "companies")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

# データベース関連の定数
DB_NAME = "faq_database.db"
DB_PATH = os.path.join("data", DB_NAME)

# アプリケーション情報
APP_NAME = "FAQ Bot"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "FAQ自動応答システム"

# ファイル名定数
# SETTINGS_FILE = "settings.json"
FAQ_FILE = "faq.csv"
CHAT_HISTORY_FILE = "chat_history.json"
USER_DATA_FILE = "users.json"
COMPANIES_FILE = "companies.json"

# デフォルト値
DEFAULT_COMPANY_ID = "demo-company"
DEFAULT_MODE = "user"
DEFAULT_FAQ_COUNT = 0
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_EMAIL = "admin@example.com"

# システム設定
MAX_FILE_SIZE_MB = 10
SUPPORTED_FILE_TYPES = [".csv", ".json", ".txt"]
MAX_CHAT_HISTORY = 100
SESSION_TIMEOUT_MINUTES = 30

# UI関連の定数
SIDEBAR_WIDTH = 300
PAGE_TITLE_MAX_LENGTH = 50
COMPANY_NAME_MAX_LENGTH = 100

# セキュリティ設定
PASSWORD_MIN_LENGTH = 6
SESSION_KEY_LENGTH = 32

# API設定
DEFAULT_API_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3

def get_url_params():
    """URLパラメータを取得する"""
    try:
        mode = st.query_params.get("mode", DEFAULT_MODE)
        company_id = st.query_params.get("company_id", DEFAULT_COMPANY_ID)
        logged_in = st.query_params.get("logged_in", "false") == "true"
        return mode, company_id, logged_in
    except Exception as e:
        print(f"[URL_PARAMS] URLパラメータ取得エラー: {e}")
        return DEFAULT_MODE, DEFAULT_COMPANY_ID, False

def setup_page_config(mode):
    """ページ設定を行う（一度だけ実行）"""
    if 'page_config_set' not in st.session_state:
        try:
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
                    "initial_sidebar_state": "expanded"
                }
            
            st.set_page_config(**config)
            st.session_state.page_config_set = True
            print(f"[PAGE_CONFIG] ページ設定完了: mode={mode}")
            
        except Exception as e:
            print(f"[PAGE_CONFIG] ページ設定エラー: {e}")

def is_test_mode():
    """テストモードかどうかを判定"""
    return os.environ.get("TEST_MODE", "false").lower() == "true"

def get_data_path(company_id=None):
    """
    会社IDに基づいたデータディレクトリのパスを取得する
    
    Args:
        company_id (str, optional): 会社ID。指定されない場合は共通データディレクトリを返す
        
    Returns:
        str: データディレクトリのパス
    """
    # 基本データディレクトリ
    base_path = "data"
    
    # データディレクトリが存在しない場合は作成
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    # 会社別データディレクトリ
    if company_id:
        company_path = os.path.join(base_path, "companies", company_id)
        
        # 会社別ディレクトリが存在しない場合は作成
        if not os.path.exists(company_path):
            os.makedirs(company_path)
            
        return company_path
    
    # 共通データディレクトリ
    return base_path

def ensure_directory_exists(directory_path):
    """ディレクトリが存在しない場合は作成する"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"[DIRECTORY] 作成しました: {directory_path}")
    return directory_path

def get_company_folder_path(company_id):
    """
    会社IDに基づいた会社フォルダのパスを取得する
    
    Args:
        company_id (str): 会社ID
        
    Returns:
        str: 会社フォルダのパス
    """
    company_path = os.path.join(COMPANIES_DIR, company_id)
    ensure_directory_exists(company_path)
    return company_path

def get_upload_folder_path(company_id=None):
    """アップロードフォルダのパスを取得"""
    if company_id:
        upload_path = os.path.join(get_company_folder_path(company_id), "uploads")
    else:
        upload_path = UPLOAD_DIR
    
    ensure_directory_exists(upload_path)
    return upload_path

def get_backup_folder_path(company_id=None):
    """バックアップフォルダのパスを取得"""
    if company_id:
        backup_path = os.path.join(get_company_folder_path(company_id), "backups")
    else:
        backup_path = BACKUP_DIR
    
    ensure_directory_exists(backup_path)
    return backup_path

def get_logs_folder_path(company_id=None):
    """ログフォルダのパスを取得"""
    if company_id:
        logs_path = os.path.join(get_company_folder_path(company_id), "logs")
    else:
        logs_path = LOGS_DIR
    
    ensure_directory_exists(logs_path)
    return logs_path

def get_faq_file_path(company_id):
    """FAQファイルのパスを取得"""
    return os.path.join(get_data_path(company_id), FAQ_FILE)

def get_companies_file_path():
    """企業情報ファイルのパスを取得"""
    return os.path.join(get_data_path(), COMPANIES_FILE)

def get_db_path(company_id=None):
    """データベースファイルのパスを取得"""
    if company_id:
        return os.path.join(get_data_path(company_id), DB_NAME)
    else:
        return os.path.join(get_data_path(), DB_NAME)

def validate_company_id(company_id):
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

def validate_email(email):
    """メールアドレスの妥当性をチェック"""
    if not email:
        return False
    
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def safe_import(module_name, function_name=None):
    """安全にモジュールをインポートする"""
    try:
        module = __import__(module_name, fromlist=[function_name] if function_name else [])
        if function_name:
            return getattr(module, function_name, None)
        return module
    except ImportError as e:
        print(f"[IMPORT_ERROR] {module_name}のインポートに失敗: {e}")
        return None
    except Exception as e:
        print(f"[IMPORT_ERROR] 予期しないエラー: {e}")
        return None

def get_absolute_path(relative_path):
    """相対パスから絶対パスを取得"""
    return os.path.abspath(relative_path)

def check_file_exists(file_path):
    """ファイルが存在するかチェック"""
    return os.path.exists(file_path) and os.path.isfile(file_path)

def check_directory_exists(directory_path):
    """ディレクトリが存在するかチェック"""
    return os.path.exists(directory_path) and os.path.isdir(directory_path)

def get_file_size(file_path):
    """ファイルサイズを取得（バイト単位）"""
    if check_file_exists(file_path):
        return os.path.getsize(file_path)
    return 0

def get_file_extension(file_path):
    """ファイルの拡張子を取得"""
    return os.path.splitext(file_path)[1].lower()

def is_allowed_file_type(filename):
    """許可されたファイルタイプかチェック"""
    return get_file_extension(filename) in SUPPORTED_FILE_TYPES

def generate_verification_url(company_id, token):
    """認証用URLを生成"""
    return f"{VERIFICATION_URL}&company_id={company_id}&token={token}"

def generate_admin_url(company_id):
    """管理者用URLを生成"""
    return f"{ADMIN_URL}&company_id={company_id}"

def generate_user_url(company_id):
    """ユーザー用URLを生成"""
    return f"{BASE_URL}/?company_id={company_id}"

def generate_login_url(company_id):
    """ログイン用URLを生成"""
    return f"{LOGIN_URL}&company_id={company_id}"

def generate_token(length=None):
    """ランダムトークンを生成"""
    import secrets
    import string
    
    if length is None:
        length = VERIFICATION_TOKEN_LENGTH
    
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def format_file_size(size_bytes):
    """ファイルサイズを人間が読みやすい形式に変換"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

# 環境変数の取得関数
def get_env_var(key, default=None):
    """環境変数を安全に取得"""
    return os.environ.get(key, default)

# ログレベル
LOG_LEVEL = get_env_var("LOG_LEVEL", "INFO")

# デバッグモード
DEBUG_MODE = get_env_var("DEBUG_MODE", "false").lower() == "true"

# メール設定関連
SMTP_USE_TLS = get_env_var("SMTP_USE_TLS", "true").lower() == "true"
SMTP_USERNAME = get_env_var("SMTP_USERNAME", "")
SMTP_PASSWORD = get_env_var("SMTP_PASSWORD", "")

# 認証・セキュリティ関連
TOKEN_EXPIRY_HOURS = 24
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

# URL関連の定数
BASE_URL = get_env_var("BASE_URL", "http://localhost:8501")
VERIFICATION_URL = f"{BASE_URL}/?mode=verify"
REGISTRATION_URL = f"{BASE_URL}/?mode=reg"
ADMIN_URL = f"{BASE_URL}/?mode=admin"
LOGIN_URL = f"{BASE_URL}/?mode=login"

# メール認証関連の定数
EMAIL_VERIFICATION_TIMEOUT_HOURS = 24
EMAIL_TEMPLATE_DIR = os.path.join("templates", "email")
VERIFICATION_TOKEN_LENGTH = 32

# よく使われるその他の定数（各ページモジュールで必要になる可能性）
ENCRYPTION_KEY = get_env_var("ENCRYPTION_KEY", "default_key_change_in_production")
JWT_SECRET = get_env_var("JWT_SECRET", "jwt_secret_key")
SMTP_SERVER = get_env_var("SMTP_SERVER", "localhost")
SMTP_PORT = int(get_env_var("SMTP_PORT", "587"))
EMAIL_FROM = get_env_var("EMAIL_FROM", "noreply@example.com")

# データベーステーブル名
TABLE_USERS = "users"
TABLE_COMPANIES = "companies" 
TABLE_FAQ = "faq"
TABLE_CHAT_HISTORY = "chat_history"

# ファイルアップロード設定
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'csv', 'txt', 'json'}

# ページ表示設定
ITEMS_PER_PAGE = 20
MAX_DISPLAY_LENGTH = 100

# エラーメッセージ
ERROR_INVALID_CREDENTIALS = "ユーザー名またはパスワードが間違っています"
ERROR_USER_NOT_FOUND = "ユーザーが見つかりません"
ERROR_COMPANY_NOT_FOUND = "企業が見つかりません"
ERROR_FILE_NOT_FOUND = "ファイルが見つかりません"
ERROR_PERMISSION_DENIED = "権限がありません"

# 成功メッセージ
SUCCESS_LOGIN = "ログインしました"
SUCCESS_LOGOUT = "ログアウトしました"
SUCCESS_REGISTRATION = "登録が完了しました"
SUCCESS_UPDATE = "更新が完了しました"
SUCCESS_DELETE = "削除が完了しました"