#!/usr/bin/env python3
"""
_get_company_base_location メソッドテストスクリプト
scripts/test_company_base_location.py

companiesテーブルからの所在地取得をテスト
"""
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.enhanced_location_service import EnhancedLocationService
from core.database import get_cursor


def test_company_base_location():
    """_get_company_base_location メソッドをテスト"""
    print("🧪 _get_company_base_location メソッドテスト\n")
    
    # EnhancedLocationService のインスタンス作成
    location_service = EnhancedLocationService()
    
    # 既存の会社一覧を取得
    try:
        with get_cursor() as cursor:
            cursor.execute("""
                SELECT id, name, prefecture, city, address 
                FROM companies 
                ORDER BY created_at DESC
            """)
            companies = cursor.fetchall()
            
            print("📋 テスト対象会社:")
            for company in companies:
                location_parts = []
                if company['prefecture']:
                    location_parts.append(company['prefecture'])
                if company['city']:
                    location_parts.append(company['city'])
                if company['address']:
                    location_parts.append(company['address'])
                
                location_str = ' '.join(location_parts) if location_parts else '(未設定)'
                print(f"  - {company['name']} (ID: {company['id']}) - {location_str}")
            
            print(f"\n🔍 各会社の_get_company_base_location 結果:\n")
            
            # 各会社で _get_company_base_location をテスト
            for company in companies:
                company_id = company['id']
                company_name = company['name']
                
                print(f"🏢 {company_name} (ID: {company_id})")
                
                # メソッド実行
                result = location_service._get_company_base_location(company_id)
                
                if result:
                    print(f"  ✅ 取得成功:")
                    print(f"    都道府県: {result.get('prefecture', 'なし')}")
                    print(f"    市区町村: {result.get('city', 'なし')}")
                    print(f"    住所詳細: {result.get('address', 'なし')}")
                    print(f"    郵便番号: {result.get('postal_code', 'なし')}")
                    print(f"    地域: {result.get('region', 'なし')}")
                    print(f"    取得タイプ: {result.get('type', 'なし')}")
                else:
                    print(f"  ❌ 取得失敗")
                
                print()
            
            # フォールバックテスト
            print(f"🔄 フォールバックテスト:\n")
            
            test_cases = [
                ('demo-company', 'デモ会社テスト'),
                ('company_oita_test', 'oitaヒントテスト'),
                ('company_tokyo_test', 'tokyoヒントテスト'),
                ('unknown_company_123', '不明会社テスト')
            ]
            
            for test_id, test_desc in test_cases:
                print(f"🧪 {test_desc} (ID: {test_id})")
                result = location_service._get_company_base_location(test_id)
                
                if result:
                    print(f"  都道府県: {result.get('prefecture')}")
                    print(f"  市区町村: {result.get('city')}")
                    print(f"  地域: {result.get('region')}")
                    print(f"  取得タイプ: {result.get('type')}")
                else:
                    print(f"  ❌ 取得失敗")
                print()
            
            print(f"🎉 テスト完了!")
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")


if __name__ == "__main__":
    test_company_base_location()