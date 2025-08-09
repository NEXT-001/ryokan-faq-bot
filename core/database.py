"""
データベース操作のコアモジュール
core/database.py
"""
import sqlite3
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from config.unified_config import UnifiedConfig
from utils.auth_utils import hash_password

# スレッドローカルストレージ
_local = threading.local()

def get_db_path():
    """データベースファイルのパスを取得"""
    base_dir = UnifiedConfig.get_data_path()
    return os.path.join(base_dir, UnifiedConfig.DB_NAME)

def get_db_connection():
    """データベース接続を取得（スレッドセーフ・改良版）"""
    if not hasattr(_local, 'connection') or _local.connection is None:
        db_path = get_db_path()
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        _local.connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=60.0,  # タイムアウト延長
            isolation_level=None  # autocommitモード
        )
        _local.connection.row_factory = sqlite3.Row  # 辞書ライクなアクセス
        
        # SQLiteの並行性を改善
        _local.connection.execute("PRAGMA journal_mode = WAL")  # WALモード
        _local.connection.execute("PRAGMA synchronous = NORMAL")  # パフォーマンス向上
        _local.connection.execute("PRAGMA cache_size = 10000")  # キャッシュサイズ増加
        _local.connection.execute("PRAGMA temp_store = MEMORY")  # メモリ使用
        
        # 外部キー制約を有効化
        _local.connection.execute("PRAGMA foreign_keys = ON")
        
        print(f"[DATABASE] 接続作成: {db_path}")
    
    return _local.connection

