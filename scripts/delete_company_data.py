#!/usr/bin/env python3
"""
会社データ削除スクリプト
scripts/delete_company_data.py

指定されたcompany_idに関連する全てのデータを削除します。
テスト用メールアドレスの再利用を可能にします。
"""
import sys
import os
import sqlite3
import shutil
from datetime import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_db_path, get_cursor
from config.unified_config import UnifiedConfig


def confirm_deletion(company_id):
    """削除確認"""
    print(f"\n⚠ WARNING: 会社ID '{company_id}' の全データを削除します")
    print("削除されるデータ:")
    print("  - faq_embeddings (エンベディング)")
    print("  - faq_data (FAQ)")
    print("  - users (ユーザー)")
    print("  - company_admins (管理者)")
    print("  - line_settings (LINE設定)")
    print("  - search_history (検索履歴)")
    print("  - faq_history (FAQ履歴)")
    print("  - companies (会社情報)")
    print(f"  - data/companies/{company_id}/ (ファイルシステム)")
    
    response = input("\n削除を実行しますか？ (yes/no): ").strip().lower()
    return response in ['yes', 'y']


def get_company_info(company_id):
    """会社情報を取得"""
    try:
        from core.database import DB_TYPE
        with get_cursor() as cursor:
            if DB_TYPE == "postgresql":
                cursor.execute("SELECT * FROM companies WHERE id = %s", (company_id,))
            else:
                cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
            company = cursor.fetchone()
            
            if company:
                print(f"\n📋 会社情報:")
                print(f"  ID: {company['id']}")
                print(f"  名前: {company['name']}")
                print(f"  作成日: {company['created_at']}")
                print(f"  FAQ数: {company['faq_count']}")
                return True
            else:
                print(f"❌ 会社ID '{company_id}' が見つかりません")
                return False
    except Exception as e:
        print(f"❌ 会社情報取得エラー: {e}")
        return False


def count_related_data(company_id):
    """関連データ数をカウント"""
    try:
        with get_cursor() as cursor:
            counts = {}
            
            # users
            from core.database import DB_TYPE
            param_format = "%s" if DB_TYPE == "postgresql" else "?"
            cursor.execute(f"SELECT COUNT(*) as count FROM users WHERE company_id = {param_format}", (company_id,))
            counts['users'] = cursor.fetchone()['count']
            
            # company_admins
            cursor.execute("SELECT COUNT(*) as count FROM company_admins WHERE company_id = ?", (company_id,))
            counts['company_admins'] = cursor.fetchone()['count']
            
            # faq_data
            cursor.execute("SELECT COUNT(*) as count FROM faq_data WHERE company_id = ?", (company_id,))
            counts['faq_data'] = cursor.fetchone()['count']
            
            # faq_embeddings (via faq_data)
            cursor.execute("""
                SELECT COUNT(*) as count FROM faq_embeddings 
                WHERE faq_id IN (SELECT id FROM faq_data WHERE company_id = ?)
            """, (company_id,))
            counts['faq_embeddings'] = cursor.fetchone()['count']
            
            # line_settings
            cursor.execute("SELECT COUNT(*) as count FROM line_settings WHERE company_id = ?", (company_id,))
            counts['line_settings'] = cursor.fetchone()['count']
            
            # search_history
            cursor.execute("SELECT COUNT(*) as count FROM search_history WHERE company_id = ?", (company_id,))
            counts['search_history'] = cursor.fetchone()['count']
            
            # faq_history
            cursor.execute("SELECT COUNT(*) as count FROM faq_history WHERE company_id = ?", (company_id,))
            counts['faq_history'] = cursor.fetchone()['count']
            
            print(f"\n📊 関連データ数:")
            for table, count in counts.items():
                if count > 0:
                    print(f"  {table}: {count}件")
            
            return counts
    except Exception as e:
        print(f"❌ データカウントエラー: {e}")
        return {}


