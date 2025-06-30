"""
JSONからSQLiteへのデータ移行スクリプト
migrate_to_sqlite.py
"""
import os
import sys

# プロジェクトルートをパスに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

def main():
    """メイン実行関数"""
    
    print("=== JSONからSQLiteへのデータ移行 ===\n")
    
    try:
        # company_serviceから移行関数をインポート
        from services.company_service import migrate_json_to_sqlite, get_company_list
        from core.database import check_database_integrity
        
        print("📋 移行前の状況確認...")
        
        # 移行前の企業一覧を確認
        companies_before = get_company_list()
        print(f"移行前の企業数: {len(companies_before)}")
        
        # データベース整合性チェック
        print("\n🔍 データベース整合性チェック...")
        check_database_integrity()
        
        # 移行実行
        print("\n🚀 データ移行を開始します...")
        
        success = migrate_json_to_sqlite()
        
        if success:
            print("\n✅ データ移行が完了しました！")
            
            # 移行後の確認
            companies_after = get_company_list()
            print(f"移行後の企業数: {len(companies_after)}")
            
            print("\n📊 移行された企業一覧:")
            for company in companies_after:
                print(f"  - {company['id']}: {company['name']} (管理者: {company['admin_count']}名)")
            
            print("\n📝 次のステップ:")
            print("1. Streamlitアプリケーションを再起動: streamlit run main.py")
            print("2. 管理者ページでログインテスト")
            print("3. 正常に動作することを確認")
            print("4. 問題なければJSONファイルをバックアップ後削除可能")
            
        else:
            print("\n❌ データ移行に失敗しました")
            print("詳細はログを確認してください")
            
    except ImportError as e:
        print(f"❌ モジュールインポートエラー: {e}")
        print("core/database.py と services/company_service.py が正しく配置されているか確認してください")
        
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        import traceback
        print(traceback.format_exc())

def test_authentication():
    """認証テストを実行"""
    
    print("\n🔐 認証テスト実行中...")
    
    try:
        from services.company_service import verify_company_admin_by_email, verify_company_admin
        
        # テスト用データ
        test_cases = [
            {
                "company_id": "demo-company",
                "username": "admin",
                "email": "admin@example.com", 
                "password": "admin123"
            },
            {
                "company_id": "company_913f36_472935",
                "username": "admin",
                "email": "kangju80@gmail.com",
                "password": "admin123"
            }
        ]
        
        for test_case in test_cases:
            company_id = test_case["company_id"]
            username = test_case["username"]
            email = test_case["email"]
            password = test_case["password"]
            
            print(f"\n📋 テスト対象: {company_id}")
            
            # ユーザー名ベース認証テスト
            print(f"  🔑 ユーザー名認証: {username}")
            success1, result1 = verify_company_admin(company_id, username, password)
            print(f"    結果: {'✅ 成功' if success1 else '❌ 失敗'} - {result1}")
            
            # メールベース認証テスト
            print(f"  📧 メール認証: {email}")
            success2, result2 = verify_company_admin_by_email(company_id, email, password)
            print(f"    結果: {'✅ 成功' if success2 else '❌ 失敗'}")
            if success2 and isinstance(result2, dict):
                print(f"    企業名: {result2.get('company_name')}")
                print(f"    ユーザー名: {result2.get('username')}")
        
    except Exception as e:
        print(f"❌ 認証テストエラー: {e}")

def backup_json_files():
    """JSONファイルをバックアップ"""
    
    print("\n💾 JSONファイルのバックアップ...")
    
    try:
        import shutil
        from datetime import datetime
        from utils.constants import get_data_path
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"json_backup_{timestamp}"
        
        base_dir = get_data_path()
        companies_dir = os.path.join(base_dir, "companies")
        
        if os.path.exists(companies_dir):
            shutil.copytree(companies_dir, backup_dir)
            print(f"✅ バックアップ完了: {backup_dir}")
            
            # バックアップ内容を確認
            backup_count = len([d for d in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, d))])
            print(f"📁 バックアップされた企業数: {backup_count}")
            
            return backup_dir
        else:
            print("⚠️ バックアップ対象のディレクトリが存在しません")
            return None
            
    except Exception as e:
        print(f"❌ バックアップエラー: {e}")
        return None

if __name__ == "__main__":
    # メイン処理
    main()
    
    # 認証テスト
    test_authentication()
    
    # バックアップオプション
    print("\n" + "="*50)
    backup_choice = input("JSONファイルをバックアップしますか？ (y/n): ")
    if backup_choice.lower() == 'y':
        backup_path = backup_json_files()
        if backup_path:
            print(f"\n📁 バックアップパス: {backup_path}")
            
            delete_choice = input("元のJSONファイルを削除しますか？ (y/n): ")
            if delete_choice.lower() == 'y':
                try:
                    from utils.constants import get_data_path
                    import shutil
                    
                    companies_dir = os.path.join(get_data_path(), "companies")
                    if os.path.exists(companies_dir):
                        shutil.rmtree(companies_dir)
                        print("✅ 元のJSONファイルを削除しました")
                    
                except Exception as e:
                    print(f"❌ 削除エラー: {e}")
    
    print("\n🎉 処理完了！")