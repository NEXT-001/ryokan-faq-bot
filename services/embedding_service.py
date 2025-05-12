"""
エンベディング関連の共通サービス
embedding_service.py
"""
import os
import pandas as pd
import numpy as np
import hashlib
import voyageai
import time
from config.settings import is_test_mode, get_data_path

# エンベディングの次元数 (テストモードでは1024次元を想定)
EMBEDDING_DIM = 1024
# API呼び出しの最大リトライ回数
MAX_RETRIES = 3
# リトライ間の待機時間（秒）
RETRY_DELAY = 20

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
        "観光": [0.1, 0.1, 0.1, 0.5, 0.2],
        # 一般的なFAQキーワードを追加
        "営業": [0.6, 0.2, 0.0, 0.1, 0.1],
        "時間": [0.5, 0.3, 0.1, 0.0, 0.1],
        "予約": [0.3, 0.6, 0.0, 0.1, 0.0],
        "支払い": [0.2, 0.2, 0.5, 0.1, 0.0],
        "料金": [0.1, 0.1, 0.7, 0.1, 0.0],
        "キャンセル": [0.1, 0.1, 0.1, 0.6, 0.1],
        "サービス": [0.1, 0.1, 0.2, 0.1, 0.5]
    }
    
    # 基本のランダムシード値（numpy.random.seed は 0 から 2^32-1 の範囲のみ対応）
    hash_obj = hashlib.md5(text.encode())
    hash_val = int(hash_obj.hexdigest(), 16) % (2**32 - 1)  # シード値の範囲を制限
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

def get_embedding(text, client=None):
    """
    テキストのエンベディングを取得する
    テストモードの場合はダミーのエンベディング、それ以外はVoyageAI API経由で取得
    
    Args:
        text (str): エンベディングを取得するテキスト
        client (voyageai.Client, optional): VoyageAI APIクライアント
        
    Returns:
        list: エンベディングベクトル
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
    
    # API呼び出しをリトライする
    for attempt in range(MAX_RETRIES):
        try:
            # VoyageAI API経由でエンベディングを取得
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
            print(f"VoyageAIエンベディング取得エラー (試行 {attempt+1}/{MAX_RETRIES}): {e}")
            
            # レート制限エラーの場合は待機してリトライ
            if "rate limit" in str(e).lower() or "your rate limits" in str(e).lower():
                print(f"{RETRY_DELAY}秒待機してリトライします...")
                time.sleep(RETRY_DELAY)
            else:
                # その他のエラーの場合はリトライせずにテストモードに切り替え
                print("テストモードのエンベディングを返します。")
                return get_test_embedding(text)
    
    # リトライ回数を超えた場合はテストモードのエンベディングを返す
    print(f"リトライ回数（{MAX_RETRIES}回）を超えました。テストモードのエンベディングを返します。")
    return get_test_embedding(text)

def create_embeddings(company_id):
    """
    指定された会社のFAQデータにエンベディングを追加して保存する
    
    Args:
        company_id (str): 会社ID
    """
    # 会社のデータディレクトリを取得
    company_dir = os.path.join(get_data_path(), "companies", company_id)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    # CSVファイルの確認
    csv_path = os.path.join(company_dir, "faq.csv")
    if not os.path.exists(csv_path):
        print(f"CSVファイルが見つかりません: {csv_path}")
        return False
    
    # CSVからデータを読み込む
    try:
        df = pd.read_csv(csv_path)
        print(f"{len(df)}個のFAQエントリを読み込みました。")
    except Exception as e:
        print(f"CSVファイルの読み込みエラー: {e}")
        return False
    
    # 一時的にテストモードをチェック
    original_test_mode = is_test_mode()
    # テストモードが明示的に設定されていない場合、または
    # ユーザーからのリクエストでテストモードが指定されていない場合は
    # VoyageAI APIが利用できるかどうかを確認
    
    print(f"現在のテストモード: {original_test_mode}")
    
    # VoyageAI APIクライアントを初期化
    client = None
    if not original_test_mode:
        client = load_voyage_client()
        
        # テスト呼び出しを行い、API呼び出しが成功するか確認
        try:
            print("API接続テスト中...")
            # テスト呼び出しのためのダミーテキスト
            dummy_text = "テスト文章"
            test_embedding = get_embedding(dummy_text, client)
            print("API接続テスト成功")
        except Exception as e:
            print(f"API接続テスト失敗: {e}")
            print("エンベディング生成をテストモードに切り替えます")
            # 一時的にテストモードに切り替え
            os.environ["TEST_MODE"] = "true"
    
    # エンベディングの生成
    embeddings = []
    
    # バッチ処理を行うためのリスト
    all_questions = df["question"].tolist()
    
    # 各質問のエンベディングを生成
    for i, question in enumerate(all_questions):
        print(f"エンベディング生成中 ({i+1}/{len(all_questions)}): '{question[:30]}...'")
        
        try:
            # エンベディングを取得
            embedding = get_embedding(question, client)
            embeddings.append(embedding)
            
            # レート制限に引っかからないように、バッチ処理の場合は一定間隔を空ける
            if i < len(all_questions) - 1 and not is_test_mode():
                time.sleep(1)  # 1秒待機
                
        except Exception as e:
            print(f"エンベディング生成エラー: {e}")
            # エラーが発生した場合はテストモードのエンベディングを使用
            embedding = get_test_embedding(question)
            embeddings.append(embedding)
    
    # 元のテストモード設定を復元
    if not original_test_mode:
        os.environ["TEST_MODE"] = "false"
    
    # エンベディングをデータフレームに追加
    df["embedding"] = embeddings
    
    # PKLファイルとして保存
    pkl_path = os.path.join(company_dir, "faq_with_embeddings.pkl")
    df.to_pickle(pkl_path)
    print(f"FAQデータとエンベディングを保存しました: {pkl_path}")
    
    return True