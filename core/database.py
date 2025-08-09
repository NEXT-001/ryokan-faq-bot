"""
データベース操作のコアモジュール（PostgreSQL/SQLite対応）
core/database.py
"""
import os
import threading
from contextlib import contextmanager
from datetime import datetime
from config.unified_config import UnifiedConfig
from utils.auth_utils import hash_password

import sqlite3

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import sql
    DB_TYPE = "postgresql"
except ImportError:
    DB_TYPE = "sqlite"
    print("[DATABASE] PostgreSQL未インストール、SQLiteを使用します")

# スレッドローカルストレージ
_local = threading.local()

def get_db_config():
    """データベース接続設定を取得"""
    if DB_TYPE == "postgresql":
        return {
            'host': os.getenv('DATABASE_HOST', 'localhost'),
            'port': os.getenv('DATABASE_PORT', '5432'),
            'database': os.getenv('DATABASE_NAME', 'ryokan_faq'),
            'user': os.getenv('DATABASE_USER', 'postgres'),
            'password': os.getenv('DATABASE_PASSWORD', 'postgres'),
        }
    else:
        # SQLite fallback
        base_dir = UnifiedConfig.get_data_path()
        return os.path.join(base_dir, UnifiedConfig.DB_NAME)

def get_db_connection():
    """データベース接続を取得（PostgreSQL/SQLite対応）"""
    global DB_TYPE
    
    if not hasattr(_local, 'connection') or _local.connection is None:
        if DB_TYPE == "postgresql":
            config = get_db_config()
            try:
                _local.connection = psycopg2.connect(
                    host=config['host'],
                    port=config['port'],
                    database=config['database'],
                    user=config['user'],
                    password=config['password'],
                    connect_timeout=60
                )
                _local.connection.autocommit = True
                print(f"[DATABASE] PostgreSQL接続作成: {config['host']}:{config['port']}/{config['database']}")
            except Exception as e:
                print(f"[DATABASE] PostgreSQL接続エラー: {e}")
                print("[DATABASE] SQLiteにフォールバック")
                # PostgreSQL接続失敗時はSQLiteにフォールバック
                DB_TYPE = "sqlite"
                
        if DB_TYPE == "sqlite":
            db_path = get_db_config()
            
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            _local.connection = sqlite3.connect(
                db_path,
                check_same_thread=False,
                timeout=60.0,
                isolation_level=None  # autocommitモード
            )
            _local.connection.row_factory = sqlite3.Row
            
            # SQLiteの並行性を改善
            _local.connection.execute("PRAGMA journal_mode = WAL")
            _local.connection.execute("PRAGMA synchronous = NORMAL")
            _local.connection.execute("PRAGMA cache_size = 10000")
            _local.connection.execute("PRAGMA temp_store = MEMORY")
            _local.connection.execute("PRAGMA foreign_keys = ON")
            
            print(f"[DATABASE] SQLite接続作成: {db_path}")
    
    return _local.connection

@contextmanager
def get_cursor():
    """カーソルを安全に取得するコンテキストマネージャ（PostgreSQL/SQLite対応）"""
    conn = get_db_connection()
    
    if DB_TYPE == "postgresql":
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor()
    
    try:
        yield cursor
        if DB_TYPE == "sqlite":
            conn.commit()
        # PostgreSQLはautocommitモードなのでcommit不要
    except Exception as e:
        if DB_TYPE == "sqlite":
            conn.rollback()
        elif DB_TYPE == "postgresql":
            conn.rollback()
        print(f"[DATABASE] エラーによりロールバック: {e}")
        raise
    finally:
        cursor.close()

