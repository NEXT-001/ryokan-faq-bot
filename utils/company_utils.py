"""
会社関連のユーティリティ関数
utils/company_utils.py

会社ID生成とフォルダ構造作成に特化したユーティリティ
"""
import os
import re
import uuid
import sqlite3
import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from config.unified_config import UnifiedConfig


def generate_company_id(company_name):
    """
    会社名から会社IDを自動生成する
    
    Args:
        company_name (str): 会社名
        
    Returns:
        str: 自動生成されたユニークな会社ID
    """
    print(f"[COMPANY ID] 会社名 '{company_name}' からIDを生成開始")
    
    # 既存の会社IDを取得
    existing_companies = get_existing_company_ids_from_sqlite()
    print(f"[COMPANY ID] 既存の会社ID数: {len(existing_companies)}")
    
    # ベースIDを生成
    base_id = create_base_company_id(company_name)
    print(f"[COMPANY ID] ベースID: '{base_id}'")
    
    # 重複チェックしてユニークIDを生成
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
    db_name = os.path.join("data", "faq_database.db")
    
    try:
        print(f"[SQLITE] データベース接続: {db_name}")
        conn = sqlite3.connect(db_name)
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
        UnifiedConfig.log_error("データベースアクセスエラーが発生しました")
        UnifiedConfig.log_debug(f"SQLiteエラー詳細: {e}")
    except Exception as e:
        UnifiedConfig.log_error("予期しないエラーが発生しました")
        UnifiedConfig.log_debug(f"エラー詳細: {e}")
    
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


def create_company_folder_structure(company_id, company_name, password, email, location_info=None):
    """
    会社用のフォルダ構造とファイルを作成する
    
    Args:
        company_id (str): 会社ID
        company_name (str): 会社名
        password (str): パスワード
        email (str): メールアドレス
        location_info (dict): 住所情報（postal_code, prefecture, city, address）
        
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
        # settings_path = os.path.join(company_folder, "settings.json")
        # if not os.path.exists(settings_path):
        #     settings = {
        #         "company_id": company_id,
        #         "company_name": company_name,
        #         "created_at": datetime.now().isoformat(),
        #         "faq_count": 5,  # 初期FAQの数
        #         "last_updated": datetime.now().isoformat(),
        #         "admins": {
        #             "admin": {
        #                 "password": hash_password(password),
        #                 "email": email,
        #                 "created_at": datetime.now().isoformat()
        #             }
        #         }
        #     }
            
        #     with open(settings_path, 'w', encoding='utf-8') as f:
        #         json.dump(settings, f, ensure_ascii=False, indent=2)
        #     print(f"[FILE CREATED] {settings_path}")
        
        # 5. データベースに会社情報と住所情報を保存
        from core.database import save_company_to_db
        db_success = save_company_to_db(
            company_id=company_id,
            company_name=company_name,
            created_at=datetime.now().isoformat(),
            faq_count=5,  # 初期FAQの数
            location_info=location_info
        )
        
        if db_success:
            print(f"[DATABASE] 会社情報をデータベースに保存しました: {company_id}")
        else:
            print(f"[DATABASE WARNING] 会社情報のデータベース保存に失敗しました: {company_id}")
        
        print(f"[SUCCESS] 会社フォルダ構造を作成しました: data/companies/{company_id}")
        return True
        
    except Exception as e:
        UnifiedConfig.log_error("会社フォルダ構造の作成に失敗しました")
        UnifiedConfig.log_debug(f"エラー詳細: {e}")
        return False
