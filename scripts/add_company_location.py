#!/usr/bin/env python3
"""
会社テーブルに所在地カラムを追加するマイグレーションスクリプト
scripts/add_company_location.py

追加するカラム:
- prefecture (都道府県)
- city (市区町村)  
- address (住所詳細)
- postal_code (郵便番号)
- phone (電話番号)
- website (ウェブサイト)
"""
import sys
import os
from datetime import datetime

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_cursor


def check_table_structure():
    """現在のテーブル構造を確認"""
    try:
        with get_cursor() as cursor:
            cursor.execute("PRAGMA table_info(companies)")
            columns = cursor.fetchall()
            
            print("📋 現在のcompaniesテーブル構造:")
            for col in columns:
                print(f"  - {col['name']}: {col['type']} {'(NOT NULL)' if col['notnull'] else ''} {'(PK)' if col['pk'] else ''}")
            
            return [col['name'] for col in columns]
    except Exception as e:
        print(f"❌ テーブル構造確認エラー: {e}")
        return []


def add_location_columns():
    """所在地関連カラムを追加"""
    try:
        with get_cursor() as cursor:
            # 既存カラムをチェック
            existing_columns = check_table_structure()
            
            # 追加するカラムの定義
            new_columns = [
                ("prefecture", "TEXT", "都道府県"),
                ("city", "TEXT", "市区町村"),
                ("address", "TEXT", "住所詳細"),
                ("postal_code", "TEXT", "郵便番号"),
                ("phone", "TEXT", "電話番号"),
                ("website", "TEXT", "ウェブサイトURL")
            ]
            
            print(f"\n🔧 所在地カラムを追加中...")
            
            for column_name, column_type, description in new_columns:
                if column_name not in existing_columns:
                    print(f"  ✓ {column_name} ({description}) を追加中...")
                    cursor.execute(f"ALTER TABLE companies ADD COLUMN {column_name} {column_type}")
                else:
                    print(f"  ⚠️ {column_name} は既に存在します")
            
            print(f"✅ カラム追加完了")
            return True
            
    except Exception as e:
        print(f"❌ カラム追加エラー: {e}")
        return False


def verify_migration():
    """マイグレーション結果を確認"""
    try:
        with get_cursor() as cursor:
            print(f"\n🔍 マイグレーション結果確認:")
            
            # 新しいテーブル構造確認
            cursor.execute("PRAGMA table_info(companies)")
            columns = cursor.fetchall()
            
            location_columns = ['prefecture', 'city', 'address', 'postal_code', 'phone', 'website']
            
            print("📋 更新後のcompaniesテーブル構造:")
            for col in columns:
                is_new = col['name'] in location_columns
                marker = "🆕 " if is_new else "   "
                print(f"{marker}{col['name']}: {col['type']} {'(NOT NULL)' if col['notnull'] else ''} {'(PK)' if col['pk'] else ''}")
            
            # 既存データのカウント
            cursor.execute("SELECT COUNT(*) as count FROM companies")
            count = cursor.fetchone()['count']
            print(f"\n📊 既存会社データ: {count}件")
            
            if count > 0:
                print("💡 既存会社データの所在地情報は空（NULL）になります")
                print("   管理画面から各会社の所在地を更新してください")
            
            return True
            
    except Exception as e:
        print(f"❌ 確認エラー: {e}")
        return False


def main():
    """メイン処理"""
    print(f"🏢 会社テーブル所在地カラム追加スクリプト")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 現在の構造確認
        existing_columns = check_table_structure()
        if not existing_columns:
            print("❌ テーブル構造の確認に失敗しました")
            sys.exit(1)
        
        # 2. カラム追加
        if not add_location_columns():
            print("❌ カラム追加に失敗しました")
            sys.exit(1)
        
        # 3. 結果確認
        if not verify_migration():
            print("❌ マイグレーション確認に失敗しました")
            sys.exit(1)
        
        print(f"\n🎉 マイグレーション完了!")
        print("📝 次のステップ:")
        print("  1. 管理画面で既存会社の所在地情報を入力")
        print("  2. 新規会社登録時に所在地入力フィールドを追加")
        print("  3. 位置情報サービスでの活用")
        
    except Exception as e:
        print(f"\n❌ マイグレーション中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()