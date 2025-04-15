# ファイル: regenerate_data.py (プロジェクトルートに配置)
from services.embedding_service import create_embeddings

print("FAQデータと改善されたエンベディングを生成中...")
create_embeddings()
print("データ生成が完了しました。")