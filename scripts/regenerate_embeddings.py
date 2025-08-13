"""
エンベディング再生成スクリプト
scripts/regenerate_embeddings.py

破損したエンベディングデータを削除して新しく生成する
"""
import os
import sys

# プロジェクトルートディレクトリをPythonパスに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

from services.faq_migration import cleanup_corrupted_embeddings, get_faq_data_from_db
from services.embedding_service import create_embeddings


def regenerate_embeddings_for_company(company_id):
    """特定企業のエンベディングを再生成"""
    print(f"[REGENERATE] 企業 {company_id} のエンベディング再生成開始")
    
    try:
        # 1. 既存の破損エンベディングを削除
        deleted_count = cleanup_corrupted_embeddings(company_id)
        print(f"[REGENERATE] 削除されたエンベディング: {deleted_count}件")
        
        # 2. FAQデータを取得
        faq_data = get_faq_data_from_db(company_id)
        if not faq_data:
            print(f"[REGENERATE] エラー: 企業 {company_id} のFAQデータが見つかりません")
            return False
        
        print(f"[REGENERATE] FAQデータ: {len(faq_data)}件")
        
        # 3. エンベディングを再生成
        success = create_embeddings(company_id, show_progress=False)
        if success:
            print(f"[REGENERATE] 企業 {company_id} のエンベディング再生成完了")
            return True
        else:
            print(f"[REGENERATE] 企業 {company_id} のエンベディング再生成失敗")
            return False
            
    except Exception as e:
        print(f"[REGENERATE] エラー: {e}")
        return False


def regenerate_all_embeddings():
    """全企業のエンベディングを再生成"""
    print("[REGENERATE] 全企業のエンベディング再生成開始")
    
    try:
        # 1. 全ての破損エンベディングを削除
        deleted_count = cleanup_corrupted_embeddings()
        print(f"[REGENERATE] 削除されたエンベディング: {deleted_count}件")
        
        # 2. 全企業のエンベディングを再生成
        # 全企業を対象とする場合は、各企業に対してcreate_embeddingsを実行
        from core.database import fetch_dict
        
        # 全ての企業IDを取得
        companies_query = "SELECT DISTINCT company_id FROM faq_data"
        companies = fetch_dict(companies_query)
        
        success_count = 0
        total_count = len(companies)
        
        for company in companies:
            company_id = company['company_id']
            print(f"[REGENERATE] 企業 {company_id} のエンベディング再生成中...")
            if create_embeddings(company_id, show_progress=False):
                success_count += 1
                print(f"[REGENERATE] 企業 {company_id} 完了")
            else:
                print(f"[REGENERATE] 企業 {company_id} 失敗")
        
        print(f"[REGENERATE] 全企業エンベディング再生成完了: {success_count}/{total_count}")
        return success_count == total_count
            
    except Exception as e:
        print(f"[REGENERATE] エラー: {e}")
        return False


def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="エンベディング再生成ツール")
    parser.add_argument("--company", "-c", type=str, help="対象企業ID（省略時は全企業）")
    parser.add_argument("--force", "-f", action="store_true", help="確認なしで実行")
    
    args = parser.parse_args()
    
    if args.company:
        target = f"企業「{args.company}」"
        action = lambda: regenerate_embeddings_for_company(args.company)
    else:
        target = "全企業"
        action = lambda: regenerate_all_embeddings()
    
    if not args.force:
        confirm = input(f"{target}のエンベディングを再生成しますか？ (y/N): ")
        if confirm.lower() != 'y':
            print("キャンセルされました。")
            return
    
    print(f"\n{target}のエンベディング再生成を開始します...")
    success = action()
    
    if success:
        print(f"\n✅ {target}のエンベディング再生成が完了しました。")
    else:
        print(f"\n❌ {target}のエンベディング再生成に失敗しました。")


if __name__ == "__main__":
    main()