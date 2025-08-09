#!/usr/bin/env python3
"""
会社データ一覧表示テストスクリプト
scripts/test_company_list.py

削除前に会社データを確認するためのスクリプト
"""
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_cursor


def list_all_companies():
    """全会社とその詳細情報を表示"""
    try:
        with get_cursor() as cursor:
            # 会社一覧取得（所在地情報含む）
            cursor.execute("""
                SELECT c.id, c.name, c.created_at, c.faq_count,
                       c.prefecture, c.city, c.address, c.postal_code, c.phone, c.website,
                       (SELECT COUNT(*) FROM users WHERE company_id = c.id) as user_count,
                       (SELECT COUNT(*) FROM company_admins WHERE company_id = c.id) as admin_count,
                       (SELECT COUNT(*) FROM faq_data WHERE company_id = c.id) as faq_data_count,
                       (SELECT COUNT(*) FROM line_settings WHERE company_id = c.id) as line_settings_count,
                       (SELECT COUNT(*) FROM search_history WHERE company_id = c.id) as search_history_count,
                       (SELECT COUNT(*) FROM faq_history WHERE company_id = c.id) as faq_history_count
                FROM companies c
                ORDER BY c.created_at DESC
            """)
            companies = cursor.fetchall()
            
            if not companies:
                print("❌ 会社データがありません")
                return
            
            print(f"📋 登録済み会社一覧 ({len(companies)}件)\n")
            
            for company in companies:
                print(f"🏢 {company['name']} (ID: {company['id']})")
                print(f"   作成日: {company['created_at']}")
                
                # 所在地情報
                location_parts = []
                if company['prefecture']:
                    location_parts.append(company['prefecture'])
                if company['city']:
                    location_parts.append(company['city'])
                if company['address']:
                    location_parts.append(company['address'])
                
                if location_parts:
                    print(f"   所在地: {' '.join(location_parts)}")
                    if company['postal_code']:
                        print(f"   郵便番号: {company['postal_code']}")
                    if company['phone']:
                        print(f"   電話番号: {company['phone']}")
                    if company['website']:
                        print(f"   ウェブサイト: {company['website']}")
                else:
                    print(f"   所在地: (未設定)")
                
                print(f"   データ詳細:")
                print(f"     - users: {company['user_count']}件")
                print(f"     - company_admins: {company['admin_count']}件") 
                print(f"     - faq_data: {company['faq_data_count']}件")
                print(f"     - line_settings: {company['line_settings_count']}件")
                print(f"     - search_history: {company['search_history_count']}件")
                print(f"     - faq_history: {company['faq_history_count']}件")
                
                # faq_embeddingsもカウント
                from core.database import DB_TYPE
                param_format = "%s" if DB_TYPE == "postgresql" else "?"
                cursor.execute(f"""
                    SELECT COUNT(*) as count FROM faq_embeddings 
                    WHERE faq_id IN (SELECT id FROM faq_data WHERE company_id = {param_format})
                """, (company['id'],))
                embedding_count = cursor.fetchone()['count']
                print(f"     - faq_embeddings: {embedding_count}件")
                
                # ユーザー詳細
                if company['user_count'] > 0:
                    cursor.execute(f"SELECT email, is_verified FROM users WHERE company_id = {param_format}", (company['id'],))
                    users = cursor.fetchall()
                    print("   ユーザー:")
                    for user in users:
                        status = "✅認証済み" if user['is_verified'] else "❌未認証"
                        print(f"     - {user['email']} ({status})")
                
                print()
                
    except Exception as e:
        print(f"❌ エラー: {e}")


if __name__ == "__main__":
    print("🏢 会社データ一覧表示\n")
    list_all_companies()