def get_create_table_sql():
    """データベースタイプに応じたCREATE TABLE SQLを返す"""
    if DB_TYPE == "postgresql":
        return {
            'companies': """
                CREATE TABLE IF NOT EXISTS companies (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    faq_count INTEGER DEFAULT 0,
                    last_updated TIMESTAMP NOT NULL,
                    prefecture TEXT,
                    city TEXT,
                    address TEXT,
                    postal_code TEXT,
                    phone TEXT,
                    website TEXT
                )
            """,
            'company_admins': """
                CREATE TABLE IF NOT EXISTS company_admins (
                    id SERIAL PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE,
                    UNIQUE(company_id, username),
                    UNIQUE(company_id, email)
                )
            """,
            'users': """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 0,
                    verify_token TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """,
            'faq_data': """
                CREATE TABLE IF NOT EXISTS faq_data (
                    id SERIAL PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """,
            'line_settings': """
                CREATE TABLE IF NOT EXISTS line_settings (
                    id SERIAL PRIMARY KEY,
                    company_id TEXT NOT NULL UNIQUE,
                    channel_access_token TEXT,
                    channel_secret TEXT,
                    user_id TEXT,
                    low_similarity_threshold REAL DEFAULT 0.4,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """,
            'faq_history': """
                CREATE TABLE IF NOT EXISTS faq_history (
                    id SERIAL PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    similarity_score REAL,
                    user_ip TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """,
            'search_history': """
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    user_info TEXT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """
        }
    else:  # SQLite
        return {
            'companies': """
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
            """,
            'company_admins': """
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
            """,
            'users': """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    is_verified INTEGER DEFAULT 0,
                    verify_token TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """,
            'faq_data': """
                CREATE TABLE IF NOT EXISTS faq_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
                )
            """,
            'line_settings': """
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
            """,
            'faq_history': """
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
            """,
            'search_history': """
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
            """
        }

def initialize_database():
    """データベースを初期化（PostgreSQL/SQLite対応）"""
    try:
        with get_cursor() as cursor:
            # データベースタイプに応じたSQLを取得
            table_sqls = get_create_table_sql()
            
            # 各テーブルを作成
            for table_name, sql in table_sqls.items():
                cursor.execute(sql)
                print(f"[DATABASE] テーブル作成/確認: {table_name}")
            
            print(f"[DATABASE] データベース初期化完了 ({DB_TYPE})")
            
    except Exception as e:
        print(f"[DATABASE] 初期化エラー: {e}")
        raise

# =============================================================================
# 基本的なデータベース操作関数
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
        raise

def fetch_dict(query, params=None):
    """結果を辞書形式で取得"""
    try:
        with get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            
            # 辞書のリストに変換
            if DB_TYPE == "postgresql":
                # PostgreSQLのRealDictCursorは既に辞書
                return [dict(row) for row in results]
            else:
                # SQLiteの場合は手動で辞書に変換
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in results]
            
    except Exception as e:
        print(f"[DATABASE] fetch_dict エラー: {e}")
        raise

def fetch_dict_one(query, params=None):
    """単一の結果を辞書形式で取得"""
    results = fetch_dict(query, params)
    return results[0] if results else None

# =============================================================================
# 会社関連の関数
# =============================================================================

