"""
データベース操作のコアモジュール
core/database.py
"""
import sqlite3
import os
import hashlib
import threading
from contextlib import contextmanager
from datetime import datetime
from utils.constants import get_data_path, DB_NAME

# スレッドローカルストレージ
_local = threading.local()

def get_db_path():
    """データベースファイルのパスを取得"""
    base_dir = get_data_path()
    return os.path.join(base_dir, DB_NAME)

def get_db_connection():
    """データベース接続を取得（スレッドセーフ）"""
    if not hasattr(_local, 'connection') or _local.connection is None:
        db_path = get_db_path()
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        _local.connection = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=30.0
        )
        _local.connection.row_factory = sqlite3.Row  # 辞書ライクなアクセス
        
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
                    last_updated TEXT NOT NULL
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
            
            # インデックスの作成
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_admins_company_id ON company_admins(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_company_admins_email ON company_admins(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_faq_company_id ON faq_data(company_id)")
            
        print("[DATABASE] データベース初期化完了")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 初期化エラー: {e}")
        return False

# =============================================================================
# company_service.py で必要な関数群を追加
# =============================================================================

def hash_password(password):
    """パスワードをハッシュ化する"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_company_tables():
    """会社関連テーブルを初期化（initialize_databaseのエイリアス）"""
    return initialize_database()

def save_company_to_db(company_id, company_name, created_at, faq_count=0):
    """会社情報をデータベースに保存"""
    try:
        if created_at is None:
            created_at = datetime.now().isoformat()
        
        query = """
            INSERT OR REPLACE INTO companies (id, name, created_at, faq_count, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """
        last_updated = datetime.now().isoformat()
        
        execute_query(query, (company_id, company_name, created_at, faq_count, last_updated))
        print(f"[DATABASE] 会社保存完了: {company_id}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 会社保存エラー: {e}")
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
                "last_updated": result["last_updated"]
            }
        return None
        
    except Exception as e:
        print(f"[DATABASE] 会社取得エラー: {e}")
        return None

def save_company_admin_to_db(company_id, username, password, email, created_at):
    """会社管理者をデータベースに保存"""
    try:
        if created_at is None:
            created_at = datetime.now().isoformat()
            
        query = """
            INSERT OR REPLACE INTO company_admins 
            (company_id, username, password, email, created_at)
            VALUES (?, ?, ?, ?, ?)
        """
        
        execute_query(query, (company_id, username, password, email, created_at))
        print(f"[DATABASE] 管理者保存完了: {company_id}/{username}")
        return True
        
    except Exception as e:
        print(f"[DATABASE] 管理者保存エラー: {e}")
        return False

def get_company_admins_from_db(company_id):
    """会社の管理者一覧をデータベースから取得"""
    try:
        query = "SELECT * FROM company_admins WHERE company_id = ?"
        results = fetch_dict(query, (company_id,))
        
        admins = {}
        for row in results:
            admins[row["username"]] = {
                "password": row["password"],
                "email": row["email"],
                "created_at": row["created_at"]
            }
        
        return admins
        
    except Exception as e:
        print(f"[DATABASE] 管理者取得エラー: {e}")
        return {}

def delete_company_admins_from_db(company_id):
    """会社の全管理者をデータベースから削除"""
    try:
        query = "DELETE FROM company_admins WHERE company_id = ?"
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
            return True, {
                "id": result["id"],
                "company_id": result["company_id"],
                "company_name": result["company_name"],
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

# モジュール読み込み時に初期化
if __name__ != "__main__":
    init_db_if_needed()