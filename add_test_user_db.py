"""
SQLiteにテストユーザーを追加
add_test_user_db.py
"""
import sqlite3
import hashlib
import os
import sys
from datetime import datetime

# プロジェクトルートをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def hash_password(password):
    """パスワードをハッシュ化する"""
    return hashlib.sha256(password.encode()).hexdigest()

def setup_database():
    """データベースとテーブルを設定"""
    
    from utils.constants import DB_NAME, get_data_path
    
    db_path = os.path.join(get_data_path(), DB_NAME)
    print(f"📊 データベースパス: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # usersテーブルの作成（存在しない場合）
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT NOT NULL,
                company_name TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_verified INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        print("✅ usersテーブルを確認・作成しました")
        
        # 既存のユーザーを確認
        c.execute("SELECT email, company_id, name FROM users")
        existing_users = c.fetchall()
        
        print(f"\n📋 既存ユーザー ({len(existing_users)}件):")
        for email, company_id, name in existing_users:
            print(f"  - {email} ({name}) - {company_id}")
        
        # テストユーザーを追加
        test_users = [
            {
                'company_id': 'demo-company',
                'company_name': 'デモ企業',
                'name': 'Administrator',
                'email': 'admin@example.com',
                'password': 'admin123'
            },
            {
                'company_id': 'demo-company', 
                'company_name': 'デモ企業',
                'name': 'Test User',
                'email': 'kangju80@gmail.com',
                'password': 'admin123'  # 同じパスワードを使用
            }
        ]
        
        print(f"\n➕ テストユーザーを追加中...")
        
        for user in test_users:
            try:
                # 既存ユーザーの確認
                c.execute("SELECT id FROM users WHERE email = ?", (user['email'],))
                existing = c.fetchone()
                
                if existing:
                    # 既存ユーザーを更新
                    c.execute("""
                        UPDATE users 
                        SET company_id = ?, company_name = ?, name = ?, password = ?, is_verified = 1
                        WHERE email = ?
                    """, (
                        user['company_id'],
                        user['company_name'], 
                        user['name'],
                        hash_password(user['password']),
                        user['email']
                    ))
                    print(f"  🔄 更新: {user['email']}")
                else:
                    # 新規ユーザーを追加
                    c.execute("""
                        INSERT INTO users (company_id, company_name, name, email, password, is_verified)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (
                        user['company_id'],
                        user['company_name'],
                        user['name'], 
                        user['email'],
                        hash_password(user['password'])
                    ))
                    print(f"  ➕ 追加: {user['email']}")
                    
            except sqlite3.IntegrityError as e:
                print(f"  ⚠️ {user['email']}: {e}")
        
        conn.commit()
        
        # 追加後の確認
        c.execute("SELECT email, company_id, name, is_verified FROM users")
        all_users = c.fetchall()
        
        print(f"\n✅ 最終ユーザー一覧 ({len(all_users)}件):")
        for email, company_id, name, is_verified in all_users:
            status = "✅認証済み" if is_verified else "❌未認証"
            print(f"  - {email} ({name}) - {company_id} [{status}]")
        
        conn.close()
        
        print(f"\n🎉 データベースセットアップ完了！")
        print(f"以下の情報でログインできます:")
        print(f"  メールアドレス: kangju80@gmail.com")
        print(f"  パスワード: admin123")
        
        return True
        
    except Exception as e:
        print(f"❌ データベースエラー: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_authentication():
    """認証テストを実行"""
    
    print(f"\n🔐 認証テスト実行中...")
    
    try:
        # authenticate_user_by_email関数をテスト
        from utils.constants import DB_NAME, get_data_path
        
        db_path = os.path.join(get_data_path(), DB_NAME)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        test_email = "kangju80@gmail.com"
        test_password = "admin123"
        
        print(f"テスト対象: {test_email}")
        
        # 手動で認証クエリを実行
        c.execute("""
            SELECT company_id, company_name, name, email, is_verified
            FROM users 
            WHERE email = ? AND password = ?
        """, (test_email, hash_password(test_password)))
        
        user = c.fetchone()
        
        if user:
            company_id, company_name, name, email, is_verified = user
            print(f"✅ 認証成功:")
            print(f"  - 会社ID: {company_id}")
            print(f"  - 会社名: {company_name}")
            print(f"  - ユーザー名: {name}")
            print(f"  - メール: {email}")
            print(f"  - 認証状態: {'認証済み' if is_verified else '未認証'}")
        else:
            print(f"❌ 認証失敗")
            
            # デバッグ: 全ユーザーを表示
            c.execute("SELECT email, name FROM users")
            all_users = c.fetchall()
            print(f"データベース内のユーザー:")
            for email, name in all_users:
                print(f"  - {email} ({name})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 認証テストエラー: {e}")

if __name__ == "__main__":
    print("=== SQLite データベース セットアップ ===")
    
    if setup_database():
        test_authentication()
        
        print(f"\n📝 次のステップ:")
        print(f"1. Streamlitアプリケーションを再起動")
        print(f"2. 管理者ページにアクセス")
        print(f"3. メールアドレス: kangju80@gmail.com でログイン")
        print(f"4. パスワード: admin123")