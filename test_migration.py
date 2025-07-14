"""
移行後のFAQ検索機能テスト
test_migration.py
"""
import time
import os
from services.chat_service import get_response
from services.faq_migration import get_faq_data_from_db
from core.database import count_records

def test_faq_search():
    """FAQ検索機能の動作確認"""
    print("🔍 FAQ検索機能テスト")
    print("=" * 50)
    
    # テスト対象の会社ID
    test_companies = ["demo-company", "company_913f36_472935", "company_fc7b87b7"]
    
    # テスト用質問セット
    test_questions = [
        "チェックインの時間は？",
        "駐車場はありますか？",
        "Wi-Fiは使えますか？",
        "温泉について教えて",
        "子供連れでも大丈夫？"
    ]
    
    for company_id in test_companies:
        print(f"\n📊 【{company_id}】")
        
        # DB内のFAQ数を確認
        faq_data = get_faq_data_from_db(company_id)
        print(f"   FAQ件数: {len(faq_data)} 件")
        
        if not faq_data:
            print("   ⚠️  FAQデータが見つかりません")
            continue
        
        # エンベディング有無の確認
        with_embedding = len([f for f in faq_data if f['embedding'] is not None])
        print(f"   エンベディング: {with_embedding}/{len(faq_data)} 件")
        
        # 各質問をテスト
        for i, question in enumerate(test_questions[:3]):  # 最初の3問のみテスト
            print(f"\n   🤔 質問{i+1}: {question}")
            
            try:
                start_time = time.time()
                answer, input_tokens, output_tokens = get_response(
                    user_input=question,
                    company_id=company_id,
                    user_info="テストユーザー"
                )
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # ミリ秒
                print(f"   ⏱️  応答時間: {response_time:.2f}ms")
                print(f"   💬 回答: {answer[:100]}...")
                print(f"   📊 トークン: 入力{input_tokens}, 出力{output_tokens}")
                
            except Exception as e:
                print(f"   ❌ エラー: {e}")
        
        print("-" * 30)

def test_performance():
    """パフォーマンステスト"""
    print("\n⚡ パフォーマンステスト")
    print("=" * 50)
    
    company_id = "demo-company"  # 最大のデータセット
    test_question = "チェックインの時間を教えてください"
    
    print(f"📊 テスト対象: {company_id}")
    print(f"🤔 テスト質問: {test_question}")
    print(f"🔄 実行回数: 5回")
    
    response_times = []
    
    for i in range(5):
        print(f"\n   実行 {i+1}/5...")
        
        try:
            start_time = time.time()
            answer, input_tokens, output_tokens = get_response(
                user_input=test_question,
                company_id=company_id,
                user_info="パフォーマンステスト"
            )
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)
            
            print(f"   ⏱️  {response_time:.2f}ms")
            
        except Exception as e:
            print(f"   ❌ エラー: {e}")
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        
        print(f"\n📈 パフォーマンス結果:")
        print(f"   平均応答時間: {avg_time:.2f}ms")
        print(f"   最短応答時間: {min_time:.2f}ms")
        print(f"   最長応答時間: {max_time:.2f}ms")
        
        # パフォーマンス評価
        if avg_time < 100:
            print(f"   🚀 優秀 (100ms未満)")
        elif avg_time < 500:
            print(f"   ✅ 良好 (500ms未満)")
        elif avg_time < 1000:
            print(f"   ⚠️  普通 (1秒未満)")
        else:
            print(f"   🐌 要改善 (1秒以上)")

def test_database_status():
    """データベース状況確認"""
    print("\n🗄️  データベース状況")
    print("=" * 50)
    
    # 各テーブルの件数確認
    tables = [
        ("companies", "会社"),
        ("faq_data", "FAQ"),
        ("faq_embeddings", "エンベディング"),
        ("faq_history", "履歴"),
        ("company_admins", "管理者"),
        ("users", "ユーザー")
    ]
    
    for table_name, display_name in tables:
        try:
            count = count_records(table_name)
            print(f"   📊 {display_name}: {count:,} 件")
        except Exception as e:
            print(f"   ❌ {display_name}: エラー ({e})")
    
    # データベースファイルサイズ
    from core.database import get_db_path
    db_path = get_db_path()
    if os.path.exists(db_path):
        db_size = os.path.getsize(db_path)
        print(f"   💾 DBサイズ: {db_size:,} bytes ({db_size/1024:.1f} KB)")

def compare_old_vs_new():
    """新旧システムの比較"""
    print("\n📊 新旧システム比較")
    print("=" * 50)
    
    # 旧システム（PKLファイル）の確認
    companies_dir = "data/companies"
    old_system_files = 0
    old_system_size = 0
    
    if os.path.exists(companies_dir):
        for company_dir in os.listdir(companies_dir):
            company_path = os.path.join(companies_dir, company_dir)
            if os.path.isdir(company_path):
                for filename in ["faq.csv", "faq_with_embeddings.pkl"]:
                    file_path = os.path.join(company_path, filename)
                    if os.path.exists(file_path):
                        old_system_files += 1
                        old_system_size += os.path.getsize(file_path)
    
    # 新システム（SQLite）の確認
    from core.database import get_db_path
    db_path = get_db_path()
    new_system_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
    new_system_files = 1 if os.path.exists(db_path) else 0
    
    print(f"📁 旧システム (CSV/PKL):")
    print(f"   ファイル数: {old_system_files} 個")
    print(f"   総サイズ: {old_system_size:,} bytes ({old_system_size/1024:.1f} KB)")
    
    print(f"\n🗄️  新システム (SQLite):")
    print(f"   ファイル数: {new_system_files} 個")
    print(f"   総サイズ: {new_system_size:,} bytes ({new_system_size/1024:.1f} KB)")
    
    if old_system_size > 0:
        efficiency = (old_system_size - new_system_size) / old_system_size * 100
        print(f"\n💡 効率化:")
        if efficiency > 0:
            print(f"   ストレージ削減: {efficiency:.1f}%")
        else:
            print(f"   ストレージ増加: {abs(efficiency):.1f}%")
        print(f"   ファイル管理: {old_system_files} → {new_system_files} (-{old_system_files-new_system_files})")

def main():
    """メインテスト実行"""
    print("🧪 FAQ移行後テストスイート")
    print("=" * 60)
    print(f"⏰ テスト開始: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. データベース状況確認
        test_database_status()
        
        # 2. FAQ検索機能テスト
        test_faq_search()
        
        # 3. パフォーマンステスト
        test_performance()
        
        # 4. 新旧システム比較
        compare_old_vs_new()
        
        print(f"\n✅ 全テスト完了")
        print(f"⏰ テスト終了: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"\n❌ テスト実行エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()