#!/usr/bin/env python3
"""
テスト用会社所在地更新スクリプト
scripts/update_test_locations.py
"""
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import update_company_location


def update_test_company_locations():
    """テスト用の会社所在地を更新"""
    print("🏢 テスト用会社所在地更新\n")
    
    # 更新するテストデータ
    test_locations = [
        {
            'company_id': 'company_913f36_472935',
            'name': 'デモ２３企業',
            'location': {
                'prefecture': '京都府',
                'city': '京都市',
                'address': '東山区清水1-294',
                'postal_code': '605-0862',
                'phone': '075-551-1234',
                'website': 'https://kyoto-example.com'
            }
        },
        {
            'company_id': 'company_fc7b87b7',
            'name': 'デモ３３会社',
            'location': {
                'prefecture': '東京都',
                'city': '渋谷区',
                'address': '道玄坂2-10-7',
                'postal_code': '150-0043',
                'phone': '03-5456-7890',
                'website': 'https://tokyo-example.com'
            }
        }
    ]
    
    for company_data in test_locations:
        company_id = company_data['company_id']
        company_name = company_data['name']
        location = company_data['location']
        
        print(f"📍 {company_name} (ID: {company_id}) を更新中...")
        print(f"   所在地: {location['prefecture']} {location['city']} {location['address']}")
        
        success = update_company_location(company_id, location)
        
        if success:
            print(f"   ✅ 更新成功\n")
        else:
            print(f"   ❌ 更新失敗\n")
    
    print("🎉 テスト用所在地更新完了!")


if __name__ == "__main__":
    update_test_company_locations()