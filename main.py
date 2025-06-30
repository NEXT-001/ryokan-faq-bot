# main.py - 統合されたFAQボットアプリ（会社ID自動生成対応版）
import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
import uuid
import re
import pickle
import numpy as np
import json
from dotenv import load_dotenv

# パスを追加してモジュールをインポート可能にする
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# モジュールのインポート（エラーハンドリング付き）
try:
    from config.settings import load_api_key, is_test_mode, get_data_path
    from services.chat_service import get_response
    from services.history_service import log_interaction, show_history
    from services.login_service import login_user, logout_user, is_logged_in, is_super_admin, get_current_company_id, admin_management_page
    from services.company_service import load_companies, add_company, get_company_name, get_company_list
    from admin_faq_management import faq_management_page, faq_preview_page
    from line_settings import line_settings_page
    MODULES_AVAILABLE = True
except ImportError as e:
    st.error(f"モジュールのインポートエラー: {e}")
    st.info("必要なモジュールファイルが見つかりません。基本機能のみ利用できます。")
    MODULES_AVAILABLE = False

# .envファイルを読み込む
load_dotenv()

# URLパラメータの取得（ページ設定より前に定義）
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

# URLパラメータに基づいてページ設定を動的に調整
mode, _, _ = get_url_params()

# ページ設定
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

# 定数
os.makedirs("data", exist_ok=True)
DB_NAME = os.path.join("data", "faq_database.db")
VERIFICATION_URL = "http://localhost:8501"
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