def delete_company_data(company_id):
    """会社データを削除（正しい順序で）"""
    try:
        with get_cursor() as cursor:
            deleted_counts = {}
            
            print(f"\n🗑️  削除開始: {company_id}")
            
            # 1. faq_embeddings (faq_dataに依存)
            print("  1/8 faq_embeddings削除中...")
            cursor.execute("""
                DELETE FROM faq_embeddings 
                WHERE faq_id IN (SELECT id FROM faq_data WHERE company_id = ?)
            """, (company_id,))
            deleted_counts['faq_embeddings'] = cursor.rowcount
            
            # 2. faq_data (companiesに依存)
            print("  2/8 faq_data削除中...")
            cursor.execute("DELETE FROM faq_data WHERE company_id = ?", (company_id,))
            deleted_counts['faq_data'] = cursor.rowcount
            
            # 3. users (companiesに依存)
            print("  3/8 users削除中...")
            cursor.execute("DELETE FROM users WHERE company_id = ?", (company_id,))
            deleted_counts['users'] = cursor.rowcount
            
            # 4. company_admins (companiesに依存)
            print("  4/8 company_admins削除中...")
            cursor.execute("DELETE FROM company_admins WHERE company_id = ?", (company_id,))
            deleted_counts['company_admins'] = cursor.rowcount
            
            # 5. line_settings (companiesに依存)
            print("  5/8 line_settings削除中...")
            cursor.execute("DELETE FROM line_settings WHERE company_id = ?", (company_id,))
            deleted_counts['line_settings'] = cursor.rowcount
            
            # 6. search_history (companiesに依存)
            print("  6/8 search_history削除中...")
            cursor.execute("DELETE FROM search_history WHERE company_id = ?", (company_id,))
            deleted_counts['search_history'] = cursor.rowcount
            
            # 7. faq_history (companiesに依存)
            print("  7/8 faq_history削除中...")
            cursor.execute("DELETE FROM faq_history WHERE company_id = ?", (company_id,))
            deleted_counts['faq_history'] = cursor.rowcount
            
            # 8. companies (最後に削除)
            print("  8/8 companies削除中...")
            cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))
            deleted_counts['companies'] = cursor.rowcount
            
            print(f"\n✅ データベース削除完了:")
            for table, count in deleted_counts.items():
                if count > 0:
                    print(f"  {table}: {count}件削除")
            
            return deleted_counts
            
    except Exception as e:
        print(f"❌ データベース削除エラー: {e}")
        raise


def delete_company_files(company_id):
    """会社のファイルシステムデータを削除"""
    try:
        company_dir = UnifiedConfig.get_data_path(company_id)
        
        if os.path.exists(company_dir):
            print(f"\n📁 ファイルシステム削除中: {company_dir}")
            
            # ディレクトリ内容を表示
            if os.path.isdir(company_dir):
                files = os.listdir(company_dir)
                if files:
                    print(f"  削除ファイル: {', '.join(files)}")
                else:
                    print(f"  空ディレクトリ")
            
            # ディレクトリ削除
            shutil.rmtree(company_dir)
            print(f"✅ ファイル削除完了")
        else:
            print(f"📁 ファイルディレクトリが存在しません: {company_dir}")
            
    except Exception as e:
        print(f"❌ ファイル削除エラー: {e}")


def main():
    """メイン処理"""
    if len(sys.argv) != 2:
        print("使用方法: python scripts/delete_company_data.py <company_id>")
        print("例: python scripts/delete_company_data.py demo-company")
        sys.exit(1)
    
    company_id = sys.argv[1]
    
    print(f"🏢 会社データ削除スクリプト")
    print(f"対象会社ID: {company_id}")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 会社情報確認
        if not get_company_info(company_id):
            sys.exit(1)
        
        # 2. 関連データ数確認
        counts = count_related_data(company_id)
        if not counts:
            sys.exit(1)
        
        # 3. 削除確認
        if not confirm_deletion(company_id):
            print("❌ 削除がキャンセルされました")
            sys.exit(0)
        
        # 4. データベースから削除
        delete_company_data(company_id)
        
        # 5. ファイルシステムから削除
        delete_company_files(company_id)
        
        print(f"\n🎉 削除完了! 会社ID '{company_id}' の全データが削除されました")
        print("📧 関連するメールアドレスがテストで再利用可能になりました")
        
    except Exception as e:
        print(f"\n❌ 削除処理中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()