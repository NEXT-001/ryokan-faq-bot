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
    
    try:
        # 3. companiesフォルダから取得
        if os.path.exists(UnifiedConfig.COMPANIES_DIR):
            folder_ids = [name for name in os.listdir(UnifiedConfig.COMPANIES_DIR) 
                         if os.path.isdir(os.path.join(UnifiedConfig.COMPANIES_DIR, name))]
            existing_ids.extend(folder_ids)
            print(f"[EXISTING IDS] companiesフォルダから取得: {folder_ids}")
    except Exception as e:
        print(f"[EXISTING IDS] companiesフォルダ取得エラー: {e}")
    
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

def create_company_folder_structure(company_id, company_name):
    """
    会社用のフォルダ構造とファイルを作成する
    
    Args:
        company_id (str): 会社ID
        company_name (str): 会社名
        
    Returns:
        bool: 作成成功したかどうか
    """
    try:
        print(f"[FOLDER] フォルダ構造作成開始: company_id={company_id}, company_name={company_name}")
        
        # 会社フォルダのパスを作成（data/companies/{company_id}/）
        company_folder = get_company_folder_path(company_id)
        
        print(f"[FOLDER] 作成対象パス: {company_folder}")
        
        # フォルダが存在しない場合は作成
        if not os.path.exists(company_folder):
            os.makedirs(company_folder, exist_ok=True)
            print(f"[FOLDER CREATED] {company_folder}")
        else:
            print(f"[FOLDER EXISTS] {company_folder}")
        
        # フォルダ作成確認
        if not os.path.exists(company_folder):
            print(f"[FOLDER ERROR] フォルダ作成に失敗: {company_folder}")
            return False
        
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
            
            try:
                pd.DataFrame(sample_faq).to_csv(faq_csv_path, index=False, encoding='utf-8')
                print(f"[FILE CREATED] {faq_csv_path}")
            except Exception as e:
                print(f"[FILE ERROR] FAQ CSV作成失敗: {e}")
        else:
            print(f"[FILE EXISTS] {faq_csv_path}")
        
        # 2. エンベディング結果ファイルを作成（空のpklファイル）
        embeddings_path = os.path.join(company_folder, "faq_with_embeddings.pkl")
        if not os.path.exists(embeddings_path):
            # 空のエンベディングデータを作成
            empty_embeddings = {
                "questions": [],
                "answers": [],
                "embeddings": np.array([])
            }
            
            try:
                with open(embeddings_path, 'wb') as f:
                    pickle.dump(empty_embeddings, f)
                print(f"[FILE CREATED] {embeddings_path}")
            except Exception as e:
                print(f"[FILE ERROR] エンベディングファイル作成失敗: {e}")
        else:
            print(f"[FILE EXISTS] {embeddings_path}")
        
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
            
            try:
                pd.DataFrame(history_headers).to_csv(history_csv_path, index=False, encoding='utf-8')
                print(f"[FILE CREATED] {history_csv_path}")
            except Exception as e:
                print(f"[FILE ERROR] 履歴CSV作成失敗: {e}")
        else:
            print(f"[FILE EXISTS] {history_csv_path}")
        
        # 4. 会社設定ファイルを作成（JSON）
        # settings_path = os.path.join(company_folder, "settings.json")
        # if not os.path.exists(settings_path):
        #     settings = {
        #         "company_id": company_id,
        #         "company_name": company_name,
        #         "created_at": datetime.now().isoformat(),
        #         "faq_count": 5,  # 初期FAQの数
        #         "last_updated": datetime.now().isoformat()
        #     }
            
        #     try:
        #         with open(settings_path, 'w', encoding='utf-8') as f:
        #             json.dump(settings, f, ensure_ascii=False, indent=2)
        #         print(f"[FILE CREATED] {settings_path}")
        #     except Exception as e:
        #         print(f"[FILE ERROR] 設定JSON作成失敗: {e}")
        # else:
        #     print(f"[FILE EXISTS] {settings_path}")
        
        # 最終確認
        required_files = ["faq.csv", "faq_with_embeddings.pkl", "history.csv"]
        all_created = True
        for file_name in required_files:
            file_path = os.path.join(company_folder, file_name)
            if not os.path.exists(file_path):
                print(f"[FILE MISSING] {file_path}")
                all_created = False
        
        if all_created:
            print(f"[SUCCESS] 会社フォルダ構造を作成しました: {company_folder}")
            return True
        else:
            print(f"[PARTIAL SUCCESS] 一部ファイルの作成に失敗: {company_folder}")
            return False
        
    except Exception as e:
        print(f"[ERROR] 会社フォルダ構造の作成に失敗しました: {e}")
        import traceback
        print(f"[FOLDER TRACEBACK] {traceback.format_exc()}")
        return False


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