def save_company_to_db(company_id, company_name, created_at=None, faq_count=0, last_updated=None, prefecture=None, city=None, address=None, postal_code=None, phone=None, website=None):
    """会社をデータベースに保存"""
    try:
        if created_at is None:
            created_at = datetime.now() if DB_TYPE == "postgresql" else datetime.now().isoformat()
        if last_updated is None:
            last_updated = datetime.now() if DB_TYPE == "postgresql" else datetime.now().isoformat()
            
        if DB_TYPE == "postgresql":
            query = """
                INSERT INTO companies (id, name, created_at, faq_count, last_updated, prefecture, city, address, postal_code, phone, website)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    faq_count = EXCLUDED.faq_count,
                    last_updated = EXCLUDED.last_updated,
                    prefecture = EXCLUDED.prefecture,
                    city = EXCLUDED.city,
                    address = EXCLUDED.address,
                    postal_code = EXCLUDED.postal_code,
                    phone = EXCLUDED.phone,
                    website = EXCLUDED.website
            """
        else:
            query = """
                INSERT OR REPLACE INTO companies 
                (id, name, created_at, faq_count, last_updated, prefecture, city, address, postal_code, phone, website)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
        
        execute_query(query, (company_id, company_name, created_at, faq_count, last_updated, prefecture, city, address, postal_code, phone, website))
        print(f"[DATABASE] 会社保存完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 会社保存エラー: {e}")
        return False

def get_all_companies_from_db():
    """すべての会社一覧を取得"""
    try:
        query = "SELECT * FROM companies ORDER BY created_at DESC"
        results = fetch_dict(query)
        
        companies = []
        for row in results:
            companies.append({
                "company_id": row["id"],
                "company_name": row["name"],
                "created_at": row["created_at"],
                "faq_count": row["faq_count"],
                "last_updated": row["last_updated"],
                "prefecture": row.get("prefecture"),
                "city": row.get("city"),
                "address": row.get("address"),
                "postal_code": row.get("postal_code"),
                "phone": row.get("phone"),
                "website": row.get("website")
            })
        
        return companies
        
    except Exception as e:
        print(f"[DATABASE] 会社一覧取得エラー: {e}")
        return []

def save_company_admin_to_db(company_id, username, password, email):
    """会社管理者をデータベースに保存"""
    try:
        hashed_password = hash_password(password)
        
        if DB_TYPE == "postgresql":
            query = """
                INSERT INTO company_admins (company_id, username, password, email, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (company_id, username) DO UPDATE SET
                    password = EXCLUDED.password,
                    email = EXCLUDED.email
            """
            created_at = datetime.now()
        else:
            query = """
                INSERT OR REPLACE INTO company_admins (company_id, username, password, email, created_at)
                VALUES (?, ?, ?, ?, ?)
            """
            created_at = datetime.now().isoformat()
        
        execute_query(query, (company_id, username, hashed_password, email, created_at))
        print(f"[DATABASE] 管理者保存完了: {company_id}/{username}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 管理者保存エラー: {e}")
        return False

def update_company_faq_count_in_db(company_id, faq_count):
    """会社のFAQ件数を更新"""
    try:
        if DB_TYPE == "postgresql":
            query = "UPDATE companies SET faq_count = %s, last_updated = %s WHERE id = %s"
            last_updated = datetime.now()
        else:
            query = "UPDATE companies SET faq_count = ?, last_updated = ? WHERE id = ?"
            last_updated = datetime.now().isoformat()
        
        execute_query(query, (faq_count, last_updated, company_id))
        print(f"[DATABASE] FAQ件数更新完了: {company_id} = {faq_count}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] FAQ件数更新エラー: {e}")
        return False

def get_company_from_db(company_id):
    """会社情報をデータベースから取得"""
    try:
        query = "SELECT * FROM companies WHERE id = %s" if DB_TYPE == "postgresql" else "SELECT * FROM companies WHERE id = ?"
        result = fetch_dict_one(query, (company_id,))
        
        if result:
            return {
                "company_id": result["id"],
                "company_name": result["name"],
                "created_at": result["created_at"],
                "faq_count": result["faq_count"],
                "last_updated": result["last_updated"],
                "prefecture": result.get("prefecture"),
                "city": result.get("city"),
                "address": result.get("address"),
                "postal_code": result.get("postal_code"),
                "phone": result.get("phone"),
                "website": result.get("website")
            }
        return None
        
    except Exception as e:
        print(f"[DATABASE] 会社取得エラー: {e}")
        return None

def company_exists_in_db(company_id):
    """会社がデータベースに存在するかチェック"""
    try:
        query = "SELECT id FROM companies WHERE id = %s" if DB_TYPE == "postgresql" else "SELECT id FROM companies WHERE id = ?"
        result = fetch_one(query, (company_id,))
        return result is not None
        
    except Exception as e:
        print(f"[DATABASE] 会社存在チェックエラー: {e}")
        return False

# =============================================================================
# ユーザー認証関連の関数
# =============================================================================

def update_company_admin_password_in_db(company_id, username, new_password):
    """会社管理者のパスワードを更新"""
    try:
        hashed_password = hash_password(new_password)
        
        if DB_TYPE == "postgresql":
            query = "UPDATE company_admins SET password = %s WHERE company_id = %s AND username = %s"
        else:
            query = "UPDATE company_admins SET password = ? WHERE company_id = ? AND username = ?"
        
        execute_query(query, (hashed_password, company_id, username))
        print(f"[DATABASE] 管理者パスワード更新完了: {company_id}/{username}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 管理者パスワード更新エラー: {e}")
        return False

def verify_company_admin_exists(company_id):
    """会社の管理者が存在するかチェック"""
    try:
        query = "SELECT COUNT(*) as count FROM company_admins WHERE company_id = %s" if DB_TYPE == "postgresql" else "SELECT COUNT(*) as count FROM company_admins WHERE company_id = ?"
        result = fetch_dict_one(query, (company_id,))
        return result["count"] > 0 if result else False
        
    except Exception as e:
        print(f"[DATABASE] 管理者存在チェックエラー: {e}")
        return False

def update_company_name_in_db(company_id, new_company_name):
    """会社名を更新"""
    try:
        if DB_TYPE == "postgresql":
            query = "UPDATE companies SET name = %s, last_updated = %s WHERE id = %s"
            last_updated = datetime.now()
        else:
            query = "UPDATE companies SET name = ?, last_updated = ? WHERE id = ?"
            last_updated = datetime.now().isoformat()
        
        execute_query(query, (new_company_name, last_updated, company_id))
        print(f"[DATABASE] 会社名更新完了: {company_id} = {new_company_name}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 会社名更新エラー: {e}")
        return False

def update_username_in_db(company_id, current_username, new_username):
    """ユーザー名を更新"""
    try:
        if DB_TYPE == "postgresql":
            query = "UPDATE company_admins SET username = %s WHERE company_id = %s AND username = %s"
        else:
            query = "UPDATE company_admins SET username = ? WHERE company_id = ? AND username = ?"
        
        execute_query(query, (new_username, company_id, current_username))
        print(f"[DATABASE] ユーザー名更新完了: {company_id} {current_username} -> {new_username}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] ユーザー名更新エラー: {e}")
        return False

def authenticate_user_by_email(email, password):
    """メールアドレスでユーザー認証"""
    try:
        hashed_password = hash_password(password)
        query = "SELECT * FROM users WHERE email = %s AND password = %s AND is_verified = 1" if DB_TYPE == "postgresql" else "SELECT * FROM users WHERE email = ? AND password = ? AND is_verified = 1"
        result = fetch_dict_one(query, (email, hashed_password))
        
        if result:
            # companiesテーブルから会社名を取得
            company_info = get_company_from_db(result["company_id"])
            company_name = company_info["company_name"] if company_info else result.get("company_name", "不明な企業")
            
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
        
        if DB_TYPE == "postgresql":
            query = """
                INSERT INTO users (company_id, company_name, name, email, password, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            created_at = datetime.now()
        else:
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
        query = "DELETE FROM users WHERE email = %s" if DB_TYPE == "postgresql" else "DELETE FROM users WHERE email = ?"
        execute_query(query, (email,))
        print(f"[DATABASE] ユーザー削除完了: {email}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] ユーザー削除エラー: {e}")
        return False

def get_company_admins_from_db(company_id):
    """会社の管理者一覧をusersテーブルから取得"""
    try:
        query = "SELECT name, email, password, created_at FROM users WHERE company_id = %s" if DB_TYPE == "postgresql" else "SELECT name, email, password, created_at FROM users WHERE company_id = ?"
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

# =============================================================================
# LINE設定関連の関数
# =============================================================================

def save_line_settings_to_db(company_id, channel_access_token, channel_secret, user_id, low_similarity_threshold=0.4):
    """LINE設定をデータベースに保存"""
    try:
        # 既存の設定があるかチェック
        existing = get_line_settings_from_db(company_id)
        
        if existing:
            # 更新
            if DB_TYPE == "postgresql":
                query = """
                    UPDATE line_settings 
                    SET channel_access_token = %s, channel_secret = %s, user_id = %s, 
                        low_similarity_threshold = %s, updated_at = %s
                    WHERE company_id = %s
                """
                updated_at = datetime.now()
            else:
                query = """
                    UPDATE line_settings 
                    SET channel_access_token = ?, channel_secret = ?, user_id = ?, 
                        low_similarity_threshold = ?, updated_at = ?
                    WHERE company_id = ?
                """
                updated_at = datetime.now().isoformat()
            
            execute_query(query, (channel_access_token, channel_secret, user_id, 
                                low_similarity_threshold, updated_at, company_id))
        else:
            # 新規作成
            if DB_TYPE == "postgresql":
                query = """
                    INSERT INTO line_settings 
                    (company_id, channel_access_token, channel_secret, user_id, low_similarity_threshold, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                created_at = updated_at = datetime.now()
            else:
                query = """
                    INSERT INTO line_settings 
                    (company_id, channel_access_token, channel_secret, user_id, low_similarity_threshold, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """
                created_at = updated_at = datetime.now().isoformat()
            
            execute_query(query, (company_id, channel_access_token, channel_secret, user_id,
                                low_similarity_threshold, created_at, updated_at))
        
        print(f"[DATABASE] LINE設定保存完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] LINE設定保存エラー: {e}")
        return False

def get_line_settings_from_db(company_id):
    """データベースからLINE設定を取得"""
    try:
        query = "SELECT * FROM line_settings WHERE company_id = %s" if DB_TYPE == "postgresql" else "SELECT * FROM line_settings WHERE company_id = ?"
        result = fetch_dict_one(query, (company_id,))
        
        if result:
            return {
                "company_id": result["company_id"],
                "channel_access_token": result["channel_access_token"],
                "channel_secret": result["channel_secret"],
                "user_id": result["user_id"],
                "low_similarity_threshold": result["low_similarity_threshold"],
                "created_at": result["created_at"],
                "updated_at": result["updated_at"]
            }
        return None
        
    except Exception as e:
        print(f"[DATABASE] LINE設定取得エラー: {e}")
        return None

# =============================================================================
# 検索履歴関連の関数
# =============================================================================

def save_search_history_to_db(company_id, user_info, question, answer, input_tokens=0, output_tokens=0):
    """検索履歴をデータベースに保存"""
    try:
        if DB_TYPE == "postgresql":
            query = """
                INSERT INTO search_history (company_id, user_info, question, answer, input_tokens, output_tokens, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            created_at = datetime.now()
        else:
            query = """
                INSERT INTO search_history (company_id, user_info, question, answer, input_tokens, output_tokens, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            created_at = datetime.now().isoformat()
        
        execute_query(query, (company_id, user_info, question, answer, input_tokens, output_tokens, created_at))
        return True
        
    except Exception as e:
        print(f"[DATABASE] 検索履歴保存エラー: {e}")
        return False

def get_search_history_from_db(company_id, limit=20):
    """検索履歴をデータベースから取得"""
    try:
        if DB_TYPE == "postgresql":
            query = "SELECT * FROM search_history WHERE company_id = %s ORDER BY created_at DESC LIMIT %s"
        else:
            query = "SELECT * FROM search_history WHERE company_id = ? ORDER BY created_at DESC LIMIT ?"
        
        results = fetch_dict(query, (company_id, limit))
        return results
        
    except Exception as e:
        print(f"[DATABASE] 検索履歴取得エラー: {e}")
        return []

def cleanup_old_search_history(company_id=None, days=7):
    """古い検索履歴を削除"""
    try:
        from datetime import timedelta
        
        if DB_TYPE == "postgresql":
            # PostgreSQLでは文字列として保存されているかもしれないので、両方に対応
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()
            
            if company_id:
                # 文字列として保存されている場合に対応
                query = """
                    DELETE FROM search_history 
                    WHERE company_id = %s 
                    AND (
                        (created_at::text < %s) 
                        OR 
                        (created_at::timestamp < %s)
                    )
                """
                params = (company_id, cutoff_str, cutoff_date)
            else:
                query = """
                    DELETE FROM search_history 
                    WHERE (
                        (created_at::text < %s) 
                        OR 
                        (created_at::timestamp < %s)
                    )
                """
                params = (cutoff_str, cutoff_date)
        else:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            if company_id:
                query = "DELETE FROM search_history WHERE company_id = ? AND created_at < ?"
                params = (company_id, cutoff_date)
            else:
                query = "DELETE FROM search_history WHERE created_at < ?"
                params = (cutoff_date,)
        
        rows_deleted = execute_query(query, params)
        print(f"[DATABASE] 古い検索履歴削除完了: {rows_deleted}件")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 検索履歴削除エラー: {e}")
        # より安全なアプローチ: 文字列として比較
        try:
            from datetime import timedelta
            cutoff_str = (datetime.now() - timedelta(days=days)).isoformat()
            
            if DB_TYPE == "postgresql":
                if company_id:
                    query = "DELETE FROM search_history WHERE company_id = %s AND created_at < %s"
                    params = (company_id, cutoff_str)
                else:
                    query = "DELETE FROM search_history WHERE created_at < %s"
                    params = (cutoff_str,)
            else:
                if company_id:
                    query = "DELETE FROM search_history WHERE company_id = ? AND created_at < ?"
                    params = (company_id, cutoff_str)
                else:
                    query = "DELETE FROM search_history WHERE created_at < ?"
                    params = (cutoff_str,)
            
            rows_deleted = execute_query(query, params)
            print(f"[DATABASE] 古い検索履歴削除完了（文字列比較）: {rows_deleted}件")
            return True
            
        except Exception as e2:
            print(f"[DATABASE] 検索履歴削除エラー（再試行も失敗）: {e2}")
            return False

def count_search_history(company_id):
    """検索履歴の件数を取得"""
    try:
        query = "SELECT COUNT(*) as count FROM search_history WHERE company_id = %s" if DB_TYPE == "postgresql" else "SELECT COUNT(*) as count FROM search_history WHERE company_id = ?"
        result = fetch_dict_one(query, (company_id,))
        return result["count"] if result else 0
        
    except Exception as e:
        print(f"[DATABASE] 検索履歴件数取得エラー: {e}")
        return 0

# =============================================================================
# その他のユーティリティ関数
# =============================================================================

def count_records(table_name, company_id=None):
    """レコード数を取得"""
    try:
        if company_id:
            query = f"SELECT COUNT(*) as count FROM {table_name} WHERE company_id = %s" if DB_TYPE == "postgresql" else f"SELECT COUNT(*) as count FROM {table_name} WHERE company_id = ?"
            result = fetch_dict_one(query, (company_id,))
        else:
            query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = fetch_dict_one(query)
        
        return result["count"] if result else 0
        
    except Exception as e:
        print(f"[DATABASE] レコード数取得エラー: {e}")
        return 0

def get_db_path():
    """データベースパスを取得（SQLite用）"""
    if DB_TYPE == "sqlite":
        return get_db_config()
    else:
        return None

def update_company_location(company_id, prefecture, city, address, postal_code):
    """会社の所在地情報を更新"""
    try:
        if DB_TYPE == "postgresql":
            query = """
                UPDATE companies 
                SET prefecture = %s, city = %s, address = %s, postal_code = %s, last_updated = %s 
                WHERE id = %s
            """
            last_updated = datetime.now()
        else:
            query = """
                UPDATE companies 
                SET prefecture = ?, city = ?, address = ?, postal_code = ?, last_updated = ? 
                WHERE id = ?
            """
            last_updated = datetime.now().isoformat()
        
        execute_query(query, (prefecture, city, address, postal_code, last_updated, company_id))
        print(f"[DATABASE] 会社所在地更新完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 会社所在地更新エラー: {e}")
        return False

def get_company_location(company_id):
    """会社の所在地情報を取得"""
    try:
        query = "SELECT prefecture, city, address, postal_code FROM companies WHERE id = %s" if DB_TYPE == "postgresql" else "SELECT prefecture, city, address, postal_code FROM companies WHERE id = ?"
        result = fetch_dict_one(query, (company_id,))
        
        if result:
            return {
                "prefecture": result["prefecture"],
                "city": result["city"],
                "address": result["address"],
                "postal_code": result["postal_code"]
            }
        return None
        
    except Exception as e:
        print(f"[DATABASE] 会社所在地取得エラー: {e}")
        return None

# =============================================================================
# ユーティリティ関数
# =============================================================================

def table_exists(table_name):
    """テーブルが存在するかチェック"""
    try:
        with get_cursor() as cursor:
            if DB_TYPE == "postgresql":
                query = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """
            else:  # SQLite
                query = """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """
            
            cursor.execute(query, (table_name,))
            result = cursor.fetchone()
            
            if DB_TYPE == "postgresql":
                return bool(result[0]) if result else False
            else:  # SQLite
                return result is not None
                
    except Exception as e:
        print(f"[DATABASE] テーブル存在チェックエラー: {e}")
        return False

def init_db():
    """データベースを初期化（エイリアス）"""
    return initialize_database()

def close_connection():
    """データベース接続を閉じる"""
    if hasattr(_local, 'connection') and _local.connection is not None:
        _local.connection.close()
        _local.connection = None
        print("[DATABASE] 接続を閉じました")

def test_connection():
    """データベース接続をテスト"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        
        success = result is not None
        print(f"[DATABASE] 接続テスト: {'成功' if success else '失敗'} ({DB_TYPE})")
        return success
        
    except Exception as e:
        print(f"[DATABASE] 接続テストエラー: {e}")
        return False

# モジュール読み込み時に初期化
if __name__ != "__main__":
    try:
        initialize_database()
    except Exception as e:
        print(f"[DATABASE] 自動初期化エラー: {e}")