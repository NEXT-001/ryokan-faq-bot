"""
検索履歴CSVからデータベースへの移行スクリプト
scripts/history_migration.py

history.csvファイルをsearch_historyテーブルに移行
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# プロジェクトルートディレクトリをPythonパスに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from core.database import save_search_history_to_db, get_search_history_from_db, cleanup_old_search_history
from config.settings import get_data_path

def migrate_csv_to_db(company_id="demo-company"):
    """
    CSVファイルからデータベースに検索履歴を移行
    
    Args:
        company_id (str): 会社ID
    """
    print(f"[MIGRATION] 検索履歴移行開始: {company_id}")
    
    # CSVファイルのパス
    csv_path = os.path.join(get_data_path(), "companies", company_id, "history.csv")
    
    if not os.path.exists(csv_path):
        print(f"[MIGRATION] CSVファイルが見つかりません: {csv_path}")
        return False
    
    try:
        # CSVファイルを読み込み
        df = pd.read_csv(csv_path)
        print(f"[MIGRATION] CSVファイル読み込み完了: {len(df)}件")
        
        # 1週間前の日時を計算
        one_week_ago = datetime.now() - timedelta(days=7)
        
        # timestamp列をdatetime型に変換
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 1週間以内のデータのみを対象とする
        df_recent = df[df['timestamp'] >= one_week_ago].copy()
        print(f"[MIGRATION] 1週間以内のデータ: {len(df_recent)}件")
        
        if len(df_recent) == 0:
            print("[MIGRATION] 移行対象のデータがありません")
            return True
        
        # データベースに移行
        migrated_count = 0
        error_count = 0
        
        for _, row in df_recent.iterrows():
            try:
                # テキストのサニタイズ（改行文字を削除）
                def sanitize_text(text):
                    if pd.isna(text):
                        return ""
                    return str(text).replace('\n', ' ').replace('\r', ' ')
                
                # データベースに保存
                success = save_search_history_to_db(
                    company_id=company_id,
                    question=sanitize_text(row['question']),
                    answer=sanitize_text(row['answer']),
                    input_tokens=int(row.get('input_tokens', 0)),
                    output_tokens=int(row.get('output_tokens', 0)),
                    user_info=sanitize_text(row.get('user_info', ''))
                )
                
                if success:
                    migrated_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                print(f"[MIGRATION] データ移行エラー: {e}")
                error_count += 1
        
        print(f"[MIGRATION] 移行完了: {migrated_count}件成功, {error_count}件エラー")
        
        # 移行後にCSVファイルをバックアップ
        backup_csv_path = f"{csv_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(csv_path, backup_csv_path)
        print(f"[MIGRATION] CSVファイルをバックアップ: {backup_csv_path}")
        
        return True
        
    except Exception as e:
        print(f"[MIGRATION] 移行エラー: {e}")
        return False

def verify_migration(company_id="demo-company"):
    """移行結果を検証"""
    try:
        # データベースから検索履歴を取得
        history_data = get_search_history_from_db(company_id, limit=1000)
        
        print(f"[VERIFICATION] データベース内の検索履歴: {len(history_data)}件")
        
        if len(history_data) > 0:
            # 最新と最古のデータを表示
            latest = history_data[0]
            oldest = history_data[-1]
            
            print(f"[VERIFICATION] 最新データ: {latest['created_at']} - {latest['question'][:50]}...")
            print(f"[VERIFICATION] 最古データ: {oldest['created_at']} - {oldest['question'][:50]}...")
            
            # 1週間以内のデータかチェック
            one_week_ago = datetime.now() - timedelta(days=7)
            oldest_date = datetime.fromisoformat(oldest['created_at'])
            
            if oldest_date >= one_week_ago:
                print("[VERIFICATION] ✅ 全データが1週間以内です")
            else:
                print(f"[VERIFICATION] ⚠️ 古いデータが含まれています: {oldest_date}")
        
        return True
        
    except Exception as e:
        print(f"[VERIFICATION] 検証エラー: {e}")
        return False

def migrate_all_companies():
    """全会社の検索履歴を移行"""
    companies_dir = os.path.join(get_data_path(), "companies")
    
    if not os.path.exists(companies_dir):
        print("[MIGRATION] companiesディレクトリが見つかりません")
        return False
    
    migrated_companies = []
    failed_companies = []
    
    # 各会社のディレクトリをチェック
    for company_id in os.listdir(companies_dir):
        company_path = os.path.join(companies_dir, company_id)
        
        if os.path.isdir(company_path):
            csv_path = os.path.join(company_path, "history.csv")
            
            if os.path.exists(csv_path):
                print(f"\n[MIGRATION] 会社 '{company_id}' の移行開始")
                
                if migrate_csv_to_db(company_id):
                    migrated_companies.append(company_id)
                    verify_migration(company_id)
                else:
                    failed_companies.append(company_id)
    
    print(f"\n[MIGRATION] 移行完了")
    print(f"[MIGRATION] 成功: {len(migrated_companies)}社 - {migrated_companies}")
    if failed_companies:
        print(f"[MIGRATION] 失敗: {len(failed_companies)}社 - {failed_companies}")
    
    return len(failed_companies) == 0

def cleanup_old_history():
    """古い検索履歴をクリーンアップ"""
    print("[CLEANUP] 古い検索履歴のクリーンアップ開始")
    
    try:
        # 全会社の7日以上古い履歴を削除
        success = cleanup_old_search_history(company_id=None, days=7)
        
        if success:
            print("[CLEANUP] クリーンアップ完了")
        else:
            print("[CLEANUP] クリーンアップ失敗")
        
        return success
        
    except Exception as e:
        print(f"[CLEANUP] クリーンアップエラー: {e}")
        return False

if __name__ == "__main__":
    print("検索履歴移行スクリプト")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "single":
            # 単一会社の移行
            company_id = sys.argv[2] if len(sys.argv) > 2 else "demo-company"
            print(f"単一会社移行: {company_id}")
            
            if migrate_csv_to_db(company_id):
                verify_migration(company_id)
            
        elif command == "all":
            # 全会社の移行
            print("全会社移行")
            migrate_all_companies()
            
        elif command == "cleanup":
            # 古い履歴のクリーンアップ
            cleanup_old_history()
            
        elif command == "verify":
            # 検証のみ
            company_id = sys.argv[2] if len(sys.argv) > 2 else "demo-company"
            verify_migration(company_id)
            
        else:
            print("使用方法:")
            print("  python history_migration.py single [company_id]  # 単一会社の移行")
            print("  python history_migration.py all                  # 全会社の移行")
            print("  python history_migration.py cleanup              # 古い履歴のクリーンアップ")
            print("  python history_migration.py verify [company_id]  # 移行結果の検証")
    else:
        # デフォルト: demo-companyの移行
        print("デフォルト移行: demo-company")
        
        response = input("続行しますか？ (yes/no): ").lower().strip()
        
        if response in ['yes', 'y']:
            if migrate_csv_to_db("demo-company"):
                verify_migration("demo-company")
        else:
            print("移行をキャンセルしました。")
