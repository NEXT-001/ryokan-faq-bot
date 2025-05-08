"""
テストモードを強制的に有効化するスクリプト
force_test_mode.py
"""
import os
import sys

# テストモードを有効化
os.environ["TEST_MODE"] = "true"
print("テストモードを強制的に有効化しました。")

# テストモードの確認（config.settings を使用）
try:
    from config.settings import is_test_mode
    test_mode = is_test_mode()
    print(f"設定されたテストモード: {test_mode}")
except ImportError:
    print("config.settings をインポートできませんでした。")

# FAQデータの存在確認
if os.path.exists("data/faq_with_embeddings.pkl"):
    print("FAQデータが存在します: data/faq_with_embeddings.pkl")
else:
    print("FAQデータが存在しません。")

print("\nアプリケーションを起動するには、以下のコマンドを実行してください:")
print("streamlit run main.py")