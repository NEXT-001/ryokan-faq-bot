"""
データベーススキーマ移行スクリプト
scripts/database_migration.py

company_adminsテーブルを削除し、usersとcompaniesテーブルのみを使用するように移行
"""
import sqlite3
import os
import sys
import shutil
from datetime import datetime

# プロジェクトルートディレクトリをPythonパスに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from core.database import get_db_path, get_db_connection, fetch_dict, execute_query

def backup_database():
    """データベースをバックアップ"""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print("[MIGRATION] データベースファイルが存在しません")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        shutil.copy2(db_path, backup_path)
        print(f"[MIGRATION] バックアップ作成完了: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"[MIGRATION] バックアップ作成エラー: {e}")
        return False

def migrate_company_admins_to_users():
    """company_adminsテーブルのデータをusersテーブルに移行"""
    try:
        # company_adminsテーブルのデータを取得
        company_admins_query = "SELECT * FROM company_admins"
        company_admins = fetch_dict(company_admins_query)
        
        if not company_admins:
            print("[MIGRATION] company_adminsテーブルにデータがありません")
            return True
        
        print(f"[MIGRATION] {len(company_admins)}件の管理者データを移行します")
        
        migrated_count = 0
        skipped_count = 0
        
        for admin in company_admins:
            company_id = admin['company_id']
            username = admin['username']
            password = admin['password']
            email = admin['email']
            created_at = admin['created_at']
            
            # 既にusersテーブルに同じメールアドレスが存在するかチェック
            from core.database import DB_TYPE
            if DB_TYPE == "postgresql":
                existing_user_query = "SELECT id FROM users WHERE email = %s"
            else:
                existing_user_query = "SELECT id FROM users WHERE email = ?"
            existing_user = fetch_dict(existing_user_query, (email,))
            
            if existing_user:
                print(f"[MIGRATION] スキップ: {email} は既にusersテーブルに存在")
                skipped_count += 1
                continue
            
            # companiesテーブルから会社名を取得
            if DB_TYPE == "postgresql":
                company_query = "SELECT name FROM companies WHERE id = %s"
            else:
                company_query = "SELECT name FROM companies WHERE id = ?"
            company_result = fetch_dict(company_query, (company_id,))
            company_name = company_result[0]['name'] if company_result else f"企業_{company_id}"
            
            # usersテーブルに挿入
            if DB_TYPE == "postgresql":
                insert_query = """
                    INSERT INTO users (company_id, company_name, name, email, password, created_at, is_verified)
                    VALUES (%s, %s, %s, %s, %s, %s, 1)
                """
            else:
                insert_query = """
                    INSERT INTO users (company_id, company_name, name, email, password, created_at, is_verified)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """
            
            try:
                execute_query(insert_query, (company_id, company_name, username, email, password, created_at))
                print(f"[MIGRATION] 移行完了: {username} ({email}) -> {company_name}")
                migrated_count += 1
            except Exception as e:
                print(f"[MIGRATION] 移行エラー: {username} ({email}) - {e}")
        
        print(f"[MIGRATION] 移行完了: {migrated_count}件成功, {skipped_count}件スキップ")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] データ移行エラー: {e}")
        return False

def remove_company_name_from_users():
    """usersテーブルからcompany_nameカラムを削除"""
    try:
        # 新しいusersテーブルを作成（company_nameカラムなし）
        create_new_users_query = """
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_verified INTEGER DEFAULT 0,
                verify_token TEXT,
                status INTEGER DEFAULT 0,
                trial_start_date TEXT,
                trial_end_date TEXT,
                is_trial_active INTEGER DEFAULT 1,
                FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
            )
        """
        execute_query(create_new_users_query)
        
        # 既存データを新しいテーブルにコピー（company_nameカラムを除く）
        copy_data_query = """
            INSERT INTO users_new (
                id, company_id, name, email, password, created_at, 
                is_verified, verify_token, status, trial_start_date, 
                trial_end_date, is_trial_active
            )
            SELECT 
                id, company_id, name, email, password, created_at,
                is_verified, verify_token, status, trial_start_date,
                trial_end_date, is_trial_active
            FROM users
        """
        execute_query(copy_data_query)
        
        # 古いテーブルを削除し、新しいテーブルをリネーム
        execute_query("DROP TABLE users")
        execute_query("ALTER TABLE users_new RENAME TO users")
        
        # インデックスを再作成
        execute_query("CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id)")
        execute_query("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        
        print("[MIGRATION] usersテーブルからcompany_nameカラムを削除しました")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] company_nameカラム削除エラー: {e}")
        return False

def drop_company_admins_table():
    """company_adminsテーブルを削除"""
    try:
        # テーブルが存在するかチェック
        check_table_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='company_admins'"
        table_exists = fetch_dict(check_table_query)
        
        if not table_exists:
            print("[MIGRATION] company_adminsテーブルは既に存在しません")
            return True
        
        # テーブルを削除
        execute_query("DROP TABLE company_admins")
        
        # インデックスも削除（存在する場合）
        try:
            execute_query("DROP INDEX IF EXISTS idx_company_admins_company_id")
            execute_query("DROP INDEX IF EXISTS idx_company_admins_email")
        except:
            pass  # インデックスが存在しない場合は無視
        
        print("[MIGRATION] company_adminsテーブルを削除しました")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] company_adminsテーブル削除エラー: {e}")
        return False

