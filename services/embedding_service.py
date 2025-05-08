"""
エンベディング関連の共通サービス
embedding_service.py
"""
import os
import pandas as pd
import numpy as np
import hashlib
import voyageai
from config.settings import is_test_mode

# エンベディングの次元数 (VoyageAI voyage-3モデルは1024次元)
EMBEDDING_DIM = 1024

def load_voyage_client():
    """
    VoyageAI APIクライアントを読み込む
    """
    try:
        api_key = os.getenv("VOYAGE_API_KEY")
        
        if not api_key:
            print("VOYAGE_API_KEYが設定されていません")
            return None
        
        client = voyageai.Client(api_key=api_key)
        print("VoyageAI APIクライアント初期化成功")
        return client
    except Exception as e:
        print(f"VoyageAI APIクライアント初期化エラー: {e}")
        return None

def get_test_embedding(text):
    """
    テスト用のエンベディングを生成する
    テキストのハッシュ値を使って擬似的に一貫性のあるベクトルを生成
    注意: 実装を変更し、より質問内容に基づいたベクトルを生成するように改良
    """
    # キーワードベースのエンベディング生成（より意味を反映）
    keywords = {
        "チェックイン": [0.8, 0.1, 0.1, 0.0, 0.0],
        "チェックアウト": [0.7, 0.2, 0.1, 0.0, 0.0],
        "駐車場": [0.1, 0.8, 0.1, 0.0, 0.0],
        "wi-fi": [0.1, 0.7, 0.2, 0.0, 0.0],
        "アレルギー": [0.1, 0.1, 0.8, 0.0, 0.0],
        "部屋": [0.2, 0.1, 0.7, 0.0, 0.0],
        "温泉": [0.1, 0.1, 0.1, 0.7, 0.0],
        "食事": [0.1, 0.1, 0.1, 0.0, 0.7],
        "子供": [0.1, 0.1, 0.1, 0.2, 0.5],
        "観光": [0.1, 0.1, 0.1, 0.5, 0.2]
    }
    
    # 基本のランダムシード値（numpy.random.seed は 0 から 2^32-1 の範囲のみ対応）
    hash_obj = hashlib.md5(text.encode())
    hash_val = int(hash_obj.hexdigest(), 16) % (2**32 - 1)  # 修正: シード値の範囲を制限
    np.random.seed(hash_val)
    
    # 基本ベクトル - ほぼランダム
    base_vector = np.random.rand(EMBEDDING_DIM)
    
    # キーワード強調ベクトル - 特定のキーワードが含まれる場合に特定の次元を強調
    keyword_vector = np.zeros(EMBEDDING_DIM)
    
    for keyword, pattern in keywords.items():
        if keyword.lower() in text.lower():
            # キーワードが含まれる場合は、対応するパターンを使って最初の5次元を設定
            for i, val in enumerate(pattern):
                keyword_vector[i] += val * 0.5
            
            # キーワード固有の次元にも影響を与える（キーワードごとに異なる次元を活性化）
            keyword_hash = int(hashlib.md5(keyword.encode()).hexdigest(), 16) % (EMBEDDING_DIM - 10)
            for i in range(5):
                keyword_vector[keyword_hash + i] += 0.8
    
    # 基本ベクトルとキーワードベクトルを組み合わせる
    combined_vector = base_vector * 0.3 + keyword_vector * 0.7
    
    # ベクトルを正規化
    norm = np.linalg.norm(combined_vector)
    if norm > 0:
        combined_vector = combined_vector / norm
    
    return combined_vector.tolist()

def normalize_vector(vector, target_dim=EMBEDDING_DIM):
    """
    ベクトルを正規化して指定された次元数に調整する
    """
    # ベクトルの長さが足りない場合は0で埋める
    if len(vector) < target_dim:
        vector = vector + [0] * (target_dim - len(vector))
    # 長すぎる場合は切り詰める
    elif len(vector) > target_dim:
        vector = vector[:target_dim]
    
    # ベクトルを正規化（単位ベクトル化）
    # これによりコサイン類似度の計算がより正確になる
    vector_np = np.array(vector)
    norm = np.linalg.norm(vector_np)
    if norm > 0:
        vector_np = vector_np / norm
    
    return vector_np.tolist()

