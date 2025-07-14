"""
FAQデータ移行ツール - 既存CSVからSQLiteへの移行
migration_tool.py
"""
import os
import sys
from datetime import datetime
from services.faq_migration import (
    init_faq_migration, backup_original_data, 
    migrate_all_companies, verify_migration
)
from core.database import initialize_database, backup_database
from config.settings import get_data_path

def print_banner():
    """バナー表示"""
    print("=" * 60)
    print("         FAQデータ移行ツール")
    print("     CSV/PKL -> SQLite Database")
    print("=" * 60)
    print()

def check_existing_data():
    """既存データの確認"""
    print("📊 既存データの確認中...")
    
    companies_dir = os.path.join(get_data_path(), "companies")
    if not os.path.exists(companies_dir):
        print("❌ companiesディレクトリが見つかりません")
        return False, []
    
    company_ids = []
    for company_dir in os.listdir(companies_dir):
        company_path = os.path.join(companies_dir, company_dir)
        if os.path.isdir(company_path):
            csv_path = os.path.join(company_path, "faq.csv")
            pkl_path = os.path.join(company_path, "faq_with_embeddings.pkl")
            
            has_csv = os.path.exists(csv_path)
            has_pkl = os.path.exists(pkl_path)
            
            if has_csv or has_pkl:
                company_ids.append(company_dir)
                csv_size = os.path.getsize(csv_path) if has_csv else 0
                pkl_size = os.path.getsize(pkl_path) if has_pkl else 0
                
                print(f"  📁 {company_dir}:")
                print(f"     CSV: {'✅' if has_csv else '❌'} ({csv_size:,} bytes)")
                print(f"     PKL: {'✅' if has_pkl else '❌'} ({pkl_size:,} bytes)")
    
    print(f"\n📈 移行対象: {len(company_ids)} 社")
    return len(company_ids) > 0, company_ids

def confirm_migration():
    """移行確認"""
    print("\n⚠️  重要: この操作により以下が実行されます:")
    print("   1. 既存CSVファイルのバックアップ作成")
    print("   2. SQLiteデータベースへの移行")
    print("   3. 移行結果の検証")
    print()
    
    try:
        response = input("🤔 続行しますか？ (yes/no): ").lower().strip()
        return response in ['yes', 'y', 'はい']
    except EOFError:
        # 非対話環境では自動的にyesとして扱う
        print("🤖 非対話環境のため自動的に続行します")
        return True

def run_migration():
    """メイン移行処理"""
    print_banner()
    
    # 1. 既存データの確認
    has_data, company_ids = check_existing_data()
    if not has_data:
        print("❌ 移行対象のデータが見つかりません")
        return False
    
    # 2. 移行確認
    if not confirm_migration():
        print("⏹️  移行をキャンセルしました")
        return False
    
    print("\n🚀 移行を開始します...")
    print(f"⏰ 開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 3. データベースのバックアップ
        print("\n📦 1. データベースのバックアップ中...")
        if backup_database():
            print("✅ データベースのバックアップ完了")
        else:
            print("⚠️  データベースのバックアップに失敗（続行）")
        
        # 4. 既存ファイルのバックアップ
        print("\n📦 2. 既存ファイルのバックアップ中...")
        if backup_original_data():
            print("✅ 既存ファイルのバックアップ完了")
        else:
            print("❌ 既存ファイルのバックアップに失敗")
            return False
        
        # 5. データベース・テーブルの初期化
        print("\n🗄️  3. データベースの初期化中...")
        if not initialize_database():
            print("❌ データベース初期化に失敗")
            return False
        
        if not init_faq_migration():
            print("❌ FAQマイグレーション初期化に失敗")
            return False
        
        print("✅ データベース初期化完了")
        
        # 6. 全会社データの移行
        print("\n🔄 4. データ移行中...")
        if not migrate_all_companies(show_progress=False):
            print("❌ データ移行に失敗")
            return False
        
        print("✅ 全データの移行完了")
        
        # 7. 移行結果の検証
        print("\n🔍 5. 移行結果の検証中...")
        all_success = True
        for company_id in company_ids:
            result = verify_migration(company_id)
            if result:
                status = "✅" if result['migration_success'] else "❌"
                print(f"   {status} {company_id}: {result['faq_count']}/{result['original_count']} 件")
                if not result['migration_success']:
                    all_success = False
            else:
                print(f"   ❌ {company_id}: 検証エラー")
                all_success = False
        
        if all_success:
            print("\n🎉 移行が正常に完了しました！")
            print("\n📋 移行後の推奨作業:")
            print("   1. アプリケーションの動作確認")
            print("   2. 既存CSVファイルの削除 (必要に応じて)")
            print("   3. バックアップディレクトリの確認")
        else:
            print("\n⚠️  一部の移行に問題がありました")
            print("詳細はログを確認してください")
        
        print(f"\n⏰ 完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return all_success
        
    except Exception as e:
        print(f"\n❌ 移行中にエラーが発生しました: {e}")
        return False

def show_status():
    """移行状況の確認"""
    print_banner()
    print("📊 現在の状況:")
    
    # データベースの状況
    from core.database import get_db_path, table_exists, count_records
    db_path = get_db_path()
    
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path)
        print(f"  📂 データベース: {db_path} ({db_size:,} bytes)")
        
        if table_exists("faq_data"):
            faq_count = count_records("faq_data")
            print(f"  📝 FAQ件数: {faq_count:,} 件")
        
        if table_exists("faq_embeddings"):
            embedding_count = count_records("faq_embeddings")
            print(f"  🧠 エンベディング件数: {embedding_count:,} 件")
        
        if table_exists("companies"):
            company_count = count_records("companies")
            print(f"  🏢 登録会社数: {company_count:,} 社")
    else:
        print("  ❌ データベースファイルが見つかりません")
    
    # CSVファイルの状況
    print("\n📁 既存CSVファイル:")
    has_data, company_ids = check_existing_data()
    
    # バックアップの状況
    backup_dir = os.path.join(get_data_path(), "backup_csv_pkl")
    if os.path.exists(backup_dir):
        backup_size = sum(os.path.getsize(os.path.join(dirpath, filename))
                         for dirpath, dirnames, filenames in os.walk(backup_dir)
                         for filename in filenames)
        print(f"\n💾 バックアップ: {backup_dir} ({backup_size:,} bytes)")
    else:
        print("\n💾 バックアップ: なし")

def main():
    """メイン関数"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "migrate":
            success = run_migration()
            sys.exit(0 if success else 1)
        elif command == "status":
            show_status()
            sys.exit(0)
        elif command == "help":
            print("📖 使用方法:")
            print("  python migration_tool.py migrate  - 移行を実行")
            print("  python migration_tool.py status   - 現在の状況を確認")
            print("  python migration_tool.py help     - このヘルプを表示")
            sys.exit(0)
        else:
            print(f"❌ 不明なコマンド: {command}")
            print("使用方法: python migration_tool.py [migrate|status|help]")
            sys.exit(1)
    else:
        # 対話式モード
        print_banner()
        print("🛠️  対話式モード")
        print("1. migrate - 移行を実行")
        print("2. status  - 現在の状況を確認")
        print("3. exit    - 終了")
        print()
        
        while True:
            command = input("コマンドを選択してください (1-3): ").strip()
            
            if command in ['1', 'migrate']:
                success = run_migration()
                if success:
                    break
            elif command in ['2', 'status']:
                show_status()
                print()
            elif command in ['3', 'exit']:
                print("👋 終了します")
                break
            else:
                print("❌ 無効な選択です")

if __name__ == "__main__":
    main()