# サイドバーナビゲーションを非表示にする関数
def hide_sidebar_navigation():
    """
    Streamlitのデフォルトページナビゲーションを非表示にする
    （管理モードのサイドバーは保持）
    """
    st.markdown("""
        <style>
            /* サイドバーのページナビゲーションのみを非表示（サイドバー自体は保持） */
            .css-1d391kg {display: none !important;}
            .css-17lntkn {display: none !important;}
            .css-pkbazv {display: none !important;}
            
            /* 新しいStreamlitバージョン対応 */
            [data-testid="stSidebarNav"] {display: none !important;}
            [data-testid="stSidebarNavItems"] {display: none !important;}
            [data-testid="stSidebarNavLink"] {display: none !important;}
            
            /* ナビゲーションリンク全般を非表示 */
            div[data-testid="stSidebar"] nav {display: none !important;}
            div[data-testid="stSidebar"] ul {display: none !important;}
            div[data-testid="stSidebar"] li {display: none !important;}
            div[data-testid="stSidebar"] a[href*="main"] {display: none !important;}
            div[data-testid="stSidebar"] a[href*="verify"] {display: none !important;}
            
            /* より具体的なナビゲーション要素のみを非表示 */
            .stSidebar .css-1544g2n {display: none !important;}
            .stSidebar .css-10trblm {display: none !important;}
            
            /* Streamlit最新版のナビゲーション要素 */
            [class*="navigation"] {display: none !important;}
            [class*="nav-link"] {display: none !important;}
            [class*="sidebar-nav"] {display: none !important;}
            
            /* 最新版対応 - ナビゲーション部分のみ */
            .st-emotion-cache-1cypcdb {display: none !important;}
            .st-emotion-cache-pkbazv {display: none !important;}
            .st-emotion-cache-1rs6os {display: none !important;}
            .st-emotion-cache-16txtl3 {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

# サイドバー全体を非表示にする関数
def hide_entire_sidebar():
    """サイドバー全体を非表示にする"""
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            .css-1d391kg {
                display: none;
            }
            /* メインコンテンツを全幅に */
            .css-18e3th9 {
                padding-left: 1rem;
            }
            .css-1d391kg {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)

def generate_company_id(company_name):
    """
    会社名から会社IDを自動生成する（SQLiteのみ使用）
    
    Args:
        company_name (str): 会社名
        
    Returns:
        str: 自動生成されたユニークな会社ID
    """
    print(f"[COMPANY ID] 会社名 '{company_name}' からIDを生成開始")
    
    # Step 1: SQLiteから既存の全会社IDを取得
    existing_companies = get_existing_company_ids_from_sqlite()
    print(f"[COMPANY ID] 既存の会社ID数: {len(existing_companies)}")
    if existing_companies:
        print(f"[COMPANY ID] 既存ID一覧: {existing_companies}")
    
    # Step 2: ベースIDを生成
    base_id = create_base_company_id(company_name)
    print(f"[COMPANY ID] ベースID: '{base_id}'")
    
    # Step 3: 重複チェックしてユニークIDを生成
    unique_id = create_unique_company_id(base_id, existing_companies)
    print(f"[COMPANY ID] 最終ID: '{unique_id}'")
    
    return unique_id

def get_existing_company_ids_from_sqlite():
    """
    SQLiteデータベースから既存の全ての会社IDを取得
    
    Returns:
        list: 既存の会社IDのリスト
    """
    existing_ids = []
    
    try:
        print(f"[SQLITE] データベース接続: {DB_NAME}")
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # テーブルの存在確認
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not c.fetchone():
            print("[SQLITE] usersテーブルが存在しません")
            conn.close()
            return existing_ids
        
        # カラム構造の確認
        c.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in c.fetchall()]
        print(f"[SQLITE] テーブル構造: {columns}")
        
        # company_idカラムが存在する場合
        if 'company_id' in columns:
            c.execute("SELECT DISTINCT company_id FROM users WHERE company_id IS NOT NULL AND company_id != ''")
            rows = c.fetchall()
            existing_ids = [row[0] for row in rows]
            print(f"[SQLITE] company_idカラムから {len(existing_ids)} 件取得")
        
        # company_idがなく、古いcompanyカラムが存在する場合
        elif 'company' in columns:
            c.execute("SELECT DISTINCT company FROM users WHERE company IS NOT NULL AND company != ''")
            rows = c.fetchall()
            existing_ids = [row[0] for row in rows]
            print(f"[SQLITE] companyカラムから {len(existing_ids)} 件取得")
        
        else:
            print("[SQLITE] 会社ID関連のカラムが見つかりません")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"[SQLITE ERROR] {e}")
    except Exception as e:
        print(f"[SQLITE ERROR] 予期しないエラー: {e}")
    
    return existing_ids

def create_base_company_id(company_name):
    """
    会社名からベースとなる会社IDを生成
    
    Args:
        company_name (str): 会社名
        
    Returns:
        str: ベース会社ID
    """
    if not company_name or not company_name.strip():
        # 会社名が空の場合
        base_id = f"company_{str(uuid.uuid4())[:8]}"
        print(f"[BASE ID] 会社名が空 -> ランダムID: {base_id}")
        return base_id
    
    # 会社名を英数字のみに変換（日本語文字を削除）
    clean_name = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
    
    if clean_name and len(clean_name) >= 3:
        # 英数字が3文字以上ある場合はそれを使用（最大15文字）
        base_id = clean_name[:15]
        print(f"[BASE ID] 会社名ベース: '{company_name}' -> '{base_id}'")
    else:
        # 英数字が少ない/ない場合はUUIDを使用
        base_id = f"company_{str(uuid.uuid4())[:8]}"
        print(f"[BASE ID] 英数字不足 -> ランダムID: {base_id}")
    
    return base_id

def create_unique_company_id(base_id, existing_ids):
    """
    ベースIDから重複のないユニークな会社IDを生成
    
    Args:
        base_id (str): ベースとなる会社ID
        existing_ids (list): 既存の会社IDリスト
        
    Returns:
        str: ユニークな会社ID
    """
    # 既存IDをセットに変換（高速検索のため）
    existing_set = set(existing_ids)
    
    # ベースIDがそのまま使える場合
    if base_id not in existing_set:
        print(f"[UNIQUE ID] ベースIDを使用: '{base_id}'")
        return base_id
    
    # 重複する場合は番号を付加
    print(f"[UNIQUE ID] '{base_id}' は重複。番号を付加します")
    
    for counter in range(1, 1000):  # 最大999まで試行
        candidate_id = f"{base_id}_{counter}"
        
        if candidate_id not in existing_set:
            print(f"[UNIQUE ID] ユニークID決定: '{candidate_id}'")
            return candidate_id
    
    # 999回試行しても重複する場合（ほぼあり得ない）
    fallback_id = f"company_{str(uuid.uuid4())[:8]}"
    print(f"[UNIQUE ID] フォールバック使用: '{fallback_id}'")
    return fallback_id

# テスト用関数
def test_company_id_generation():
    """
    会社ID生成のテスト
    """
    print("=" * 50)
    print("会社ID生成テスト")
    print("=" * 50)
    
    test_cases = [
        "株式会社サンプル",
        "Sample Company Inc",
        "テスト企業",
        "ABC123",
        "山田商事",
        "",
        "!@#$%^&*()",
        "VeryLongCompanyNameForTesting",
        "123456789"
    ]
    
    results = []
    
    for company_name in test_cases:
        print(f"\n--- テスト: '{company_name}' ---")
        try:
            company_id = generate_company_id(company_name)
            results.append((company_name, company_id, "成功"))
            print(f"✅ 結果: '{company_id}'")
        except Exception as e:
            results.append((company_name, str(e), "失敗"))
            print(f"❌ エラー: {e}")
    
    # 結果サマリー
    print(f"\n{'='*50}")
    print("テスト結果サマリー")
    print(f"{'='*50}")
    for company_name, result, status in results:
        print(f"{status}: '{company_name}' -> '{result}'")
    
    return results

# デバッグ用関数
def debug_sqlite_companies():
    """
    SQLiteの会社データをデバッグ表示
    """
    print("\n" + "=" * 40)
    print("SQLite会社データ デバッグ")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # テーブル存在確認
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not c.fetchone():
            print("❌ usersテーブルが存在しません")
            conn.close()
            return
        
        # テーブル構造
        c.execute("PRAGMA table_info(users)")
        columns = c.fetchall()
        print("📋 テーブル構造:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # データ件数
        c.execute("SELECT COUNT(*) FROM users")
        total_count = c.fetchone()[0]
        print(f"\n📊 総レコード数: {total_count}")
        
        # 会社ID関連データ
        column_names = [col[1] for col in columns]
        
        if 'company_id' in column_names:
            c.execute("SELECT company_id, company_name, name, email FROM users WHERE company_id IS NOT NULL")
            rows = c.fetchall()
            print(f"\n🏢 company_idデータ ({len(rows)}件):")
            for row in rows:
                print(f"  - ID: {row[0]}, 会社名: {row[1]}, 担当: {row[2]}, Email: {row[3]}")
        
        elif 'company' in column_names:
            c.execute("SELECT company, name, email FROM users WHERE company IS NOT NULL")
            rows = c.fetchall()
            print(f"\n🏢 companyデータ ({len(rows)}件):")
            for row in rows:
                print(f"  - 会社: {row[0]}, 担当: {row[1]}, Email: {row[2]}")
        
        else:
            print("\n⚠️ 会社関連のカラムが見つかりません")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ デバッグエラー: {e}")
    
    print("=" * 40)

# 重複テスト用関数
def test_duplicate_handling():
    """
    重複処理のテスト（同じ会社名で複数回実行）
    """
    print("\n" + "=" * 40)
    print("重複処理テスト")
    print("=" * 40)
    
    test_company_name = "テスト会社"
    generated_ids = []
    
    print(f"'{test_company_name}' で5回連続生成テスト:")
    
    for i in range(5):
        company_id = generate_company_id(test_company_name)
        generated_ids.append(company_id)
        print(f"  {i+1}回目: '{company_id}'")
    
    # 重複チェック
    unique_ids = set(generated_ids)
    print(f"\n結果:")
    print(f"  生成されたID: {generated_ids}")
    print(f"  ユニークID数: {len(unique_ids)}")
    print(f"  重複なし: {'✅' if len(unique_ids) == len(generated_ids) else '❌'}")
    
    return generated_ids

def create_company_folder_structure(company_id, company_name, password, email):
    """
    会社用のフォルダ構造とファイルを作成する
    
    Args:
        company_id (str): 会社ID
        company_name (str): 会社名
        password (str): パスワード
        email (str): メールアドレス
        
    Returns:
        bool: 作成成功したかどうか
    """
    try:
        # 会社フォルダのパスを作成（data/companies/{company_id}）
        companies_base_dir = os.path.join("data", "companies")
        company_folder = os.path.join(companies_base_dir, company_id)
        
        # companiesディレクトリが存在しない場合は作成
        if not os.path.exists(companies_base_dir):
            os.makedirs(companies_base_dir)
            print(f"[BASE DIR CREATED] {companies_base_dir}")
        
        # 会社フォルダが存在しない場合は作成
        if not os.path.exists(company_folder):
            os.makedirs(company_folder)
            print(f"[COMPANY FOLDER CREATED] {company_folder}")
        
        # 1. FAQ用のCSVファイルを作成
        faq_csv_path = os.path.join(company_folder, "faq.csv")
        if not os.path.exists(faq_csv_path):
            # サンプルFAQデータを作成
            sample_faq = {
                "question": [
                    f"{company_name}について教えてください",
                    "お問い合わせ方法を教えてください",
                    "営業時間はいつですか？",
                    "サービスの詳細について知りたいです",
                    "料金体系について教えてください"
                ],
                "answer": [
                    f"ようこそ{company_name}のFAQシステムへ！こちらでは、よくある質問にお答えしています。",
                    "お問い合わせは、メールまたはお電話にて承っております。詳細は担当者までお尋ねください。",
                    "営業時間は平日9:00〜18:00となっております。土日祝日は休業です。",
                    "サービスの詳細については、担当者が詳しくご説明いたします。お気軽にお問い合わせください。",
                    "料金体系については、ご利用内容に応じて異なります。詳しくはお見積りをお出しいたします。"
                ]
            }
            
            pd.DataFrame(sample_faq).to_csv(faq_csv_path, index=False, encoding='utf-8')
            print(f"[FILE CREATED] {faq_csv_path}")
        
        # 2. エンベディング結果ファイルを作成（空のpklファイル）
        embeddings_path = os.path.join(company_folder, "faq_with_embeddings.pkl")
        if not os.path.exists(embeddings_path):
            # 空のエンベディングデータを作成
            empty_embeddings = {
                "questions": [],
                "answers": [],
                "embeddings": np.array([])
            }
            
            with open(embeddings_path, 'wb') as f:
                pickle.dump(empty_embeddings, f)
            print(f"[FILE CREATED] {embeddings_path}")
        
        # 3. FAQ検索履歴ファイルを作成
        history_csv_path = os.path.join(company_folder, "history.csv")
        if not os.path.exists(history_csv_path):
            # 履歴CSVのヘッダーを作成
            history_headers = {
                "timestamp": [],
                "question": [],
                "answer": [],
                "input_tokens": [],
                "output_tokens": [],
                "user_info": [],
                "company_id": []
            }
            
            pd.DataFrame(history_headers).to_csv(history_csv_path, index=False, encoding='utf-8')
            print(f"[FILE CREATED] {history_csv_path}")
        
        # 4. 会社設定ファイルを作成（JSON）
        settings_path = os.path.join(company_folder, "settings.json")
        if not os.path.exists(settings_path):
            settings = {
                "company_id": company_id,
                "company_name": company_name,
                "created_at": datetime.now().isoformat(),
                "faq_count": 5,  # 初期FAQの数
                "last_updated": datetime.now().isoformat(),
                "admins": {
                    "admin": {
                        "password": hash_password(password),
                        "email": email,
                        "created_at": datetime.now().isoformat()
                    }
                }
            }
            
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            print(f"[FILE CREATED] {settings_path}")
        
        print(f"[SUCCESS] 会社フォルダ構造を作成しました: data/companies/{company_id}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 会社フォルダ構造の作成に失敗しました: {e}")
        return False
    
# === データベース関連機能 ===
def init_db():
    """データベースを初期化（シンプル版）"""
    try:
        print(f"[DB INIT] データベース初期化開始: {DB_NAME}")
        
        conn = sqlite3.connect(DB_NAME)
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
    
def hash_password(password):
    """パスワードをハッシュ化"""
    return hashlib.sha256(password.encode()).hexdigest()

def send_verification_email(email, token):
    """認証メールを送信"""
    if not SMTP_USER or not SMTP_PASS:
        st.warning("メール設定が不完全です。管理者にお問い合わせください。")
        return False
        
    msg = MIMEText(
        f"以下のリンクをクリックして登録を完了してください:\n"
        f"{VERIFICATION_URL}?token={token}"
    )
    msg["Subject"] = "【FAQシステム】メールアドレス認証のお願い"
    msg["From"] = SMTP_USER
    msg["To"] = email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"メール送信エラー: {e}")
        return False

def register_user(company_name, name, email, password):
    """ユーザーを仮登録（修正版）"""
    token = str(uuid.uuid4())
    
    try:
        # 1. 会社IDを自動生成
        company_id = generate_company_id(company_name)
        print(f"[COMPANY ID GENERATED] {company_name} -> {company_id}")
        
        # 2. データベースに登録
        conn = sqlite3.connect(DB_NAME)
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
            conn = sqlite3.connect(DB_NAME)
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
            conn = sqlite3.connect(DB_NAME)
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
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT id, company_id, email FROM users WHERE verify_token = ? AND is_verified = 0", (token,))
        user = c.fetchone()

        if user:
            c.execute("UPDATE users SET is_verified = 1, verify_token = NULL WHERE id = ?", (user[0],))
            conn.commit()
            conn.close()
            return True, user[1], user[2]
        conn.close()
        return False, None
    except Exception as e:
        st.error(f"データベースエラーが発生しました: {e}")
        return False, None

def login_user_by_email(email, password):
    """
    メールアドレスとパスワードでのログイン処理（修正版）
    
    Args:
        email (str): メールアドレス
        password (str): パスワード
        
    Returns:
        tuple: (成功したかどうか, メッセージ, 会社ID)
    """
    try:
        conn = sqlite3.connect(DB_NAME)
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
            
            # セッション情報を設定
            st.session_state["is_logged_in"] = True
            st.session_state["is_super_admin"] = False
            st.session_state["company_id"] = company_id  # 実際の会社IDを使用
            st.session_state["company_name"] = company_name  # 会社名を別途保存
            st.session_state["username"] = user_name
            st.session_state["user_email"] = user_email
            
            # URLパラメータにログイン状態を追加
            st.query_params.logged_in = "true"
            
            conn.close()
            return True, f"{company_name}の管理者として", company_id
        else:
            print(f"[LOGIN FAILED] Email: {email} - ユーザーが見つからない、またはメール認証未完了")
            conn.close()
            return False, "メールアドレスまたはパスワードが間違っているか、メール認証が完了していません", None
            
    except Exception as e:
        print(f"[LOGIN ERROR] Email: {email} - エラー: {e}")
        return False, f"データベースエラー: {e}", None

# === ページ機能 ===
def registration_page():
    """登録ページ（mode=reg）- 会社ID自動生成版"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    st.title("FAQチャットボットシステム")
    st.subheader("14日間無料お試し登録")
    
    # データベース初期化
    init_db()
    
    st.info("📝 会社IDは会社名から自動で生成されます")
    
    with st.form("register_form"):
        company = st.text_input("会社名", placeholder="例: 株式会社サンプル")
        name = st.text_input("担当者名", placeholder="例: 田中太郎")
        email = st.text_input("メールアドレス", placeholder="例: tanaka@sample.com")
        password = st.text_input("パスワード", type="password", placeholder="8文字以上を推奨")
        
        # 会社ID生成プレビュー
        # if company:
        #     generated_id = generate_company_id(company)
        #     st.caption(f"💡 生成される会社ID: `{generated_id}`")
        
        submitted = st.form_submit_button("登録")

    if submitted:
        if company and name and email and password:
            # パスワードの長さチェック
            if len(password) < 6:
                st.warning("パスワードは6文字以上で入力してください。")
                return
            
            success = register_user(company, name, email, password)
            if success:
                # generated_id = generate_company_id(company)
                st.success("✅ 仮登録が完了しました。認証メールをご確認ください。")
                st.info("📧 お送りしたメールのリンクをクリックして、登録を完了してください。")
                
                # 生成された会社IDを表示
                st.markdown("---")
                st.markdown("### 📋 登録情報")
                st.markdown(f"**会社名:** {company}")
                # st.markdown(f"**会社ID:** `{generated_id}`")
                st.markdown(f"**担当者:** {name}")
                st.markdown(f"**メールアドレス:** {email}")
                
                st.markdown("---")
                st.markdown("**メールが届かない場合は、迷惑メールフォルダもご確認ください。**")
            else:
                st.error("このメールアドレスは既に登録されているか、システムエラーが発生しました。")
        else:
            st.warning("すべての項目を入力してください。")
    
    # 他のページへのリンク
    st.markdown("---")
    st.markdown("### 既にアカウントをお持ちの方")
    st.markdown("[🔐 管理者ログイン](?mode=admin)")
    st.markdown("[💬 FAQチャットボットを試す](?mode=user&company=demo-company)")

def verify_page():
    """メール認証ページ（token パラメータ）"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    st.title("📧 メール認証")
    
    # クエリパラメータからトークン取得
    token = st.query_params.get("token")
    
    if token:
        verified, company_id, email = verify_user_token(token)
        if verified:
            st.success("✅ 認証完了")
            st.info(f"メールアドレス（{email}）の認証が完了しました！")
            st.markdown("### 次のステップ")
            st.markdown("1. 下記のボタンをクリックしてログイン画面に移動してください")
            
            # ログイン画面へのリンクボタン
            if st.button("🔐 ログイン画面に移動", type="primary"):
                # URLパラメータをクリアしてログイン画面に移動
                st.query_params.clear()
                st.query_params.mode = "admin"
                st.query_params.company = company_id
                st.rerun()
                
        else:
            st.error("❌ 認証失敗")
            st.warning("このトークンは無効、または既に認証済みです。")
            
            # ホームに戻るボタン
            if st.button("🏠 ホームページに戻る"):
                st.query_params.clear()
                st.rerun()
    else:
        st.warning("⚠️ トークンが見つかりません")
        st.info("メールのリンクが正しいか確認してください。")
        
        # ホームに戻るボタン
        if st.button("🏠 ホームページに戻る"):
            st.query_params.clear()
            st.rerun()

def user_page(company_id):
    """ユーザーページ（mode=user）"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    # 会社名を取得
    if MODULES_AVAILABLE:
        try:
            company_name = get_company_name(company_id) or "デモ企業"
        except:
            company_name = "デモ企業"
    else:
        company_name = "デモ企業"
    
    # タイトル表示
    st.title(f"💬 {company_name} FAQチャットボット")
    
    # テストモードの場合はヒントを表示
    if MODULES_AVAILABLE:
        try:
            if is_test_mode():
                st.info("""
                **テストモードで実行中です**
                
                以下のキーワードを含む質問に回答できます:
                チェックイン, チェックアウト, 駐車場, wi-fi, アレルギー, 部屋, 温泉, 食事, 子供, 観光
                """)
        except:
            pass
    else:
        st.info("⚠️ システムの一部機能が利用できません。基本的なチャット機能のみ動作します。")
    
    # セッション状態の初期化
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    # 履歴クリアボタン
    if st.button("会話履歴をクリア"):
        st.session_state.conversation_history = []
        if "user_input" in st.session_state:
            del st.session_state["user_input"]
        if "user_info" in st.session_state:
            del st.session_state["user_info"]
        st.success("会話履歴をクリアしました！")
    
    # ユーザー情報入力欄
    user_info = st.text_input("お部屋番号：", key="user_info", placeholder="例: 101")
    
    # ユーザー入力
    user_input = st.text_input("ご質問をどうぞ：", key="user_input", placeholder="例: チェックインの時間は何時ですか？")
    st.caption("💡 メッセージ入力後に入力欄から離れると結果が表示されます")
    
    if user_input:
        with st.spinner("回答を生成中..."):
            try:
                if MODULES_AVAILABLE:
                    # 回答を取得
                    response, input_tokens, output_tokens = get_response(
                        user_input, 
                        company_id,
                        user_info
                    )
                    
                    # ログに保存
                    log_interaction(
                        question=user_input,
                        answer=response,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        company_id=company_id,
                        user_info=user_info
                    )
                else:
                    # モジュールが利用できない場合のダミー応答
                    response = "申し訳ございません。現在システムがメンテナンス中です。基本機能のみ利用可能です。"
                
                # 会話履歴に追加
                st.session_state.conversation_history.append({
                    "user_info": user_info,
                    "question": user_input, 
                    "answer": response
                })
                
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                # エラー時のダミー応答
                st.session_state.conversation_history.append({
                    "user_info": user_info,
                    "question": user_input, 
                    "answer": "申し訳ございません。現在システムに問題が発生しております。しばらくお待ちください。"
                })
    
    # 会話履歴の表示
    if st.session_state.conversation_history:
        st.subheader("会話履歴")
        with st.container():
            for i, exchange in enumerate(st.session_state.conversation_history[-5:]):  # 直近5件のみ表示
                st.markdown(f"**質問 {i+1}:** {exchange['question']}")
                st.markdown(f"**回答 {i+1}:** {exchange['answer']}")
                if exchange.get("user_info"):
                    st.markdown(f"**お客様情報:** {exchange['user_info']}")
                st.markdown("---")
    
    # フッター
    st.markdown("---")
    st.markdown("### 管理者の方")
    st.markdown(f"[🔐 管理者ログイン](?mode=admin&company={company_id})")

def admin_page(company_id):
    """管理者ページ（mode=admin）"""
    # サイドバーのページナビゲーションのみを非表示（サイドバー自体は保持）
    hide_sidebar_navigation()
    
    # サイドバーを確実に表示するための設定
    st.markdown("""
        <style>
            /* サイドバー自体は表示する */
            [data-testid="stSidebar"] {
                display: block !important;
            }
            section[data-testid="stSidebar"] {
                display: block !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    if not MODULES_AVAILABLE:
        st.error("管理機能を利用するために必要なモジュールが見つかりません。")
        st.info("必要なファイルが正しく配置されているか確認してください。")
        st.markdown(f"[💬 FAQチャットボットに戻る](?mode=user&company={company_id})")
        return
    
    try:
        # ログイン状態をチェック
        if not is_logged_in():
            login_page(company_id)
            return
        
        # 管理者ダッシュボードを表示
        admin_dashboard(company_id)
    except Exception as e:
        st.error(f"管理者ページの読み込み中にエラーが発生しました: {e}")
        st.info("必要なモジュールが見つからない可能性があります。")
        
        # 基本的なログイン画面を表示
        st.title("💬 管理者ログイン")
        st.info("システムの一部機能が利用できません。")
        st.markdown(f"[💬 FAQ AIチャットボットに戻る](?mode=user&company={company_id})")

def login_page(company_id):
    """ログインページ"""
    st.title("💬 FAQ AIチャットボット - ログイン")
    
    # 会社名を表示
    if MODULES_AVAILABLE:
        try:
            company_name = get_company_name(company_id)
            if company_name:
                st.header(f"企業: {company_name}")
        except:
            pass
    
    # ログインフォーム（メールアドレス認証用に修正）
    with st.form("admin_login_form"):
        st.subheader("管理者ログイン")
        
        # メールアドレス欄を追加
        admin_email = st.text_input("メールアドレス", placeholder="example@company.com")
        admin_password = st.text_input("パスワード", type="password")
        
        # 既存の企業管理者ログイン用のオプション（折りたたみ式で提供）
        with st.expander("従来の企業ID・ユーザー名でのログイン"):
            admin_company_id = st.text_input("企業ID", value=company_id or '')
            admin_username = st.text_input("ユーザー名")
            st.caption("※ 従来の管理者アカウントでログインする場合にご利用ください")
        
        admin_submit = st.form_submit_button("ログイン")
        
        if admin_submit:
            # メールアドレスでのログインを優先
            if admin_email and admin_password:
                try:
                    # SQLiteからメールアドレス認証
                    success, message, user_company_id = login_user_by_email(admin_email, admin_password)
                    if success:
                        st.success(f"{message} ログインしました。")
                        
                        # URLパラメータを更新してページを再読み込み
                        st.query_params.mode = "admin"
                        st.query_params.company = user_company_id
                        st.query_params.logged_in = "true"
                        
                        st.success("管理者ページに移動しています...")
                        st.rerun()
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"ログイン処理でエラーが発生しました: {e}")
            
            # 従来の企業ID・ユーザー名でのログイン
            elif admin_company_id and admin_username and admin_password:
                try:
                    # 従来のログイン処理
                    success, message = login_user(admin_company_id, admin_username, admin_password)
                    if success:
                        st.success(f"{message} ログインしました。")
                        
                        # URLパラメータを更新してページを再読み込み
                        st.query_params.mode = "admin"
                        st.query_params.company = admin_company_id
                        st.query_params.logged_in = "true"
                        
                        st.success("管理者ページに移動しています...")
                        st.rerun()
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"ログイン処理でエラーが発生しました: {e}")
            else:
                st.error("メールアドレスとパスワード、または企業ID・ユーザー名・パスワードを入力してください")
    
    # 他のページへのリンク
    st.markdown("---")
    st.markdown("### その他")
    st.markdown(f"[💬 FAQチャットボットを利用する](?mode=user&company={company_id or 'demo-company'})")
    st.markdown("[📝 新規登録](?mode=reg)")

def admin_dashboard(company_id):
    """管理者ダッシュボード"""
    try:
        # スーパー管理者かどうかを確認
        is_super = is_super_admin()
        
        # 会社名を取得
        if is_super:
            company_name = "スーパー管理者"
        else:
            company_name = get_company_name(company_id) or "不明な会社"
        
        # タイトル表示
        st.title(f"💬 {company_name} - 管理画面")
        
        # テストモード表示
        if is_test_mode():
            st.info("📝 テストモードで実行中です")
        
        # サイドバーのナビゲーション
        with st.sidebar:
            st.header(f"ようこそ、{st.session_state.get('username', '')}さん")
            
            # メニュー
            if is_super:
                # スーパー管理者メニュー
                admin_page_option = st.radio(
                    "管理メニュー",
                    ["企業管理", "FAQデモ"]
                )
            else:
                # 企業管理者メニュー
                admin_page_option = st.radio(
                    "管理メニュー",
                    ["FAQ管理", "FAQ履歴", "LINE通知設定", "管理者設定", "FAQプレビュー"]
                )
            
            st.markdown("---")
            
            # ログアウト機能
            logout_btn = st.button("ログアウト")
            if logout_btn:
                logout_user()
                
                # ログアウト後はログイン画面に戻る
                st.query_params.mode = "admin"
                st.query_params.company = company_id
                # logged_inパラメータを削除
                if "logged_in" in st.query_params:
                    del st.query_params["logged_in"]
                
                st.success("ログアウトしました。")
                st.rerun()
            
            # ユーザーモードへのリンク
            user_url = f"?mode=user&company={company_id}"
            st.markdown(f"[お客様向けページを表示]({user_url})")
        
        # 選択したページを表示
        if is_super:
            # スーパー管理者ページ
            if admin_page_option == "企業管理":
                super_admin_company_management()
            elif admin_page_option == "FAQデモ":
                # 企業選択
                companies = get_company_list()
                company_options = {company["name"]: company["id"] for company in companies}
                
                selected_company_name = st.selectbox("企業を選択", list(company_options.keys()))
                selected_company_id = company_options[selected_company_name]
                
                # プレビュー表示
                faq_preview_page(selected_company_id)
        else:
            # 企業管理者ページ
            if admin_page_option == "FAQ管理":
                faq_management_page()
            elif admin_page_option == "FAQ履歴":
                show_history(company_id)
            elif admin_page_option == "LINE通知設定":
                line_settings_page(company_id)
            elif admin_page_option == "管理者設定":
                admin_management_page()
            elif admin_page_option == "FAQプレビュー":
                faq_preview_page(company_id)
                
    except Exception as e:
        st.error(f"管理機能の読み込み中にエラーが発生しました: {e}")
        st.markdown(f"[💬 FAQチャットボットに戻る](?mode=user&company={company_id})")

def super_admin_company_management():
    """スーパー管理者の企業管理ページ"""
    st.header("企業管理")
    
    try:
        # 企業一覧を表示
        companies = get_company_list()
        
        if companies:
            st.subheader("登録企業一覧")
            
            # 企業データをシンプルに表示
            company_data = []
            for company in companies:
                company_data.append({
                    "ID": company["id"],
                    "名前": company["name"],
                    "管理者数": company["admin_count"],
                    "作成日時": company["created_at"]
                })
            
            # シンプルなデータフレーム表示
            company_df = pd.DataFrame(company_data)
            st.dataframe(company_df)
            
            # 企業切り替え
            st.subheader("企業切り替え")
            
            for company in companies:
                # ログイン状態を維持
                admin_url = f"?mode=admin&company={company['id']}&logged_in=true"
                user_url = f"?mode=user&company={company['id']}"
                st.markdown(f"**{company['name']}**: [管理者として表示]({admin_url}) | [ユーザーとして表示]({user_url})")
        else:
            st.info("登録企業がありません。")
        
        # 新規企業追加フォーム
        st.subheader("新規企業登録")
        with st.form("add_company_form"):
            company_id = st.text_input("企業ID (英数字のみ)")
            company_name = st.text_input("企業名")
            admin_username = st.text_input("管理者ユーザー名")
            admin_password = st.text_input("管理者パスワード", type="password")
            admin_email = st.text_input("管理者メールアドレス")
            
            submit = st.form_submit_button("企業を登録")
            
            if submit:
                if not company_id or not company_name or not admin_username or not admin_password:
                    st.error("すべての必須項目を入力してください。")
                else:
                    # IDが英数字のみかチェック
                    if not company_id.isalnum():
                        st.error("企業IDは英数字のみで入力してください。")
                    else:
                        success, message = add_company(company_id, company_name, admin_username, admin_password, admin_email)
                        if success:
                            st.success(message)
                            # 直接URLを提供してリンクとして表示
                            admin_url = f"?mode=admin&company={company_id}&logged_in=true"
                            st.markdown(f"新しい企業の管理画面を表示するには[ここをクリック]({admin_url})")
                        else:
                            st.error(message)
    except Exception as e:
        st.error(f"企業管理機能でエラーが発生しました: {e}")

def show_company_info_debug():
    """登録された会社情報をデバッグ表示する（テストモード時のみ）"""
    if MODULES_AVAILABLE:
        try:
            if is_test_mode():
                with st.expander("🔧 登録済み会社情報（デバッグ用）"):
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        c = conn.cursor()
                        c.execute("""
                            SELECT company_id, company_name, name, email, is_verified, created_at 
                            FROM users 
                            ORDER BY created_at DESC
                        """)
                        users = c.fetchall()
                        conn.close()
                        
                        if users:
                            st.write("SQLiteデータベースの登録情報:")
                            for user in users:
                                company_id, company_name, name, email, verified, created = user
                                status = "✅ 認証済み" if verified else "⏳ 認証待ち"
                                st.write(f"- 会社ID: `{company_id}` | 会社名: {company_name}")
                                st.write(f"  担当者: {name} | メール: {email} | {status}")
                                
                                # フォルダ存在チェック
                                folder_path = os.path.join("data", company_id)
                                if os.path.exists(folder_path):
                                    st.write(f"  📁 フォルダ: 作成済み ({folder_path})")
                                    
                                    # ファイル存在チェック
                                    files_to_check = ["faq.csv", "faq_with_embeddings.pkl", "history.csv", "settings.json"]
                                    for file_name in files_to_check:
                                        file_path = os.path.join(folder_path, file_name)
                                        if os.path.exists(file_path):
                                            file_size = os.path.getsize(file_path)
                                            st.write(f"    ✅ {file_name} ({file_size} bytes)")
                                        else:
                                            st.write(f"    ❌ {file_name}")
                                else:
                                    st.write(f"  📁 フォルダ: 未作成")
                                st.write("---")
                        else:
                            st.write("登録されたユーザーはありません")
                    except Exception as e:
                        st.write(f"エラー: {e}")
        except:
            pass

def show_debug_info():
    """デバッグ情報を表示する（テストモード時のみ）"""
    if MODULES_AVAILABLE:
        try:
            if is_test_mode():
                with st.expander("🔧 デバッグ情報"):
                    # セッション状態
                    st.write("セッション状態:")
                    for key, value in st.session_state.items():
                        if key not in ["conversation_history"]:
                            st.write(f"- {key}: {value}")
                    
                    # ログイン状態のチェック
                    st.write(f"is_logged_in()の結果: {is_logged_in()}")
                    
                    # 環境変数の状態
                    st.write("環境変数:")
                    st.write(f"- TEST_MODE: {os.getenv('TEST_MODE', 'false')}")
                    st.write(f"- MODULES_AVAILABLE: {MODULES_AVAILABLE}")
                    
                    # モード切替リンク
                    test_company = "demo-company"
                    st.write("モード切替リンク:")
                    st.markdown(f"- [ユーザーモード](?mode=user&company={test_company})")
                    st.markdown(f"- [管理者モード](?mode=admin&company={test_company})")
                    st.markdown(f"- [登録モード](?mode=reg)")
                    
                    # セッションリセットボタン
                    if st.button("セッションをリセット"):
                        # セッションだけクリアして、URLはそのまま
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        st.success("セッションをリセットしました。")
        except:
            pass

# メイン実行部分
if __name__ == "__main__":
    # 最初にページナビゲーションを非表示にする（全モード共通）
    hide_sidebar_navigation()
    
    # URLパラメータに基づいて画面を切り替え
    mode, company_id, url_logged_in = get_url_params()
    
    # セッション状態の初期化
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    # 会社IDをセッションに保存（regモード以外）
    if company_id:
        st.session_state.selected_company = company_id
    
    # URLのログイン状態からセッション状態を復元
    if url_logged_in and "is_logged_in" not in st.session_state:
        st.session_state["is_logged_in"] = True
    
    # APIキーのロード（エラーハンドリング付き）
    if MODULES_AVAILABLE:
        try:
            load_api_key()
        except ValueError as e:
            st.error(f"エラー: {e}")
            st.info("APIキーが設定されていないため、テストモードで実行します")
            # テストモードを有効化
            os.environ["TEST_MODE"] = "true"
        except:
            # APIキーが設定されていない場合はテストモードを有効化
            os.environ["TEST_MODE"] = "true"
    
    # デバッグ情報表示（テストモード時のみ）
    show_debug_info()
    
    # 登録済み会社情報表示（テストモード時のみ）
    show_company_info_debug()
    
    # モードに応じた表示
    if mode == "verify":
        # メール認証ページ（tokenパラメータがある場合）
        verify_page()
    elif mode == "reg":
        # 登録ページ
        registration_page()
    elif mode == "admin":
        # 管理者ページ
        admin_page(company_id)
    else:
        # ユーザーページ（デフォルト）
        user_page(company_id)