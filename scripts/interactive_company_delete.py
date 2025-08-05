#!/usr/bin/env python3
"""
インタラクティブ会社データ削除スクリプト
scripts/interactive_company_delete.py

会社一覧を表示して選択形式で削除できます。
"""
import sys
import os
import sqlite3
from datetime import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_cursor
from scripts.delete_company_data import delete_company_data, delete_company_files, count_related_data


def list_companies():
    """全会社の一覧を表示"""
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT id, name, created_at, faq_count, 
                       (SELECT COUNT(*) FROM users WHERE company_id = companies.id) as user_count,
                       (SELECT COUNT(*) FROM company_admins WHERE company_id = companies.id) as admin_count
                FROM companies 
                ORDER BY created_at DESC
            """)
            companies = cursor.fetchall()
            
            if not companies:
                print("❌ 会社データがありません")
                return []
            
            print(f"\n📋 登録済み会社一覧 ({len(companies)}件):")
            print("-" * 100)
            print(f"{'No':<4} {'Company ID':<20} {'Company Name':<20} {'Users':<8} {'Admins':<8} {'FAQs':<8} {'Created':<12}")
            print("-" * 100)
            
            for i, company in enumerate(companies, 1):
                print(f"{i:<4} {company['id']:<20} {company['name']:<20} "
                      f"{company['user_count']:<8} {company['admin_count']:<8} "
                      f"{company['faq_count']:<8} {company['created_at'][:10]:<12}")
            
            print("-" * 100)
            return companies
            
    except Exception as e:
        print(f"❌ 会社一覧取得エラー: {e}")
        return []


def select_company(companies):
    """会社を選択"""
    while True:
        try:
            print(f"\n削除する会社を選択してください (1-{len(companies)}):")
            print("0: キャンセル")
            
            choice = input("選択番号: ").strip()
            
            if choice == '0':
                return None
            
            index = int(choice) - 1
            if 0 <= index < len(companies):
                selected = companies[index]
                print(f"\n選択された会社:")
                print(f"  ID: {selected['id']}")
                print(f"  名前: {selected['name']}")
                print(f"  ユーザー数: {selected['user_count']}")
                print(f"  管理者数: {selected['admin_count']}")
                print(f"  FAQ数: {selected['faq_count']}")
                print(f"  作成日: {selected['created_at']}")
                
                confirm = input("\nこの会社を削除しますか？ (yes/no): ").strip().lower()
                if confirm in ['yes', 'y']:
                    return selected['id']
                else:
                    print("❌ キャンセルされました")
                    continue
            else:
                print("❌ 無効な選択番号です")
                
        except ValueError:
            print("❌ 数字を入力してください")
        except KeyboardInterrupt:
            print("\n❌ 操作がキャンセルされました")
            return None


def main():
    """メイン処理"""
    print(f"🏢 インタラクティブ会社データ削除スクリプト")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 会社一覧表示
        companies = list_companies()
        if not companies:
            sys.exit(1)
        
        # 2. 会社選択
        company_id = select_company(companies)
        if not company_id:
            print("❌ 削除がキャンセルされました")
            sys.exit(0)
        
        # 3. 関連データ数確認
        print(f"\n🔍 '{company_id}' の関連データを確認中...")
        counts = count_related_data(company_id)
        if not counts:
            sys.exit(1)
        
        # 4. 最終確認
        print(f"\n⚠️  最終確認: 会社ID '{company_id}' の全データを削除します")
        final_confirm = input("本当に削除しますか？ (DELETE と入力): ").strip()
        
        if final_confirm != "DELETE":
            print("❌ 削除がキャンセルされました")
            sys.exit(0)
        
        # 5. データベースから削除
        delete_company_data(company_id)
        
        # 6. ファイルシステムから削除
        delete_company_files(company_id)
        
        print(f"\n🎉 削除完了! 会社ID '{company_id}' の全データが削除されました")
        print("📧 関連するメールアドレスがテストで再利用可能になりました")
        
    except KeyboardInterrupt:
        print("\n❌ 操作がキャンセルされました")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 削除処理中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()