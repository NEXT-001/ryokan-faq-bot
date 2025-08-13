# core/company_manager.py - 会社管理機能（パス分離版）
import os
import re
import uuid
import json
import pandas as pd
import pickle
import numpy as np
import hashlib
import time
from datetime import datetime
from config.unified_config import UnifiedConfig

def get_existing_company_ids():
    """既存の会社IDリストを取得（複数ソースから）"""
    existing_ids = []
    
    try:
        # 1. SQLiteデータベースから取得
        import sqlite3
        DB_NAME = UnifiedConfig.DB_NAME
        
        if os.path.exists(DB_NAME):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            
            # usersテーブルから取得
            try:
                c.execute("SELECT DISTINCT company_id FROM users WHERE company_id IS NOT NULL")
                user_ids = [row[0] for row in c.fetchall()]
                existing_ids.extend(user_ids)
                print(f"[EXISTING IDS] usersテーブルから取得: {user_ids}")
            except:
                print(f"[EXISTING IDS] usersテーブル読み込みエラー")
            
            # company_idsテーブルから取得
            try:
                c.execute("SELECT DISTINCT company_id FROM company_ids")
                company_ids = [row[0] for row in c.fetchall()]
                existing_ids.extend(company_ids)
                print(f"[EXISTING IDS] company_idsテーブルから取得: {company_ids}")
            except:
                print(f"[EXISTING IDS] company_idsテーブル読み込みエラー")
            
            conn.close()
    except Exception as e:
        print(f"[EXISTING IDS] SQLite取得エラー: {e}")
    
    try:
        # 2. JSONファイルから取得（既存システム対応）
        from services.company_service import load_companies
        json_companies = load_companies()
        json_ids = list(json_companies.keys())
        existing_ids.extend(json_ids)
        print(f"[EXISTING IDS] JSONから取得: {json_ids}")
    except Exception as e:
        print(f"[EXISTING IDS] JSON取得エラー: {e}")
    
    # 3. companiesフォルダからの取得は廃止（データベース管理に移行済み）
    print(f"[EXISTING IDS] companiesフォルダ機能は廃止されました")
    
    # 重複を除去
    unique_ids = list(set([id for id in existing_ids if id]))  # 空文字列やNoneを除外
    print(f"[EXISTING IDS] 重複除去後: {unique_ids}")
    
    return unique_ids

def generate_unique_company_id(company_name):
    """
    会社名から一意の会社IDを自動生成する（強化版）
    
    Args:
        company_name (str): 会社名
        
    Returns:
        str: 一意の会社ID
    """
    print(f"[COMPANY ID] 会社ID生成開始: {company_name}")
    
    # 基本的な変換処理
    # 1. 小文字に変換
    base_name = company_name.lower().strip()
    
    # 2. 日本語を削除し、英数字とハイフン、アンダースコアのみを残す
    clean_name = re.sub(r'[^a-zA-Z0-9\-_]', '', base_name)
    
    # 3. 空文字列や短すぎる場合は会社名の一部を使用
    if len(clean_name) < 2:
        # 会社名をハッシュ化して短い文字列を生成
        hash_name = hashlib.md5(company_name.encode('utf-8')).hexdigest()[:6]
        clean_name = f"company_{hash_name}"
    
    # 長すぎる場合は短縮
    if len(clean_name) > 20:
        clean_name = clean_name[:20]
    
    print(f"[COMPANY ID] 基本変換後: {clean_name}")
    
    # 4. 既存の会社IDと重複しないかチェック
    existing_ids = get_existing_company_ids()
    
    # 5. 一意性を保証するために追加情報を付加
    company_id = clean_name
    
    # タイムスタンプベースの一意性確保
    timestamp = str(int(time.time()))[-6:]  # 現在時刻の下6桁
    
    # 基本IDが既存と重複する場合、または短すぎる場合
    if company_id in existing_ids or len(company_id) < 3:
        company_id = f"{clean_name}_{timestamp}"
        print(f"[COMPANY ID] タイムスタンプ追加: {company_id}")
    
    # まだ重複する場合は、ランダム文字列を追加
    counter = 1
    while company_id in existing_ids:
        # UUIDの一部を使用してより一意性を高める
        unique_suffix = str(uuid.uuid4()).replace('-', '')[:8]
        company_id = f"{clean_name}_{timestamp}_{unique_suffix}"
        counter += 1
        
        # 無限ループ防止
        if counter > 10:
            company_id = f"company_{str(uuid.uuid4()).replace('-', '')[:12]}"
            break
        
        print(f"[COMPANY ID] 重複回避({counter}): {company_id}")
        
        # 既存IDリストを再取得（他の処理で追加されている可能性）
        if counter % 3 == 0:
            existing_ids = get_existing_company_ids()
    
    # 最終的な長さとフォーマットチェック
    if len(company_id) > 50:  # 長すぎる場合は短縮
        unique_part = str(uuid.uuid4()).replace('-', '')[:8]
        company_id = f"{clean_name[:20]}_{unique_part}"
    
    # 最終チェック
    final_existing = get_existing_company_ids()
    if company_id in final_existing:
        # 最後の手段として完全にランダムなIDを生成
        company_id = f"company_{str(uuid.uuid4()).replace('-', '')[:16]}"
        print(f"[COMPANY ID] 最終ランダム生成: {company_id}")
    
    print(f"[COMPANY ID] 最終生成ID: {company_id}")
    return company_id

# 互換性のため、元の関数名も残す
def generate_company_id(company_name):
    """会社名から会社IDを生成（互換性維持）"""
    return generate_unique_company_id(company_name)

# 削除済み: create_company_folder_structure() 
# データベース管理に移行したため、フォルダ作成機能は廃止


def validate_company_id(company_id):
    """会社IDの妥当性をチェック"""
    if not company_id:
        return False, "会社IDが空です"
    
    if len(company_id) < 3:
        return False, "会社IDが短すぎます（3文字以上必要）"
    
    if len(company_id) > 50:
        return False, "会社IDが長すぎます（50文字以下必要）"
    
    # 使用可能文字チェック
    if not re.match(r'^[a-zA-Z0-9\-_]+$', company_id):
        return False, "会社IDに使用できない文字が含まれています（英数字、ハイフン、アンダースコアのみ）"
    
    return True, "妥当な会社IDです"