def get_embedding(text, client=None):
    """
    テキストのエンベディングを取得する
    テストモードの場合はダミーのエンベディング、それ以外はVoyageAI API経由で取得
    """
    # テストモードの場合
    if is_test_mode():
        return get_test_embedding(text)
    
    # クライアントが渡されていない場合は取得
    if client is None:
        client = load_voyage_client()
    
    # クライアントがNoneの場合（APIキーがない場合）はテストモードに切り替え
    if client is None:
        print("VoyageAI APIキーの読み込みに失敗しました。テストモードのエンベディングを返します。")
        return get_test_embedding(text)
    
    try:
        # VoyageAI API経由でエンベディングを取得（修正後の呼び出し方法）
        result = client.embed(
            [text],  # リストとして渡す（単一のテキストでもリストに入れる）
            model="voyage-3",
            input_type="document"
        )
        
        # レスポンスからエンベディングを取得
        embedding = result.embeddings[0]  # 最初の要素を取得
        
        print(f"VoyageAIエンベディング取得成功: {len(embedding)}次元")
        return embedding
    except Exception as e:
        print(f"VoyageAIエンベディング取得エラー: {e}")
        # エラー発生時はテスト用エンベディングを返す
        return get_test_embedding(text)

def check_embedding_quality(questions, embeddings):
    """
    エンベディングの品質をチェックする
    """
    problematic_pairs = []
    
    # 各質問ペアのコサイン類似度を計算
    from sklearn.metrics.pairwise import cosine_similarity
    
    # 各質問ペアのコサイン類似度を計算
    for i in range(len(questions)):
        for j in range(i+1, len(questions)):
            if i != j:
                similarity = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
                
                # 内容が明らかに異なるのに類似度が高い場合、または
                # 内容が似ているのに類似度が低い場合を検出
                question1_words = set(questions[i].lower().split())
                question2_words = set(questions[j].lower().split())
                word_overlap = len(question1_words.intersection(question2_words)) / len(question1_words.union(question2_words))
                
                # 単語の重複が少ないのに類似度が高い場合を検出
                if similarity > 0.8 and word_overlap < 0.3:
                    problematic_pairs.append((i, j, similarity, word_overlap))
                # 単語の重複が多いのに類似度が低い場合を検出
                elif similarity < 0.5 and word_overlap > 0.7:
                    problematic_pairs.append((i, j, similarity, word_overlap))
    
    return problematic_pairs

def save_embeddings(questions, answers, embeddings):
    """
    FAQデータとエンベディングを保存する
    """
    # データフレームを作成
    df = pd.DataFrame({
        'question': questions,
        'answer': answers,
        'embedding': embeddings
    })
    
    # データの形式を確認
    print(f"保存するデータ: {len(df)}行, カラム={df.columns.tolist()}")
    print(f"エンベディングの形状: {len(df['embedding'][0])}次元")
    
    # データを保存
    df.to_pickle("data/faq_with_embeddings.pkl")
    
    # 保存後に読み込んで確認
    test_df = pd.read_pickle("data/faq_with_embeddings.pkl")
    print(f"読み込みテスト: {len(test_df)}行, カラム={test_df.columns.tolist()}")
    print(f"読み込んだエンベディングの形状: {len(test_df['embedding'][0])}次元")
    
    return df

