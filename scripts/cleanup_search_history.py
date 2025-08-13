#!/usr/bin/env python3
"""
検索履歴削除スクリプト
scripts/cleanup_search_history.py

指定した期間より古い検索履歴を削除し、データベースのサイズを管理する
"""
import sys
import os
import argparse
from datetime import datetime, timedelta

# プロジェクトルートディレクトリをPythonパスに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from core.database import fetch_dict, execute_query, DB_TYPE
from dotenv import load_dotenv

# 環境変数読み込み
load_dotenv()

class SearchHistoryCleanup:
    def __init__(self):
        self.db_type = DB_TYPE
        self.stats = {
            'total_before': 0,
            'total_after': 0,
            'deleted_count': 0,
            'companies_affected': []
        }
    
    def get_statistics(self, company_id=None):
        """
        現在の履歴統計を取得
        
        Args:
            company_id (str, optional): 特定企業の統計を取得
            
        Returns:
            dict: 統計情報
        """
        try:
            if company_id:
                # 特定企業の統計
                total_query = "SELECT COUNT(*) as total FROM search_history WHERE company_id = ?"
                if self.db_type == "postgresql":
                    total_query = "SELECT COUNT(*) as total FROM search_history WHERE company_id = %s"
                
                total_result = fetch_dict(total_query, (company_id,))
                total_count = total_result[0]['total'] if total_result else 0
                
                return {
                    'company_id': company_id,
                    'total_count': total_count,
                    'is_single_company': True
                }
            else:
                # 全体統計
                total_query = "SELECT COUNT(*) as total FROM search_history"
                total_result = fetch_dict(total_query)
                total_count = total_result[0]['total'] if total_result else 0
                
                # 企業別統計
                company_query = "SELECT company_id, COUNT(*) as count FROM search_history GROUP BY company_id ORDER BY count DESC"
                company_results = fetch_dict(company_query)
                
                return {
                    'total_count': total_count,
                    'companies': company_results,
                    'is_single_company': False
                }
                
        except Exception as e:
            print(f"[ERROR] 統計取得エラー: {e}")
            return {'total_count': 0, 'companies': [], 'is_single_company': False}
    
    def preview_deletion(self, days=30, company_id=None):
        """
        削除対象のデータをプレビュー
        
        Args:
            days (int): 削除対象の日数
            company_id (str, optional): 対象企業ID
            
        Returns:
            dict: プレビュー情報
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            if company_id:
                if self.db_type == "postgresql":
                    count_query = "SELECT COUNT(*) as count FROM search_history WHERE company_id = %s AND created_at < %s"
                    sample_query = "SELECT question, created_at FROM search_history WHERE company_id = %s AND created_at < %s ORDER BY created_at DESC LIMIT 5"
                    params = (company_id, cutoff_date)
                else:
                    count_query = "SELECT COUNT(*) as count FROM search_history WHERE company_id = ? AND created_at < ?"
                    sample_query = "SELECT question, created_at FROM search_history WHERE company_id = ? AND created_at < ? ORDER BY created_at DESC LIMIT 5"
                    params = (company_id, cutoff_date)
            else:
                if self.db_type == "postgresql":
                    count_query = "SELECT COUNT(*) as count FROM search_history WHERE created_at < %s"
                    sample_query = "SELECT company_id, question, created_at FROM search_history WHERE created_at < %s ORDER BY created_at DESC LIMIT 10"
                    params = (cutoff_date,)
                else:
                    count_query = "SELECT COUNT(*) as count FROM search_history WHERE created_at < ?"
                    sample_query = "SELECT company_id, question, created_at FROM search_history WHERE created_at < ? ORDER BY created_at DESC LIMIT 10"
                    params = (cutoff_date,)
            
            # 削除対象件数
            count_result = fetch_dict(count_query, params)
            deletion_count = count_result[0]['count'] if count_result else 0
            
            # サンプルデータ
            sample_result = fetch_dict(sample_query, params)
            
            return {
                'deletion_count': deletion_count,
                'cutoff_date': cutoff_date,
                'sample_data': sample_result,
                'days': days
            }
            
        except Exception as e:
            print(f"[ERROR] プレビューエラー: {e}")
            return {'deletion_count': 0, 'sample_data': []}
    
    def backup_before_deletion(self, backup_file, days=30, company_id=None):
        """
        削除前のバックアップを作成
        
        Args:
            backup_file (str): バックアップファイルパス
            days (int): バックアップ対象の日数
            company_id (str, optional): 対象企業ID
            
        Returns:
            bool: バックアップ成功フラグ
        """
        try:
            import csv
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            if company_id:
                if self.db_type == "postgresql":
                    backup_query = """
                        SELECT company_id, user_info, question, answer, input_tokens, output_tokens, created_at 
                        FROM search_history 
                        WHERE company_id = %s AND created_at < %s 
                        ORDER BY created_at DESC
                    """
                    params = (company_id, cutoff_date)
                else:
                    backup_query = """
                        SELECT company_id, user_info, question, answer, input_tokens, output_tokens, created_at 
                        FROM search_history 
                        WHERE company_id = ? AND created_at < ? 
                        ORDER BY created_at DESC
                    """
                    params = (company_id, cutoff_date)
            else:
                if self.db_type == "postgresql":
                    backup_query = """
                        SELECT company_id, user_info, question, answer, input_tokens, output_tokens, created_at 
                        FROM search_history 
                        WHERE created_at < %s 
                        ORDER BY created_at DESC
                    """
                    params = (cutoff_date,)
                else:
                    backup_query = """
                        SELECT company_id, user_info, question, answer, input_tokens, output_tokens, created_at 
                        FROM search_history 
                        WHERE created_at < ? 
                        ORDER BY created_at DESC
                    """
                    params = (cutoff_date,)
            
            backup_data = fetch_dict(backup_query, params)
            
            if not backup_data:
                print("[INFO] バックアップ対象データがありません")
                return True
            
            # CSVファイルに保存
            with open(backup_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['company_id', 'user_info', 'question', 'answer', 'input_tokens', 'output_tokens', 'created_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for row in backup_data:
                    writer.writerow(row)
            
            print(f"[SUCCESS] バックアップ完了: {len(backup_data)}件 → {backup_file}")
            return True
            
        except Exception as e:
            print(f"[ERROR] バックアップエラー: {e}")
            return False
    
    def delete_old_history(self, days=30, company_id=None, backup_file=None):
        """
        古い検索履歴を削除
        
        Args:
            days (int): 削除対象の日数 (この日数より古いデータを削除)
            company_id (str, optional): 対象企業ID
            backup_file (str, optional): 削除前バックアップファイル
            
        Returns:
            dict: 削除結果
        """
        try:
            # 削除前の統計取得
            before_stats = self.get_statistics(company_id)
            self.stats['total_before'] = before_stats.get('total_count', 0)
            
            # バックアップ作成
            if backup_file:
                print(f"[BACKUP] バックアップを作成しています: {backup_file}")
                if not self.backup_before_deletion(backup_file, days, company_id):
                    print("[ERROR] バックアップに失敗しました。削除を中止します。")
                    return {'success': False, 'error': 'backup_failed'}
            
            # 削除実行
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            print(f"[DELETE] {cutoff_date} より古いデータを削除中...")
            
            if company_id:
                if self.db_type == "postgresql":
                    delete_query = "DELETE FROM search_history WHERE company_id = %s AND created_at < %s"
                    params = (company_id, cutoff_date)
                else:
                    delete_query = "DELETE FROM search_history WHERE company_id = ? AND created_at < ?"
                    params = (company_id, cutoff_date)
            else:
                if self.db_type == "postgresql":
                    delete_query = "DELETE FROM search_history WHERE created_at < %s"
                    params = (cutoff_date,)
                else:
                    delete_query = "DELETE FROM search_history WHERE created_at < ?"
                    params = (cutoff_date,)
            
            # 削除実行
            deleted_count = execute_query(delete_query, params)
            
            # 削除後の統計取得
            after_stats = self.get_statistics(company_id)
            self.stats['total_after'] = after_stats.get('total_count', 0)
            self.stats['deleted_count'] = self.stats['total_before'] - self.stats['total_after']
            
            result = {
                'success': True,
                'deleted_count': self.stats['deleted_count'],
                'before_count': self.stats['total_before'],
                'after_count': self.stats['total_after'],
                'cutoff_date': cutoff_date,
                'days': days,
                'company_id': company_id,
                'backup_file': backup_file
            }
            
            return result
            
        except Exception as e:
            print(f"[ERROR] 削除エラー: {e}")
            return {'success': False, 'error': str(e)}

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description="検索履歴削除スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 30日より古い履歴をすべて削除（プレビューあり）
  python cleanup_search_history.py --days 30
  
  # 特定企業の90日より古い履歴を削除
  python cleanup_search_history.py --days 90 --company demo-company
  
  # バックアップ付きで削除
  python cleanup_search_history.py --days 30 --backup backup_20250813.csv
  
  # 現在の統計のみ表示
  python cleanup_search_history.py --stats-only
  
  # 削除対象のプレビューのみ
  python cleanup_search_history.py --days 30 --preview-only
        """
    )
    
    parser.add_argument("--days", "-d", type=int, default=30, 
                      help="削除対象の日数（この日数より古いデータを削除、デフォルト: 30日）")
    parser.add_argument("--company", "-c", type=str, 
                      help="対象企業ID（省略時は全企業）")
    parser.add_argument("--backup", "-b", type=str, 
                      help="削除前バックアップファイルパス")
    parser.add_argument("--force", "-f", action="store_true", 
                      help="確認なしで実行")
    parser.add_argument("--stats-only", action="store_true", 
                      help="現在の統計のみ表示")
    parser.add_argument("--preview-only", action="store_true", 
                      help="削除対象のプレビューのみ表示")
    
    args = parser.parse_args()
    
    cleanup = SearchHistoryCleanup()
    
    # 統計のみ表示
    if args.stats_only:
        print("=" * 50)
        print("📊 検索履歴統計情報")
        print("=" * 50)
        
        stats = cleanup.get_statistics(args.company)
        
        if args.company:
            print(f"企業ID: {args.company}")
            print(f"総履歴件数: {stats['total_count']:,}件")
        else:
            print(f"総履歴件数: {stats['total_count']:,}件")
            print("\n企業別内訳:")
            for company in stats['companies'][:10]:
                print(f"  {company['company_id']}: {company['count']:,}件")
        
        return
    
    # プレビューのみ表示
    if args.preview_only:
        print("=" * 50)
        print(f"🔍 削除対象プレビュー ({args.days}日より古いデータ)")
        print("=" * 50)
        
        preview = cleanup.preview_deletion(args.days, args.company)
        
        print(f"削除対象件数: {preview['deletion_count']:,}件")
        print(f"削除基準日時: {preview['cutoff_date']}")
        
        if preview['sample_data']:
            print("\n削除対象サンプル:")
            for i, sample in enumerate(preview['sample_data'][:5], 1):
                if args.company:
                    print(f"  {i}. [{sample['created_at']}] {sample['question'][:50]}...")
                else:
                    print(f"  {i}. [{sample['created_at']}] [{sample['company_id']}] {sample['question'][:50]}...")
        
        return
    
    # メイン処理
    print("=" * 50)
    print("🧹 検索履歴クリーンアップツール")
    print("=" * 50)
    
    # 現在の状況表示
    current_stats = cleanup.get_statistics(args.company)
    print(f"現在の履歴件数: {current_stats['total_count']:,}件")
    
    # 削除対象プレビュー
    preview = cleanup.preview_deletion(args.days, args.company)
    print(f"削除対象: {preview['deletion_count']:,}件 ({args.days}日より古いデータ)")
    
    if preview['deletion_count'] == 0:
        print("✅ 削除対象のデータがありません。")
        return
    
    # 確認
    if not args.force:
        target_desc = f"企業「{args.company}」の" if args.company else "全企業の"
        backup_desc = f" (バックアップ: {args.backup})" if args.backup else ""
        
        print(f"\n⚠️  {target_desc}{preview['deletion_count']:,}件の履歴を削除します{backup_desc}")
        confirm = input("実行しますか？ (y/N): ")
        if confirm.lower() != 'y':
            print("❌ キャンセルされました。")
            return
    
    # 削除実行
    print(f"\n🗑️  削除を実行しています...")
    result = cleanup.delete_old_history(args.days, args.company, args.backup)
    
    if result['success']:
        print(f"✅ 削除完了!")
        print(f"   削除件数: {result['deleted_count']:,}件")
        print(f"   削除前: {result['before_count']:,}件")
        print(f"   削除後: {result['after_count']:,}件")
        
        if result['backup_file']:
            print(f"   バックアップ: {result['backup_file']}")
    else:
        print(f"❌ 削除に失敗しました: {result.get('error', '不明なエラー')}")

if __name__ == "__main__":
    main()