@contextmanager
def get_cursor():
    """カーソルを安全に取得するコンテキストマネージャ"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[DATABASE] エラーによりロールバック: {e}")
        raise
    finally:
        cursor.close()

def initialize_database():
    """データベースを初期化"""
    try:
        with get_cursor() as cursor:
            # 基本テーブルの作成
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    faq_count INTEGER DEFAULT 0,
                    last_updated TEXT NOT NULL,
                    prefecture TEXT,
                    city TEXT,
                    address TEXT,
                    postal_code TEXT,
                    phone TEXT,
                    website TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS company_admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
                    UNIQUE(company_id, username),
                    UNIQUE(company_id, email)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faq_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS line_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL UNIQUE,
                    channel_access_token TEXT,
                    channel_secret TEXT,
                    user_id TEXT,
                    low_similarity_threshold REAL DEFAULT 0.4,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faq_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    similarity_score REAL,
                    user_ip TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    user_info TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """)
            
            # インデックスの作成
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_admins_company_id ON company_admins(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_admins_email ON company_admins(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_faq_company_id ON faq_data(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_settings_company_id ON line_settings(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_faq_history_company_id ON faq_history(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_faq_history_created_at ON faq_history(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_company_id ON search_history(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at)")
            
        print("[DATABASE] データベース初期化完了")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 初期化エラー: {e}")
        return False

# =============================================================================
# company_service.py で必要な関数群を追加
# =============================================================================

# hash_password関数はutils.auth_utilsから使用

def init_company_tables():
    """会社関連テーブルを初期化（initialize_databaseのエイリアス）"""
    return initialize_database()

def save_company_to_db(company_id, company_name, created_at, faq_count=0, location_info=None):
    """会社情報をデータベースに保存（所在地情報対応）"""
    try:
        if created_at is None:
            created_at = datetime.now().isoformat()
        
        last_updated = datetime.now().isoformat()
        
        # 位置情報のデフォルト値
        if location_info is None:
            location_info = {}
        
        prefecture = location_info.get('prefecture')
        city = location_info.get('city')
        address = location_info.get('address')
        postal_code = location_info.get('postal_code')
        phone = location_info.get('phone')
        website = location_info.get('website')
        
        # 既存の会社が存在するかチェック
        if company_exists_in_db(company_id):
            # 既存の会社情報を更新（FAQデータを保持）
            query = """
                UPDATE companies 
                SET name = ?, last_updated = ?, prefecture = ?, city = ?, 
                    address = ?, postal_code = ?, phone = ?, website = ?
                WHERE id = ?
            """
            execute_query(query, (company_name, last_updated, prefecture, city, 
                                address, postal_code, phone, website, company_id))
            print(f"[DATABASE] 会社更新完了: {company_id}")
        else:
            # 新しい会社を作成
            query = """
                INSERT INTO companies (id, name, created_at, faq_count, last_updated,
                                     prefecture, city, address, postal_code, phone, website)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            execute_query(query, (company_id, company_name, created_at, faq_count, last_updated,
                                prefecture, city, address, postal_code, phone, website))
            print(f"[DATABASE] 会社作成完了: {company_id}")
        
        return True
        
    except Exception as e:
        print(f"[DATABASE] 会社保存エラー: {e}")
        return False


def get_company_location(company_id):
    """会社の所在地情報を取得"""
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT prefecture, city, address, postal_code, phone, website
                FROM companies WHERE id = ?
            """, (company_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'prefecture': result['prefecture'],
                    'city': result['city'],
                    'address': result['address'],
                    'postal_code': result['postal_code'],
                    'phone': result['phone'],
                    'website': result['website']
                }
            return None
            
    except Exception as e:
        print(f"[DATABASE] 会社所在地取得エラー: {e}")
        return None


def update_company_location(company_id, location_info):
    """会社の所在地情報を更新"""
    try:
        last_updated = datetime.now().isoformat()
        
        with get_cursor() as cursor:
            cursor.execute("""
                UPDATE companies 
                SET prefecture = ?, city = ?, address = ?, postal_code = ?, 
                    phone = ?, website = ?, last_updated = ?
                WHERE id = ?
            """, (
                location_info.get('prefecture'),
                location_info.get('city'),
                location_info.get('address'),
                location_info.get('postal_code'),
                location_info.get('phone'),
                location_info.get('website'),
                last_updated,
                company_id
            ))
            
            if cursor.rowcount > 0:
                print(f"[DATABASE] 会社所在地更新完了: {company_id}")
                return True
            else:
                print(f"[DATABASE] 会社が見つかりません: {company_id}")
                return False
                
    except Exception as e:
        print(f"[DATABASE] 会社所在地更新エラー: {e}")
        return False

def get_company_from_db(company_id):
    """会社情報をデータベースから取得"""
    try:
        query = "SELECT * FROM companies WHERE id = ?"
        result = fetch_dict_one(query, (company_id,))
        
        if result:
            return {
                "company_id": result["id"],
                "company_name": result["name"],
                "created_at": result["created_at"],
                "faq_count": result["faq_count"],
                "last_updated": result["last_updated"],
                "prefecture": result["prefecture"],
                "city": result["city"],
                "address": result["address"],
                "postal_code": result["postal_code"],
                "phone": result["phone"],
                "website": result["website"]
            }
        return None
        
    except Exception as e:
        print(f"[DATABASE] 会社取得エラー: {e}")
        return None

def save_company_admin_to_db(company_id, username, password, email, created_at):
    """会社管理者をusersテーブルに保存"""
    try:
        if created_at is None:
            created_at = datetime.now().isoformat()
        
        # 既存の管理者が存在するかチェック
        existing_query = "SELECT id FROM users WHERE company_id = ? AND name = ?"
        existing_admin = fetch_one(existing_query, (company_id, username))
        
        if existing_admin:
            # 既存の管理者情報を更新
            query = """
                UPDATE users 
                SET password = ?, email = ?
                WHERE company_id = ? AND name = ?
            """
            execute_query(query, (password, email, company_id, username))
            print(f"[DATABASE] 管理者更新完了: {company_id}/{username}")
        else:
            # 新しい管理者を作成
            query = """
                INSERT INTO users 
                (company_id, name, password, email, created_at, is_verified)
                VALUES (?, ?, ?, ?, ?, 1)
            """
            execute_query(query, (company_id, username, password, email, created_at))
            print(f"[DATABASE] 管理者作成完了: {company_id}/{username}")
        
        return True
        
    except Exception as e:
        print(f"[DATABASE] 管理者保存エラー: {e}")
        return False

def get_company_admins_from_db(company_id):
    """会社の管理者一覧をusersテーブルから取得"""
    try:
        query = "SELECT name, email, password, created_at FROM users WHERE company_id = ?"
        results = fetch_dict(query, (company_id,))
        
        admins = {}
        for row in results:
            admins[row["name"]] = {
                "password": row["password"],
                "email": row["email"],
                "created_at": row["created_at"]
            }
        
        return admins
        
    except Exception as e:
        print(f"[DATABASE] 管理者取得エラー: {e}")
        return {}

def delete_company_admins_from_db(company_id):
    """会社の全管理者をusersテーブルから削除"""
    try:
        query = "DELETE FROM users WHERE company_id = ?"
        execute_query(query, (company_id,))
        print(f"[DATABASE] 管理者削除完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 管理者削除エラー: {e}")
        return False

def get_all_companies_from_db():
    """全会社情報をデータベースから取得"""
    try:
        query = "SELECT * FROM companies"
        companies_data = fetch_dict(query)
        
        companies = {}
        for row in companies_data:
            company_id = row["id"]
            
            # 管理者情報を取得
            admins = get_company_admins_from_db(company_id)
            
            companies[company_id] = {
                "name": row["name"],
                "created_at": row["created_at"],
                "faq_count": row["faq_count"],
                "last_updated": row["last_updated"],
                "admins": admins
            }
        
        return companies
        
    except Exception as e:
        print(f"[DATABASE] 全会社取得エラー: {e}")
        return {}

def company_exists_in_db(company_id):
    """会社がデータベースに存在するかチェック"""
    try:
        query = "SELECT id FROM companies WHERE id = ?"
        result = fetch_one(query, (company_id,))
        return result is not None
        
    except Exception as e:
        print(f"[DATABASE] 会社存在チェックエラー: {e}")
        return False

def update_company_faq_count_in_db(company_id, count):
    """会社のFAQ数をデータベースで更新"""
    try:
        query = """
            UPDATE companies 
            SET faq_count = ?, last_updated = ?
            WHERE id = ?
        """
        last_updated = datetime.now().isoformat()
        
        execute_query(query, (count, last_updated, company_id))
        print(f"[DATABASE] FAQ数更新完了: {company_id} -> {count}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] FAQ数更新エラー: {e}")
        return False

# =============================================================================
# ユーザー認証関連の関数群
# =============================================================================

def init_db():
    """データベースを初期化（エイリアス）"""
    return initialize_database()

def verify_user_token(token):
    """ユーザートークンを検証（簡易実装）"""
    # TODO: 実際のトークン検証ロジックを実装
    print(f"[DATABASE] トークン検証: {token}")
    return False, None

def authenticate_user_by_email(email, password):
    """メールアドレスでユーザー認証"""
    try:
        hashed_password = hash_password(password)
        query = "SELECT * FROM users WHERE email = ? AND password = ?"
        result = fetch_dict_one(query, (email, hashed_password))
        
        if result:
            # companiesテーブルから会社名を取得
            company_info = get_company_from_db(result["company_id"])
            company_name = company_info["company_name"] if company_info else "不明な企業"
            
            return True, {
                "id": result["id"],
                "company_id": result["company_id"],
                "company_name": company_name,
                "name": result["name"],
                "email": result["email"]
            }
        return False, None
        
    except Exception as e:
        print(f"[DATABASE] ユーザー認証エラー: {e}")
        return False, None

def register_user_to_db(company_id, company_name, name, email, password):
    """ユーザーをデータベースに登録"""
    try:
        hashed_password = hash_password(password)
        query = """
            INSERT INTO users (company_id, company_name, name, email, password, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        created_at = datetime.now().isoformat()
        
        execute_query(query, (company_id, company_name, name, email, hashed_password, created_at))
        print(f"[DATABASE] ユーザー登録完了: {email}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] ユーザー登録エラー: {e}")
        return False

def delete_user_by_email(email):
    """メールアドレスでユーザーを削除"""
    try:
        query = "DELETE FROM users WHERE email = ?"
        execute_query(query, (email,))
        print(f"[DATABASE] ユーザー削除完了: {email}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] ユーザー削除エラー: {e}")
        return False

def get_existing_company_ids():
    """既存の会社IDリストを取得"""
    try:
        query = "SELECT id FROM companies"
        results = fetch_all(query)
        return [row[0] for row in results]
        
    except Exception as e:
        print(f"[DATABASE] 会社ID取得エラー: {e}")
        return []

def register_company_id(company_id):
    """会社IDを登録（簡易実装）"""
    # この関数は具体的な実装が不明なため、基本的な会社作成として実装
    try:
        if not company_exists_in_db(company_id):
            return save_company_to_db(
                company_id=company_id,
                company_name=f"企業_{company_id}",
                created_at=datetime.now().isoformat(),
                faq_count=0
            )
        return True
        
    except Exception as e:
        print(f"[DATABASE] 会社ID登録エラー: {e}")
        return False

# =============================================================================
# 既存の関数群（元のdatabase.pyから）
# =============================================================================

def execute_query(query, params=None):
    """クエリを実行（INSERT, UPDATE, DELETE用）"""
    try:
        with get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount
    except Exception as e:
        print(f"[DATABASE] クエリ実行エラー: {e}")
        print(f"[DATABASE] クエリ: {query}")
        print(f"[DATABASE] パラメータ: {params}")
        raise

def fetch_one(query, params=None):
    """単一の結果を取得"""
    try:
        with get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            return tuple(result) if result else None
    except Exception as e:
        print(f"[DATABASE] fetch_one エラー: {e}")
        print(f"[DATABASE] クエリ: {query}")
        print(f"[DATABASE] パラメータ: {params}")
        raise

def fetch_all(query, params=None):
    """複数の結果を取得"""
    try:
        with get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            return [tuple(row) for row in results]
    except Exception as e:
        print(f"[DATABASE] fetch_all エラー: {e}")
        print(f"[DATABASE] クエリ: {query}")
        print(f"[DATABASE] パラメータ: {params}")
        raise

def fetch_dict(query, params=None):
    """結果を辞書形式で取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # カラム名を取得
        columns = [description[0] for description in cursor.description]
        results = cursor.fetchall()
        
        cursor.close()
        
        # 辞書のリストに変換
        dict_results = []
        for row in results:
            dict_results.append(dict(zip(columns, row)))
        
        return dict_results
        
    except Exception as e:
        print(f"[DATABASE] fetch_dict エラー: {e}")
        raise

def fetch_dict_one(query, params=None):
    """単一の結果を辞書形式で取得"""
    results = fetch_dict(query, params)
    return results[0] if results else None

def close_connection():
    """データベース接続を閉じる"""
    if hasattr(_local, 'connection') and _local.connection is not None:
        _local.connection.close()
        _local.connection = None
        print("[DATABASE] 接続を閉じました")

def backup_database(backup_path=None):
    """データベースをバックアップ"""
    if backup_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_{timestamp}.db"
    
    try:
        source_conn = get_db_connection()
        backup_conn = sqlite3.connect(backup_path)
        
        source_conn.backup(backup_conn)
        backup_conn.close()
        
        print(f"[DATABASE] バックアップ完了: {backup_path}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] バックアップエラー: {e}")
        return False

def get_table_info(table_name):
    """テーブル情報を取得"""
    try:
        # SQLインジェクション対策: テーブル名をサニタイズ
        if not table_name.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Invalid table name")
        query = f"PRAGMA table_info({table_name})"
        return fetch_all(query)
    except Exception as e:
        print(f"[DATABASE] テーブル情報取得エラー: {e}")
        return []

def get_all_tables():
    """全テーブル名を取得"""
    try:
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        results = fetch_all(query)
        return [table[0] for table in results]
    except Exception as e:
        print(f"[DATABASE] テーブル一覧取得エラー: {e}")
        return []

def vacuum_database():
    """データベースを最適化"""
    try:
        conn = get_db_connection()
        conn.execute("VACUUM")
        print("[DATABASE] データベースの最適化完了")
        return True
    except Exception as e:
        print(f"[DATABASE] 最適化エラー: {e}")
        return False

def get_database_size():
    """データベースサイズを取得（バイト単位）"""
    try:
        db_path = get_db_path()
        if os.path.exists(db_path):
            return os.path.getsize(db_path)
        return 0
    except Exception as e:
        print(f"[DATABASE] サイズ取得エラー: {e}")
        return 0

def check_database_integrity():
    """データベースの整合性をチェック"""
    try:
        result = fetch_one("PRAGMA integrity_check")
        return result[0] == "ok" if result else False
    except Exception as e:
        print(f"[DATABASE] 整合性チェックエラー: {e}")
        return False

# =============================================================================
# LINE設定関連の関数群
# =============================================================================

def save_line_settings_to_db(company_id, channel_access_token, channel_secret, user_id, low_similarity_threshold=0.4):
    """LINE設定をデータベースに保存"""
    try:
        updated_at = datetime.now().isoformat()
        
        # 既存のLINE設定が存在するかチェック
        existing_query = "SELECT id FROM line_settings WHERE company_id = ?"
        existing_setting = fetch_one(existing_query, (company_id,))
        
        if existing_setting:
            # 既存のLINE設定を更新
            query = """
                UPDATE line_settings 
                SET channel_access_token = ?, channel_secret = ?, user_id = ?, 
                    low_similarity_threshold = ?, updated_at = ?
                WHERE company_id = ?
            """
            execute_query(query, (channel_access_token, channel_secret, user_id, 
                                low_similarity_threshold, updated_at, company_id))
            print(f"[DATABASE] LINE設定更新完了: {company_id}")
        else:
            # 新しいLINE設定を作成
            query = """
                INSERT INTO line_settings 
                (company_id, channel_access_token, channel_secret, user_id, low_similarity_threshold, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            execute_query(query, (company_id, channel_access_token, channel_secret, user_id, 
                                low_similarity_threshold, updated_at))
            print(f"[DATABASE] LINE設定作成完了: {company_id}")
        
        return True
        
    except Exception as e:
        print(f"[DATABASE] LINE設定保存エラー: {e}")
        return False

def get_line_settings_from_db(company_id):
    """LINE設定をデータベースから取得"""
    try:
        query = "SELECT * FROM line_settings WHERE company_id = ?"
        result = fetch_dict_one(query, (company_id,))
        
        if result:
            return {
                "channel_access_token": result["channel_access_token"],
                "channel_secret": result["channel_secret"],
                "user_id": result["user_id"],
                "low_similarity_threshold": result["low_similarity_threshold"]
            }
        return None
        
    except Exception as e:
        print(f"[DATABASE] LINE設定取得エラー: {e}")
        return None

def delete_line_settings_from_db(company_id):
    """LINE設定をデータベースから削除"""
    try:
        query = "DELETE FROM line_settings WHERE company_id = ?"
        execute_query(query, (company_id,))
        print(f"[DATABASE] LINE設定削除完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] LINE設定削除エラー: {e}")
        return False

# =============================================================================
# FAQデータ関連の関数群
# =============================================================================

def save_faq_to_db(company_id, question, answer):
    """FAQデータをデータベースに保存"""
    try:
        query = """
            INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """
        current_time = datetime.now().isoformat()
        
        execute_query(query, (company_id, question, answer, current_time, current_time))
        print(f"[DATABASE] FAQ保存完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] FAQ保存エラー: {e}")
        return False

def get_faq_data_from_db(company_id):
    """会社のFAQデータをデータベースから取得"""
    try:
        query = "SELECT id, question, answer, created_at, updated_at FROM faq_data WHERE company_id = ? ORDER BY created_at"
        results = fetch_dict(query, (company_id,))
        return results
        
    except Exception as e:
        print(f"[DATABASE] FAQデータ取得エラー: {e}")
        return []

def update_faq_in_db(faq_id, question, answer):
    """FAQデータを更新"""
    try:
        query = """
            UPDATE faq_data 
            SET question = ?, answer = ?, updated_at = ?
            WHERE id = ?
        """
        current_time = datetime.now().isoformat()
        
        execute_query(query, (question, answer, current_time, faq_id))
        print(f"[DATABASE] FAQ更新完了: {faq_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] FAQ更新エラー: {e}")
        return False

def delete_faq_from_db(faq_id):
    """FAQデータを削除"""
    try:
        query = "DELETE FROM faq_data WHERE id = ?"
        execute_query(query, (faq_id,))
        print(f"[DATABASE] FAQ削除完了: {faq_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] FAQ削除エラー: {e}")
        return False

def count_faq_data(company_id):
    """会社のFAQ数を取得"""
    try:
        query = "SELECT COUNT(*) FROM faq_data WHERE company_id = ?"
        result = fetch_one(query, (company_id,))
        return result[0] if result else 0
    except Exception as e:
        print(f"[DATABASE] FAQ数取得エラー: {e}")
        return 0

def delete_all_faq_data(company_id):
    """会社の全FAQデータを削除"""
    try:
        query = "DELETE FROM faq_data WHERE company_id = ?"
        execute_query(query, (company_id,))
        print(f"[DATABASE] 全FAQ削除完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 全FAQ削除エラー: {e}")
        return False

# =============================================================================
# FAQ履歴関連の関数群
# =============================================================================

def save_faq_history_to_db(company_id, question, answer, similarity_score=None, user_ip=None):
    """FAQ履歴をデータベースに保存"""
    try:
        query = """
            INSERT INTO faq_history 
            (company_id, question, answer, similarity_score, user_ip, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        created_at = datetime.now().isoformat()
        
        execute_query(query, (company_id, question, answer, similarity_score, user_ip, created_at))
        print(f"[DATABASE] FAQ履歴保存完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] FAQ履歴保存エラー: {e}")
        return False

def get_faq_history_from_db(company_id, limit=100):
    """FAQ履歴をデータベースから取得"""
    try:
        query = """
            SELECT * FROM faq_history 
            WHERE company_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        results = fetch_dict(query, (company_id, limit))
        return results
        
    except Exception as e:
        print(f"[DATABASE] FAQ履歴取得エラー: {e}")
        return []

def delete_faq_history_from_db(company_id):
    """FAQ履歴をデータベースから削除"""
    try:
        query = "DELETE FROM faq_history WHERE company_id = ?"
        execute_query(query, (company_id,))
        print(f"[DATABASE] FAQ履歴削除完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] FAQ履歴削除エラー: {e}")
        return False

def count_faq_history(company_id):
    """FAQ履歴の件数を取得"""
    try:
        query = "SELECT COUNT(*) FROM faq_history WHERE company_id = ?"
        result = fetch_one(query, (company_id,))
        return result[0] if result else 0
    except Exception as e:
        print(f"[DATABASE] FAQ履歴件数取得エラー: {e}")
        return 0

# =============================================================================
# 検索履歴関連の関数群
# =============================================================================

def save_search_history_to_db(company_id, question, answer, input_tokens=0, output_tokens=0, user_info=""):
    """検索履歴をデータベースに保存"""
    try:
        query = """
            INSERT INTO search_history 
            (company_id, user_info, question, answer, input_tokens, output_tokens, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        created_at = datetime.now().isoformat()
        
        execute_query(query, (company_id, user_info, question, answer, input_tokens, output_tokens, created_at))
        print(f"[DATABASE] 検索履歴保存完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 検索履歴保存エラー: {e}")
        return False

def get_search_history_from_db(company_id, limit=100):
    """検索履歴をデータベースから取得"""
    try:
        query = """
            SELECT * FROM search_history 
            WHERE company_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        """
        results = fetch_dict(query, (company_id, limit))
        return results
        
    except Exception as e:
        print(f"[DATABASE] 検索履歴取得エラー: {e}")
        return []

def cleanup_old_search_history(company_id=None, days=7):
    """古い検索履歴を削除（デフォルト7日間）"""
    try:
        from datetime import timedelta
        
        # 指定日数前の日時を計算
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()
        
        if company_id:
            # 特定の会社の古い履歴を削除
            query = "DELETE FROM search_history WHERE company_id = ? AND created_at < ?"
            rows_affected = execute_query(query, (company_id, cutoff_str))
        else:
            # 全会社の古い履歴を削除
            query = "DELETE FROM search_history WHERE created_at < ?"
            rows_affected = execute_query(query, (cutoff_str,))
        
        if rows_affected > 0:
            print(f"[DATABASE] 古い検索履歴を{rows_affected}件削除しました")
        
        return True
        
    except Exception as e:
        print(f"[DATABASE] 検索履歴クリーンアップエラー: {e}")
        return False

def delete_search_history_from_db(company_id):
    """検索履歴をデータベースから削除"""
    try:
        query = "DELETE FROM search_history WHERE company_id = ?"
        execute_query(query, (company_id,))
        print(f"[DATABASE] 検索履歴削除完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 検索履歴削除エラー: {e}")
        return False

def count_search_history(company_id):
    """検索履歴の件数を取得"""
    try:
        query = "SELECT COUNT(*) FROM search_history WHERE company_id = ?"
        result = fetch_one(query, (company_id,))
        return result[0] if result else 0
    except Exception as e:
        print(f"[DATABASE] 検索履歴件数取得エラー: {e}")
        return 0

# 便利な関数
def table_exists(table_name):
    """テーブルが存在するかチェック"""
    try:
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = fetch_one(query, (table_name,))
        return result is not None
    except Exception as e:
        print(f"[DATABASE] テーブル存在チェックエラー: {e}")
        return False

def count_records(table_name, where_clause=None, params=None):
    """レコード数を取得"""
    try:
        # SQLインジェクション対策: テーブル名をサニタイズ
        if not table_name.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Invalid table name")
            
        if where_clause:
            query = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
        else:
            query = f"SELECT COUNT(*) FROM {table_name}"
        
        result = fetch_one(query, params)
        return result[0] if result else 0
    except Exception as e:
        print(f"[DATABASE] レコード数取得エラー: {e}")
        return 0

# 初期化時にデータベースを準備
def init_db_if_needed():
    """必要に応じてデータベースを初期化"""
    try:
        db_path = get_db_path()
        
        # データベースファイルが存在しない場合、または空の場合
        if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
            print("[DATABASE] データベースファイルが存在しないため、初期化します")
            return initialize_database()
        
        # テーブルが存在するかチェック
        if not table_exists("companies"):
            print("[DATABASE] 必要なテーブルが存在しないため、初期化します")
            return initialize_database()
        
        print("[DATABASE] 既存のデータベースを使用します")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 初期化チェックエラー: {e}")
        return False

# データベース接続テスト
def test_connection():
    """データベース接続をテスト"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        
        success = result is not None
        print(f"[DATABASE] 接続テスト: {'成功' if success else '失敗'}")
        return success
        
    except Exception as e:
        print(f"[DATABASE] 接続テストエラー: {e}")
        return False

def update_company_admin_password_in_db(company_id, new_password):
    """会社管理者のパスワードをデータベースで更新"""
    try:
        hashed_password = hash_password(new_password)
        query = """
            UPDATE users 
            SET password = ?
            WHERE company_id = ?
        """
        
        rows_affected = execute_query(query, (hashed_password, company_id))
        
        if rows_affected > 0:
            print(f"[DATABASE] パスワード更新完了: {company_id} ({rows_affected}件)")
            return True
        else:
            print(f"[DATABASE] パスワード更新失敗: 管理者が見つかりません {company_id}")
            return False
        
    except Exception as e:
        print(f"[DATABASE] パスワード更新エラー: {e}")
        return False

def verify_company_admin_exists(company_id):
    """会社管理者が存在するかチェック"""
    try:
        query = "SELECT name FROM users WHERE company_id = ?"
        result = fetch_all(query, (company_id,))
        return len(result) > 0
        
    except Exception as e:
        print(f"[DATABASE] 管理者存在チェックエラー: {e}")
        return False

def update_company_name_in_db(company_id, new_company_name):
    """会社名をcompaniesテーブルのみで更新"""
    try:
        # companiesテーブルのみを更新
        query = "UPDATE companies SET name = ? WHERE id = ?"
        rows_affected = execute_query(query, (new_company_name, company_id))
        
        if rows_affected > 0:
            print(f"[DATABASE] 会社名更新完了: {company_id} -> {new_company_name}")
            return True
        else:
            print(f"[DATABASE] 会社名更新失敗: 会社が見つかりません {company_id}")
            return False
        
    except Exception as e:
        print(f"[DATABASE] 会社名更新エラー: {e}")
        return False

def update_username_in_db(company_id, old_username, new_username):
    """ユーザー名をデータベースで更新"""
    try:
        # usersテーブルを更新
        query = "UPDATE users SET name = ? WHERE company_id = ? AND name = ?"
        rows_affected = execute_query(query, (new_username, company_id, old_username))
        
        if rows_affected > 0:
            print(f"[DATABASE] ユーザー名更新完了: {old_username} -> {new_username}")
            return True
        else:
            print(f"[DATABASE] ユーザー名更新失敗: ユーザーが見つかりません {old_username}")
            return False
        
    except Exception as e:
        print(f"[DATABASE] ユーザー名更新エラー: {e}")
        return False
    
# モジュール読み込み時に初期化
if __name__ != "__main__":
    init_db_if_needed()