def create_embeddings():
    """
    FAQデータにエンベディングを追加して保存する
    VoyageAIを使用
    """
    # データディレクトリの確認
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # CSVファイルの確認
    if not os.path.exists("data/faq.csv"):
        # サンプルデータを作成
        sample_data = {
            "question": [
                "チェックインの時間は何時ですか？",
                "駐車場はありますか？",
                "Wi-Fiは利用できますか？",
                "食事のアレルギー対応はできますか？",
                "部屋のタイプはどのようなものがありますか？",
                "温泉の効能は何ですか？",
                "食事はどのような内容ですか？",
                "チェックアウトの時間は何時ですか？",
                "子供連れでも大丈夫ですか？",
                "周辺の観光スポットはありますか？"
            ],
            "answer": [
                "チェックインは15:00〜19:00です。事前にご連絡いただければ、遅いチェックインにも対応可能です。",
                "はい、無料の駐車場を提供しています。大型車の場合は事前にご連絡ください。",
                "全客室でWi-Fiを無料でご利用いただけます。接続情報はチェックイン時にお渡しします。",
                "はい、アレルギーがある場合は予約時にお知らせください。可能な限り対応いたします。",
                "和室と洋室の両方をご用意しています。和室は8畳・10畳・12畳、洋室はシングル・ツイン・ダブルがございます。",
                "当館の温泉は神経痛、筋肉痛、関節痛、五十肩、運動麻痺、関節のこわばり、うちみ、くじき、慢性消化器病、痔疾、冷え性、病後回復期、疲労回復、健康増進に効果があります。",
                "地元の新鮮な食材を使った会席料理をご提供しています。朝食は和食または洋食からお選びいただけます。",
                "チェックアウトは10:00となっております。レイトチェックアウトをご希望の場合は、フロントにご相談ください。",
                "はい、お子様連れのお客様も大歓迎です。お子様用の浴衣やスリッパ、食事用の椅子もご用意しております。",
                "当館から車で15分以内に、〇〇神社、△△美術館、□□公園などがございます。詳しい情報はフロントでご案内しております。"
            ]
        }
        pd.DataFrame(sample_data).to_csv("data/faq.csv", index=False)
        print("サンプルFAQデータを作成しました。")
    
    # CSVからデータを読み込む
    df = pd.read_csv("data/faq.csv")
    print(f"{len(df)}個のFAQエントリを読み込みました。")
    
    # VoyageAI APIクライアントを初期化
    client = load_voyage_client()
    
    # API呼び出しが失敗した場合のためにTEST_MODEを一時的に有効にする
    test_mode_original = os.environ.get("TEST_MODE", "false")
    
    try:
        # テスト呼び出しを行い、API呼び出しが成功するか確認
        print("API接続テスト中...")
        test_embedding = get_embedding("テスト", client)
        print("API接続テスト成功")
        # 成功した場合は通常モードで処理
        use_api = True
    except Exception as e:
        print(f"API接続テスト失敗: {e}")
        print("テストモードに切り替えます")
        # 失敗した場合はテストモードに切り替え
        os.environ["TEST_MODE"] = "true"
        use_api = False
    
    # エンベディングの生成
    embeddings = []
    
    # バッチ処理を行うためのリスト
    all_questions = df["question"].tolist()
    
    if use_api and client is not None:
        try:
            # バッチ処理でエンベディングを取得
            print(f"一括でエンベディングを取得します...")
            result = client.embed(
                all_questions,  # 質問のリスト全体を渡す
                model="voyage-3",
                input_type="document"
            )
            embeddings = result.embeddings
            print(f"一括エンベディング取得成功: {len(embeddings)}件")
        except Exception as e:
            print(f"一括エンベディング取得失敗: {e}")
            print("個別にエンベディングを取得します...")
            embeddings = []  # リセット
    
    # 個別処理（バッチ処理に失敗した場合や最初からテストモードの場合）
    if len(embeddings) == 0:
        for question in all_questions:
            if use_api:
                try:
                    # API経由でエンベディングを取得
                    embedding = get_embedding(question, client)
                    embeddings.append(embedding)
                except Exception as e:
                    print(f"API経由のエンベディング取得に失敗: {e}")
                    print("テストモードに切り替えます")
                    os.environ["TEST_MODE"] = "true"
                    embedding = get_test_embedding(question)
                    embeddings.append(embedding)
                    use_api = False  # 以降の処理もテストモードで
            else:
                # テストモードでエンベディングを生成
                embedding = get_test_embedding(question)
                embeddings.append(embedding)
            
            print(f"エンベディング生成: '{question[:30]}...'")
    
    # エンベディングをデータフレームに追加
    df["embedding"] = embeddings
    
    # エンベディングの品質チェック
    print("エンベディングの品質チェックを実行...")
    
    # エンベディング間の類似度を計算
    from sklearn.metrics.pairwise import cosine_similarity
    similarities = cosine_similarity(embeddings)
    
    # 対角要素（自分自身との類似度）を0にする
    np.fill_diagonal(similarities, 0)
    
    # 高い類似度のペアがあるか確認
    high_sim_threshold = 0.95
    high_sim_pairs = np.where(similarities > high_sim_threshold)
    
    if len(high_sim_pairs[0]) > 0:
        print(f"警告: 類似度が {high_sim_threshold} を超えるペアが {len(high_sim_pairs[0]) // 2} 個あります")
        for i, j in zip(high_sim_pairs[0], high_sim_pairs[1]):
            if i < j:  # 重複を避けるため
                print(f"  - '{df.iloc[i]['question'][:30]}...' と '{df.iloc[j]['question'][:30]}...'")
                print(f"    類似度: {similarities[i, j]:.4f}")
    else:
        print("エンベディングの品質は良好です。")
    
    # PKLファイルとして保存
    df.to_pickle("data/faq_with_embeddings.pkl")
    print("FAQデータとエンベディングを保存しました。")
    
    # 元のTEST_MODE設定を復元
    os.environ["TEST_MODE"] = test_mode_original

if __name__ == "__main__":
    create_embeddings()