def verify_migration():
    """移行結果を検証"""
    try:
        # テーブル一覧を取得
        tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
        tables = fetch_dict(tables_query)
        table_names = [table['name'] for table in tables]
        
        print(f"[MIGRATION] 現在のテーブル: {table_names}")
        
        # company_adminsテーブルが削除されているかチェック
        if 'company_admins' in table_names:
            print("[MIGRATION] 警告: company_adminsテーブルがまだ存在します")
            return False
        
        # usersテーブルの構造をチェック
        users_info_query = "PRAGMA table_info(users)"
        users_columns = fetch_dict(users_info_query)
        column_names = [col['name'] for col in users_columns]
        
        print(f"[MIGRATION] usersテーブルのカラム: {column_names}")
        
        # company_nameカラムが削除されているかチェック
        if 'company_name' in column_names:
            print("[MIGRATION] 警告: usersテーブルにcompany_nameカラムがまだ存在します")
            return False
        
        # 必要なカラムが存在するかチェック
        required_columns = ['id', 'company_id', 'name', 'email', 'password']
        missing_columns = [col for col in required_columns if col not in column_names]
        
        if missing_columns:
            print(f"[MIGRATION] エラー: 必要なカラムが不足: {missing_columns}")
            return False
        
        # データ数をチェック
        users_count_query = "SELECT COUNT(*) as count FROM users"
        users_count = fetch_dict(users_count_query)[0]['count']
        
        companies_count_query = "SELECT COUNT(*) as count FROM companies"
        companies_count = fetch_dict(companies_count_query)[0]['count']
        
        print(f"[MIGRATION] データ数 - users: {users_count}, companies: {companies_count}")
        
        print("[MIGRATION] 移行検証完了: 正常")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] 移行検証エラー: {e}")
        return False

def run_migration():
    """移行を実行"""
    print("[MIGRATION] データベース移行を開始します")
    print("=" * 50)
    
    # ステップ1: バックアップ
    print("\n[STEP 1] データベースバックアップ")
    backup_path = backup_database()
    if not backup_path:
        print("[MIGRATION] バックアップに失敗しました。移行を中止します。")
        return False
    
    try:
        # ステップ2: company_adminsデータをusersに移行
        print("\n[STEP 2] company_adminsデータをusersテーブルに移行")
        if not migrate_company_admins_to_users():
            print("[MIGRATION] データ移行に失敗しました")
            return False
        
        # ステップ3: usersテーブルからcompany_nameカラムを削除
        print("\n[STEP 3] usersテーブルからcompany_nameカラムを削除")
        if not remove_company_name_from_users():
            print("[MIGRATION] company_nameカラム削除に失敗しました")
            return False
        
        # ステップ4: company_adminsテーブルを削除
        print("\n[STEP 4] company_adminsテーブルを削除")
        if not drop_company_admins_table():
            print("[MIGRATION] company_adminsテーブル削除に失敗しました")
            return False
        
        # ステップ5: 移行結果を検証
        print("\n[STEP 5] 移行結果を検証")
        if not verify_migration():
            print("[MIGRATION] 移行検証に失敗しました")
            return False
        
        print("\n" + "=" * 50)
        print("[MIGRATION] データベース移行が正常に完了しました")
        print(f"[MIGRATION] バックアップファイル: {backup_path}")
        return True
        
    except Exception as e:
        print(f"\n[MIGRATION] 移行中にエラーが発生しました: {e}")
        print(f"[MIGRATION] バックアップから復旧してください: {backup_path}")
        return False

def rollback_migration(backup_path):
    """移行をロールバック"""
    try:
        db_path = get_db_path()
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, db_path)
            print(f"[MIGRATION] ロールバック完了: {backup_path} -> {db_path}")
            return True
        else:
            print(f"[MIGRATION] バックアップファイルが見つかりません: {backup_path}")
            return False
    except Exception as e:
        print(f"[MIGRATION] ロールバックエラー: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        if len(sys.argv) > 2:
            backup_path = sys.argv[2]
            rollback_migration(backup_path)
        else:
            print("使用方法: python database_migration.py rollback <backup_path>")
    else:
        # 移行実行の確認
        print("データベース移行を実行しますか？")
        print("この操作により、company_adminsテーブルが削除され、")
        print("usersテーブルの構造が変更されます。")
        print("")
        
        response = input("続行しますか？ (yes/no): ").lower().strip()
        
        if response in ['yes', 'y']:
            success = run_migration()
            if not success:
                print("\n移行に失敗しました。バックアップファイルから復旧してください。")
                sys.exit(1)
        else:
            print("移行をキャンセルしました。")
