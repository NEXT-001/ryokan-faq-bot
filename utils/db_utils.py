"""
データベース関連のユーティリティ関数
utils/db_utils.py
"""
import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
import uuid
from datetime import datetime
from utils.auth_utils import hash_password


def get_db_path():
    """データベースファイルのパスを取得"""
    return os.path.join("data", "faq_database.db")


def init_db():
    """データベースを初期化（シンプル版）"""
    db_name = get_db_path()
    
    try:
        print(f"[DB INIT] データベース初期化開始: {db_name}")
        
        # dataディレクトリを確保
        os.makedirs("data", exist_ok=True)
        
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        
        # usersテーブルの存在チェック
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = c.fetchone()
        
        if not table_exists:
            print("[DB INIT] usersテーブルが存在しません。新規作成します")
            
            # 新しいusersテーブルを作成
            c.execute('''CREATE TABLE users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            company_id TEXT,
                            company_name TEXT,
                            name TEXT,
                            email TEXT UNIQUE,
                            password TEXT,
                            created_at TEXT,
                            is_verified INTEGER DEFAULT 0,
                            verify_token TEXT
                        )''')
            
            # インデックスを作成
            c.execute("CREATE INDEX idx_users_email ON users(email)")
            c.execute("CREATE INDEX idx_users_company_id ON users(company_id)")
            c.execute("CREATE INDEX idx_users_verify_token ON users(verify_token)")
            
            conn.commit()
            print("[DB INIT] usersテーブルを作成しました")
        else:
            print("[DB INIT] usersテーブルは既に存在します")
        
        conn.close()
        print("[DB INIT] データベース初期化完了")
        
    except sqlite3.Error as e:
        print(f"[DB INIT ERROR] SQLiteエラー: {e}")
        if 'conn' in locals():
            conn.close()
        raise
        
    except Exception as e:
        print(f"[DB INIT ERROR] 予期しないエラー: {e}")
        if 'conn' in locals():
            conn.close()
        raise


def send_verification_email(email, token):
    """認証メールを送信"""
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    verification_url = "http://localhost:8501"
    
    if not smtp_user or not smtp_pass:
        print("メール設定が不完全です。管理者にお問い合わせください。")
        return False
        
    msg = MIMEText(
        f"以下のリンクをクリックして登録を完了してください:\n"
        f"{verification_url}?token={token}"
    )
    msg["Subject"] = "【FAQシステム】メールアドレス認証のお願い"
    msg["From"] = smtp_user
    msg["To"] = email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"メール送信エラー: {e}")
        return False


def register_user(company_name, name, email, password):
    """ユーザーを仮登録"""
    from utils.company_utils import generate_company_id, create_company_folder_structure
    
    token = str(uuid.uuid4())
    db_name = get_db_path()
    
    try:
        # 1. 会社IDを自動生成
        company_id = generate_company_id(company_name)
        print(f"[COMPANY ID GENERATED] {company_name} -> {company_id}")
        
        # 2. データベースに登録
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        
        # テーブル構造を確認
        c.execute("PRAGMA table_info(users)")
        columns_info = c.fetchall()
        existing_columns = [column[1] for column in columns_info]
        print(f"[REGISTER] 現在のテーブル構造: {existing_columns}")
        
        # 必要なカラムが存在するかチェック
        required_columns = ['company_id', 'company_name', 'verify_token']
        missing_columns = [col for col in required_columns if col not in existing_columns]
        
        if missing_columns:
            print(f"[REGISTER ERROR] 不足しているカラム: {missing_columns}")
            conn.close()
            # データベースを再初期化
            init_db()
            # 再接続
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
        
        # 登録処理を実行
        c.execute("""
            INSERT INTO users (company_id, company_name, name, email, password, created_at, is_verified, verify_token) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (company_id, company_name, name, email, hash_password(password), datetime.now().isoformat(), 0, token))
        
        conn.commit()
        conn.close()
        
        # 3. 会社フォルダ構造を作成
        folder_success = create_company_folder_structure(company_id, company_name, password, email)
        if not folder_success:
            print(f"[WARNING] フォルダ構造の作成に失敗しましたが、登録は継続します")
        
        # 4. メール送信
        if send_verification_email(email, token):
            print(f"[REGISTRATION SUCCESS] Company: {company_name} ({company_id}), User: {name}, Email: {email}")
            return True
        else:
            # メール送信に失敗した場合は登録を削除
            conn = sqlite3.connect(db_name)
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE email = ?", (email,))
            conn.commit()
            conn.close()
            return False
            
    except sqlite3.IntegrityError as e:
        print(f"[REGISTRATION ERROR] Email already exists: {email}")
        return False
    except Exception as e:
        print(f"[REGISTRATION ERROR] {e}")
        return False


def verify_user_token(token):
    """メール認証トークンを検証する"""
    db_name = get_db_path()
    
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        c.execute("SELECT id, company_id, email FROM users WHERE verify_token = ? AND is_verified = 0", (token,))
        user = c.fetchone()

        if user:
            c.execute("UPDATE users SET is_verified = 1, verify_token = NULL WHERE id = ?", (user[0],))
            conn.commit()
            conn.close()
            return True, user[1], user[2]
        conn.close()
        return False, None, None
    except Exception as e:
        print(f"データベースエラーが発生しました: {e}")
        return False, None, None


def login_user_by_email(email, password):
    """
    メールアドレスとパスワードでのログイン処理
    
    Args:
        email (str): メールアドレス
        password (str): パスワード
        
    Returns:
        tuple: (成功したかどうか, メッセージ, 会社ID)
    """
    db_name = get_db_path()
    
    try:
        conn = sqlite3.connect(db_name)
        c = conn.cursor()
        
        # ログイン試行をログ出力
        print(f"[LOGIN ATTEMPT] Email: {email}")
        
        # メールアドレスとパスワードで検索（認証済みのユーザーのみ）
        c.execute("""
            SELECT company_id, company_name, name, email 
            FROM users 
            WHERE email = ? AND password = ? AND is_verified = 1
        """, (email, hash_password(password)))
        
        user = c.fetchone()
        
        if user:
            company_id, company_name, user_name, user_email = user
            
            # 取得した情報をコンソールにログ出力
            print(f"[LOGIN SUCCESS] SQLiteから取得したデータ:")
            print(f"  - 会社ID: {company_id}")
            print(f"  - 会社名: {company_name}")
            print(f"  - ユーザー名: {user_name}")
            print(f"  - メールアドレス: {user_email}")
            print(f"  - ログイン日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            conn.close()
            return True, f"{company_name}の管理者として", company_id, company_name, user_name, user_email
        else:
            print(f"[LOGIN FAILED] Email: {email} - ユーザーが見つからない、またはメール認証未完了")
            conn.close()
            return False, "メールアドレスまたはパスワードが間違っているか、メール認証が完了していません", None, None, None, None
            
    except Exception as e:
        print(f"[LOGIN ERROR] Email: {email} - エラー: {e}")
        return False, f"データベースエラー: {e}", None, None, None, None