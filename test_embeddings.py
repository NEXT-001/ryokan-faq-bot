"""
エンベディングと回答をテストするスクリプト
test_embeddings.py
"""
import os
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from services.chat_service import get_response

# テストモードを強制的に有効化
os.environ["TEST_MODE"] = "true"

def test_responses():
    """
    様々な質問に対する回答をテストする
    """
    test_questions = [
        "温泉について教えてください",
        "子供連れでも大丈夫ですか？",
        "食事はどんな内容ですか",
        "チェックインは何時からできますか",
        "部屋のタイプはどんなものがありますか",
        "駐車場はありますか"
    ]
    
    print("回答テスト:")
    print("="*50)
    
    for question in test_questions:
        print(f"\n質問: {question}")
        answer, _, _ = get_response(question)
        print(f"回答: {answer}")
    
    print("\n" + "="*50)

def analyze_embeddings():
    """
    保存されたエンベディングを分析する
    """
    if not os.path.exists("data/faq_with_embeddings.pkl"):
        print("エンベディングデータが見つかりません。")
        return
    
    df = pd.read_pickle("data/faq_with_embeddings.pkl")
    print(f"データエントリ数: {len(df)}")
    
    # エンベディングの次元数を確認
    first_embedding = df["embedding"].iloc[0]
    print(f"エンベディングの次元数: {len(first_embedding)}")
    
    # エンベディング間の類似度を計算
    embeddings = df["embedding"].tolist()
    similarities = cosine_similarity(embeddings)
    
    # 対角要素（自分自身との類似度）を0にする
    np.fill_diagonal(similarities, 0)
    
    # 類似度の統計
    avg_similarity = np.mean(similarities)
    max_similarity = np.max(similarities)
    min_similarity = np.min(similarities)
    
    print(f"平均類似度: {avg_similarity:.4f}")
    print(f"最大類似度: {max_similarity:.4f}")
    print(f"最小類似度: {min_similarity:.4f}")
    
    # 最も類似しているペアを見つける
    max_i, max_j = np.unravel_index(np.argmax(similarities), similarities.shape)
    print("\n最も類似しているペア:")
    print(f"質問1: {df['question'].iloc[max_i]}")
    print(f"質問2: {df['question'].iloc[max_j]}")
    print(f"類似度: {similarities[max_i, max_j]:.4f}")
    
    # テスト質問に対するマッチングをシミュレート
    test_questions = [
        "温泉について教えてください",
        "子供連れでも大丈夫ですか？",
        "食事はどんな内容ですか"
    ]
    
    from services.embedding_service import get_embedding
    
    print("\nテスト質問の類似度シミュレーション:")
    for question in test_questions:
        print(f"\n質問: {question}")
        test_embedding = get_embedding(question)
        
        # 類似度の計算
        test_similarities = cosine_similarity([test_embedding], embeddings)[0]
        best_idx = np.argmax(test_similarities)
        similarity_score = test_similarities[best_idx]
        
        print(f"最も類似しているFAQ: {df['question'].iloc[best_idx]}")
        print(f"類似度スコア: {similarity_score:.4f}")
        print(f"回答: {df['answer'].iloc[best_idx]}")

if __name__ == "__main__":
    # エンベディングの分析
    print("エンベディングの分析:")
    print("="*50)
    analyze_embeddings()
    print("\n")
    
    # 回答のテスト
    test_responses()