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


# 削除済み: create_company_folder_structure() 
# データベース管理に移行したため、フォルダ作成機能は廃止
def create_company_folder_structure_deprecated(company_id, company_name, password, email, location_info=None):
    """
    廃止: データベース管理に移行したため、フォルダ作成機能は使用されません
    互換性のためのスタブ関数
    """
    # データベースに会社情報を保存するのみ
    try:
        from core.database import save_company_to_db
        db_success = save_company_to_db(
            company_id=company_id,
            company_name=company_name,
            created_at=datetime.now().isoformat(),
            faq_count=0,  # 初期状態
            location_info=location_info
        )
        
        if db_success:
            print(f"[DATABASE] 会社情報をデータベースに保存しました: {company_id}")
            return True
        else:
            print(f"[DATABASE ERROR] 会社情報のデータベース保存に失敗しました: {company_id}")
            return False
        
    except Exception as e:
        print(f"[ERROR] 会社作成エラー: {e}")
        return False
