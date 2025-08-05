#!/usr/bin/env python3
"""
会社所在地機能テストスクリプト
scripts/test_company_location.py
"""
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import (get_company_from_db, get_company_location, 
                           update_company_location, get_cursor)


def test_company_location_functions():
    """会社所在地機能をテスト"""
    print("🧪 会社所在地機能テスト\n")
    
    # 既存の会社一覧を表示
    try:
        with get_cursor() as cursor:
            cursor.execute("SELECT id, name FROM companies")
            companies = cursor.fetchall()
            
            print("📋 既存の会社一覧:")
            for company in companies:
                print(f"  - {company['name']} (ID: {company['id']})")
            
            if not companies:
                print("  ❌ 会社データがありません")
                return
            
            # テスト対象の会社
            test_company_id = companies[0]['id']
            print(f"\n🎯 テスト対象: {test_company_id}")
            
            # 1. 会社情報取得テスト（新しいカラム含む）
            print(f"\n1️⃣ 会社情報取得テスト:")
            company_info = get_company_from_db(test_company_id)
            if company_info:
                print(f"  ✅ 会社情報取得成功:")
                for key, value in company_info.items():
                    print(f"    {key}: {value}")
            else:
                print(f"  ❌ 会社情報取得失敗")
                return
            
            # 2. 所在地情報取得テスト
            print(f"\n2️⃣ 所在地情報取得テスト:")
            location_info = get_company_location(test_company_id)
            if location_info is not None:
                print(f"  ✅ 所在地情報取得成功:")
                for key, value in location_info.items():
                    print(f"    {key}: {value if value else '(空)'}")
            else:
                print(f"  ❌ 所在地情報取得失敗")
                return
            
            # 3. 所在地情報更新テスト
            print(f"\n3️⃣ 所在地情報更新テスト:")
            test_location = {
                'prefecture': '大分県',
                'city': '別府市',
                'address': '北浜3-2-18',
                'postal_code': '874-0920',
                'phone': '097-532-1111',
                'website': 'https://example-ryokan.com'
            }
            
            success = update_company_location(test_company_id, test_location)
            if success:
                print(f"  ✅ 所在地情報更新成功")
                
                # 更新後の情報を確認
                updated_info = get_company_location(test_company_id)
                print(f"  📄 更新後の所在地情報:")
                for key, value in updated_info.items():
                    print(f"    {key}: {value}")
            else:
                print(f"  ❌ 所在地情報更新失敗")
            
            print(f"\n🎉 テスト完了!")
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")


if __name__ == "__main__":
    test_company_location_functions()