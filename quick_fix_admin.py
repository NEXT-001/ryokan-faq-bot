"""
緊急修正スクリプト
quick_fix_admin.py

管理者データを直接作成します
"""
import os
import sys
import sqlite3
import hashlib
from datetime import datetime

# プロジェクトルートをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def hash_password(password):
    """パスワードをハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

def quick_fix():
    """緊急修正を実行"""
    
    # 設定値
    company_id = "company_913f36_472935"
    company_name = "テスト株式会社"
    admin_email = "kangju80@gmail.com"
    admin_password = "admin123"
    
    print("=== 緊急修正実行 ===")
    print(f"企業ID: {company_id}")
    print(f"メール: {admin_email}")
    print(f"パスワード: {admin_password}")
    
    try:
        # データベースファイルパス
        from utils.constants import DB_NAME
        db_path = os.path.join("data", DB_NAME)
        
        print(f"データベースパス: {db_path}")
        
        # データディレクトリを作成
        os.makedirs("data", exist_ok=True)
        
        # データベース接続
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # テーブル作成
        print("テーブル作成中...")
        
        c.execute('''CREATE TABLE IF NOT EXISTS companies (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        faq_count INTEGER DEFAULT 0,
                        last_updated TEXT NOT NULL
                    )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS company_admins (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        company_id TEXT NOT NULL,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        email TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE(company_id, username),
                        UNIQUE(company_id, email)
                    )''')
        
        current_time = datetime.now().isoformat()
        
        # 会社データを挿入
        print("会社データ挿入中...")
        
        c.execute("""
            INSERT OR REPLACE INTO companies 
            (id, name, created_at, faq_count, last_updated)
            VALUES (?, ?, ?, ?, ?)
        """, (company_id, company_name, current_time, 5, current_time))
        
        # 管理者データを挿入
        print("管理者データ挿入中...")
        
        # 既存の管理者を削除
        c.execute("DELETE FROM company_admins WHERE company_id = ?", (company_id,))
        
        # 新しい管理者を挿入
        hashed_password = hash_password(admin_password)
        
        c.execute("""
            INSERT INTO company_admins 
            (company_id, username, password, email, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (company_id, "admin", hashed_password, admin_email, current_time))
        
        # コミット
        conn.commit()
        
        # 確認
        print("\n📋 挿入結果確認:")
        
        # 会社データ確認
        c.execute("SELECT id, name FROM companies WHERE id = ?", (company_id,))
        company = c.fetchone()
        if company:
            print(f"✅ 会社: {company[1]}")
        else:
            print("❌ 会社データなし")
        
        # 管理者データ確認
        c.execute("SELECT username, email FROM company_admins WHERE company_id = ?", (company_id,))
        admins = c.fetchall()
        if admins:
            print(f"✅ 管理者:")
            for admin in admins:
                print(f"   - {admin[0]}: {admin[1]}")
        else:
            print("❌ 管理者データなし")
        
        conn.close()
        
        print("\n🎉 緊急修正完了!")
        print("Streamlitアプリを再起動してログインしてみてください。")
        
        return True
        
    except Exception as e:
        print(f"❌ 緊急修正エラー: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    quick_fix()