#!/usr/bin/env python3
"""
FAQ多言語対応のためのDBマイグレーション
faq_dataテーブルにlanguageカラムを追加
"""

import sqlite3
import os
import sys

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.unified_config import UnifiedConfig
from core.database import execute_query, fetch_dict

def add_language_column():
    """faq_dataテーブルにlanguageカラムを追加"""
    
    # データベースファイルのパス
    db_path = os.path.join(UnifiedConfig.get_data_path(), "faq_database.db")
    
    if not os.path.exists(db_path):
        print(f"データベースファイルが見つかりません: {db_path}")
        return False
    
    try:
        print("faq_dataテーブルにlanguageカラムを追加中...")
        
        # テーブルの現在の構造を確認
        check_query = "PRAGMA table_info(faq_data)"
        columns = fetch_dict(check_query)
        
        # languageカラムが既に存在するかチェック
        language_exists = any(col['name'] == 'language' for col in columns)
        
        if language_exists:
            print("languageカラムは既に存在します。")
        else:
            # languageカラムを追加
            alter_query = "ALTER TABLE faq_data ADD COLUMN language TEXT DEFAULT 'ja'"
            execute_query(alter_query)
            print("languageカラムを追加しました。")
        
        # 既存データのlanguageカラムを'ja'で更新（NULLまたは空の場合）
        update_query = "UPDATE faq_data SET language = 'ja' WHERE language IS NULL OR language = ''"
        execute_query(update_query)
        print("既存データのlanguageカラムを'ja'に設定しました。")
        
        # 結果を確認
        verify_query = "SELECT COUNT(*) as total, language FROM faq_data GROUP BY language"
        results = fetch_dict(verify_query)
        
        print("\n=== マイグレーション結果 ===")
        for result in results:
            print(f"言語: {result['language']}, 件数: {result['total']}")
        
        return True
        
    except Exception as e:
        print(f"マイグレーションエラー: {e}")
        return False

if __name__ == "__main__":
    print("FAQ多言語対応マイグレーション開始")
    print("=" * 50)
    
    success = add_language_column()
    
    if success:
        print("\n✅ マイグレーション完了")
    else:
        print("\n❌ マイグレーション失敗")
        sys.exit(1)