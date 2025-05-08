"""
デバッグ用の関数
debug_functions.py
"""
import os
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json

def inspect_faq_data():
    """
    FAQ データの内容を検査して問題を特定する
    結果をデバッグレポートとして保存
    """
    report = {"status": "unknown", "errors": [], "findings": []}
    
    try:
        # データファイルの存在確認
        if not os.path.exists("data/faq_with_embeddings.pkl"):
            report["status"] = "error"
            report["errors"].append("データファイル data/faq_with_embeddings.pkl が存在しません")
            return report
        
        # データの読み込み
        df = pd.read_pickle("data/faq_with_embeddings.pkl")
        report["findings"].append(f"データエントリ数: {len(df)}")
        
        # カラム確認
        columns = df.columns.tolist()
        report["findings"].append(f"カラム: {columns}")
        
        if "question" not in columns or "answer" not in columns:
            report["status"] = "error"
            report["errors"].append("必要なカラム (question, answer) がありません")
            return report
            
        if "embedding" not in columns:
            report["status"] = "error"
            report["errors"].append("embedding カラムがありません")
            return report
        
        # エンベディングの確認
        embedding_samples = {}
        for i, row in df.iterrows():
            question = row["question"]
            embedding = row["embedding"]
            
            # エンベディングが None またはリストでない場合
            if embedding is None or not isinstance(embedding, list):
                report["status"] = "error"
                report["errors"].append(f"エントリ {i}: エンベディングがNoneまたはリスト型ではありません")
                continue
                
            # エンベディングの次元数を確認
            embedding_dim = len(embedding)
            if embedding_dim != 1536:
                report["findings"].append(f"エントリ {i}: エンベディングの次元数が 1536 ではなく {embedding_dim} です")
            
            # サンプルとして最初の5要素を記録
            embedding_samples[question[:20]] = embedding[:5]
            
            # すべて0または非常に小さい値かを確認
            if all(abs(x) < 1e-6 for x in embedding):
                report["findings"].append(f"エントリ {i}: エンベディングがほぼすべて0です")
                
        report["embedding_samples"] = embedding_samples
        
        # エンベディング間の類似性を計算
        embeddings = df["embedding"].tolist()
        similarities = cosine_similarity(embeddings)
        
        # 類似度の統計情報
        avg_similarity = np.mean(similarities)
        max_similarity = np.max(similarities - np.eye(len(similarities)))  # 対角線を除外
        min_similarity = np.min(similarities + np.eye(len(similarities)) * 100)  # 対角線を除外
        
        report["findings"].append(f"平均類似度: {avg_similarity:.4f}")
        report["findings"].append(f"最大類似度 (自分自身を除く): {max_similarity:.4f}")
        report["findings"].append(f"最小類似度: {min_similarity:.4f}")
        
        # 高い類似度のペアを特定
        high_similarity_threshold = 0.95  # 非常に高い類似度のしきい値
        high_similarity_pairs = []
        
        for i in range(len(similarities)):
            for j in range(i+1, len(similarities)):  # 対角線より上だけを見る
                if similarities[i, j] > high_similarity_threshold:
                    high_similarity_pairs.append({
                        "question1": df.iloc[i]["question"],
                        "question2": df.iloc[j]["question"],
                        "similarity": similarities[i, j]
                    })
        
        if high_similarity_pairs:
            report["findings"].append(f"類似度が {high_similarity_threshold} を超えるペア: {len(high_similarity_pairs)}")
            report["high_similarity_pairs"] = high_similarity_pairs[:10]  # 最初の10個だけ記録
        
        # テスト質問に対する回答を評価
        test_questions = [
            "温泉について教えてください",
            "子供連れで利用できますか",
            "チェックインの時間は何時ですか",
            "駐車場はありますか",
            "食事はどのようなものが出ますか"
        ]
        
        test_results = []
        for question in test_questions:
            # 簡易的なキーワード抽出
            keywords = set(question.replace("について", "").replace("は", "").replace("ですか", "").split())
            
            # キーワードが含まれる質問を見つける（デバッグ用）
            matched_questions = []
            for i, row in df.iterrows():
                faq_question = row["question"]
                if any(keyword in faq_question for keyword in keywords):
                    matched_questions.append(faq_question)
            
            # 類似度を計算するための疑似エンベディング（ハッシュベースのランダム）
            import hashlib
            hash_obj = hashlib.md5(question.encode())
            hash_val = int(hash_obj.hexdigest(), 16)
            np.random.seed(hash_val)
            test_embedding = np.random.rand(1536).tolist()
            
            # コサイン類似度の計算
            similarities = cosine_similarity([test_embedding], embeddings)
            best_idx = np.argmax(similarities)
            similarity_score = similarities[0][best_idx]
            
            test_results.append({
                "question": question,
                "best_match": df.iloc[best_idx]["question"],
                "answer": df.iloc[best_idx]["answer"],
                "similarity_score": float(similarity_score),
                "keyword_matches": matched_questions
            })
        
        report["test_results"] = test_results
        
        # ステータスの設定
        if report["errors"]:
            report["status"] = "error"
        elif avg_similarity > 0.9:
            report["status"] = "warning"
            report["findings"].append("エンベディング間の平均類似度が非常に高いです。これにより、異なる質問でも同じ回答が返される可能性があります。")
        else:
            report["status"] = "ok"
        
        return report
        
    except Exception as e:
        report["status"] = "error"
        report["errors"].append(f"検査中にエラーが発生しました: {str(e)}")
        return report
    
def test_embeddings(test_texts):
    """
    テストテキストのエンベディングを生成し、類似度を計算する
    
    Args:
        test_texts (list): テスト用のテキストリスト
        
    Returns:
        dict: テスト結果
    """
    from services.embedding_service import get_embedding
    
    results = {"embeddings": {}, "similarities": {}}
    
    try:
        # 各テキストのエンベディングを取得
        embeddings = []
        for text in test_texts:
            embedding = get_embedding(text)
            embeddings.append(embedding)
            # サンプルとして最初の5要素を記録
            results["embeddings"][text] = embedding[:5]
        
        # エンベディング間の類似度を計算
        similarities = cosine_similarity(embeddings)
        
        # 類似度マトリックスを記録
        for i, text1 in enumerate(test_texts):
            results["similarities"][text1] = {}
            for j, text2 in enumerate(test_texts):
                results["similarities"][text1][text2] = similarities[i, j]
        
        return results
    
    except Exception as e:
        return {"error": str(e)}

def save_debug_report(report, filename="debug_report.json"):
    """デバッグレポートをJSONファイルとして保存"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"レポート保存エラー: {e}")
        return False
        
def run_diagnostics():
    """
    診断を実行して結果を保存
    """
    # FAQデータの検査
    faq_report = inspect_faq_data()
    save_debug_report(faq_report, "faq_debug_report.json")
    
    # テストエンベディングの検査
    test_texts = [
        "温泉について教えてください",
        "子供連れで利用できますか",
        "食事はどのようなものが出ますか",
        "チェックインの時間は何時ですか",
        "駐車場はありますか"
    ]
    
    embedding_report = test_embeddings(test_texts)
    save_debug_report(embedding_report, "embedding_debug_report.json")
    
    return {
        "faq_report": faq_report,
        "embedding_report": embedding_report
    }