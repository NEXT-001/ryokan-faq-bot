"""
データ移行ユーティリティ
utils/migration_utils.py
"""
import os
import pandas as pd
from datetime import datetime
from utils.constants import get_data_path
from core.database import (
    save_company_to_db, save_company_admin_to_db, save_line_settings_to_db,
    save_faq_history_to_db, company_exists_in_db, get_all_companies_from_db
)

def migrate_company_data_to_sqlite():
    """
    既存のJSONファイルとCSVデータをSQLiteに移行する
    """
    print("[MIGRATION] データ移行開始")
    
    # companiesディレクトリをスキャン
    base_dir = get_data_path()
    companies_dir = os.path.join(base_dir, "companies")
    
    if not os.path.exists(companies_dir):
        print("[MIGRATION] companiesディレクトリが存在しません")
        return False
    
    migrated_companies = 0
    
    for company_dir in os.listdir(companies_dir):
        company_path = os.path.join(companies_dir, company_dir)
        if os.path.isdir(company_path):
            print(f"[MIGRATION] 会社ID: {company_dir} の移行開始")
            
            # settings.jsonから情報を抽出して移行
            if migrate_single_company_from_settings(company_dir, company_path):
                # CSV履歴ファイルを移行
                migrate_csv_history_to_sqlite(company_dir, company_path)
                migrated_companies += 1
            else:
                print(f"[MIGRATION] 会社ID: {company_dir} の移行に失敗")
    
    print(f"[MIGRATION] データ移行完了: {migrated_companies}社")
    return True

def migrate_single_company_from_settings(company_id, company_path):
    """
    単一企業のsettings.jsonデータをSQLiteに移行する
    """
    try:
        settings_file = os.path.join(company_path, "settings.json")
        
        # settings.jsonが存在しない場合はスキップ
        if not os.path.exists(settings_file):
            print(f"[MIGRATION] settings.jsonが存在しません: {company_id}")
            return True
        
        # JSONファイルを読み込み
        import json
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        # 会社基本情報を移行
        company_name = settings.get("company_name", f"企業_{company_id}")
        created_at = settings.get("created_at", datetime.now().isoformat())
        faq_count = settings.get("faq_count", 0)
        
        # 会社が既にSQLiteに存在するかチェック
        if not company_exists_in_db(company_id):
            save_company_to_db(company_id, company_name, created_at, faq_count)
            print(f"[MIGRATION] 会社情報を移行: {company_id}")
        
        # 管理者情報を移行
        admins = settings.get("admins", {})
        for username, admin_info in admins.items():
            save_company_admin_to_db(
                company_id,
                username,
                admin_info.get("password", ""),
                admin_info.get("email", ""),
                admin_info.get("created_at", created_at)
            )
            print(f"[MIGRATION] 管理者を移行: {company_id}/{username}")
        
        # LINE設定を移行
        line_settings = settings.get("line_settings")
        if line_settings:
            save_line_settings_to_db(
                company_id,
                line_settings.get("channel_access_token", ""),
                line_settings.get("channel_secret", ""),
                line_settings.get("user_id", ""),
                line_settings.get("low_similarity_threshold", 0.4)
            )
            print(f"[MIGRATION] LINE設定を移行: {company_id}")
        
        return True
        
    except Exception as e:
        print(f"[MIGRATION] 会社移行エラー {company_id}: {e}")
        return False

def migrate_csv_history_to_sqlite(company_id, company_path):
    """
    CSVファイルの履歴データをSQLiteに移行する
    """
    try:
        history_file = os.path.join(company_path, "history.csv")
        
        # history.csvが存在しない場合はスキップ
        if not os.path.exists(history_file):
            print(f"[MIGRATION] history.csvが存在しません: {company_id}")
            return True
        
        # CSVファイルを読み込み
        try:
            df = pd.read_csv(history_file, encoding='utf-8')
        except:
            try:
                df = pd.read_csv(history_file, encoding='shift_jis')
            except:
                print(f"[MIGRATION] history.csvの読み込みに失敗: {company_id}")
                return False
        
        # データをSQLiteに移行
        migrated_count = 0
        for _, row in df.iterrows():
            question = row.get("question", "")
            answer = row.get("answer", "")
            similarity_score = row.get("similarity_score")
            user_ip = row.get("user_ip", "")
            
            # 日付情報を処理
            created_at = row.get("timestamp")
            if created_at is None:
                created_at = row.get("created_at")
            if created_at is None:
                created_at = datetime.now().isoformat()
            
            # similarity_scoreを数値に変換
            if similarity_score is not None:
                try:
                    similarity_score = float(similarity_score)
                except:
                    similarity_score = None
            
            # SQLiteに保存
            if save_faq_history_to_db(company_id, question, answer, similarity_score, user_ip):
                migrated_count += 1
        
        print(f"[MIGRATION] FAQ履歴を移行: {company_id} ({migrated_count}件)")
        return True
        
    except Exception as e:
        print(f"[MIGRATION] CSV履歴移行エラー {company_id}: {e}")
        return False

def backup_original_files():
    """
    元のJSONファイルをバックアップする
    """
    print("[MIGRATION] 元ファイルのバックアップ開始")
    
    base_dir = get_data_path()
    companies_dir = os.path.join(base_dir, "companies")
    backup_dir = os.path.join(base_dir, "backup_before_migration")
    
    if not os.path.exists(companies_dir):
        return False
    
    # バックアップディレクトリを作成
    os.makedirs(backup_dir, exist_ok=True)
    
    import shutil
    
    backed_up_companies = 0
    for company_dir in os.listdir(companies_dir):
        company_path = os.path.join(companies_dir, company_dir)
        if os.path.isdir(company_path):
            backup_company_path = os.path.join(backup_dir, company_dir)
            
            try:
                shutil.copytree(company_path, backup_company_path, dirs_exist_ok=True)
                backed_up_companies += 1
                print(f"[MIGRATION] バックアップ完了: {company_dir}")
            except Exception as e:
                print(f"[MIGRATION] バックアップエラー {company_dir}: {e}")
    
    print(f"[MIGRATION] バックアップ完了: {backed_up_companies}社")
    return True

def verify_migration():
    """
    移行結果を検証する
    """
    print("[MIGRATION] 移行結果の検証開始")
    
    try:
        # SQLiteから全企業データを取得
        companies_data = get_all_companies_from_db()
        
        print(f"[MIGRATION] SQLiteに移行された企業数: {len(companies_data)}")
        
        for company_id, company_info in companies_data.items():
            print(f"[MIGRATION] 企業: {company_id}")
            print(f"  - 名前: {company_info.get('name', 'N/A')}")
            print(f"  - 管理者数: {len(company_info.get('admins', {}))}")
            print(f"  - FAQ数: {company_info.get('faq_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"[MIGRATION] 検証エラー: {e}")
        return False

def run_full_migration():
    """
    完全な移行プロセスを実行する
    """
    print("[MIGRATION] 完全移行プロセス開始")
    
    # 1. バックアップ
    if not backup_original_files():
        print("[MIGRATION] バックアップに失敗しました")
        return False
    
    # 2. データ移行
    if not migrate_company_data_to_sqlite():
        print("[MIGRATION] データ移行に失敗しました")
        return False
    
    # 3. 検証
    if not verify_migration():
        print("[MIGRATION] 移行検証に失敗しました")
        return False
    
    print("[MIGRATION] 完全移行プロセス完了")
    return True

if __name__ == "__main__":
    # スクリプトとして実行された場合は完全移行を実行
    run_full_migration()