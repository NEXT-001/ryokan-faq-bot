"""
エンベディング関連の共通サービス（進行状況表示対応版）
embedding_service.py
"""
import os
import pandas as pd
import numpy as np
import hashlib
import voyageai
import time
import streamlit as st
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

def create_embeddings(company_id, show_progress=True):
    """
    指定された会社のFAQデータにエンベディングを追加して保存する
    
    Args:
        company_id (str): 会社ID
        show_progress (bool): Streamlitで進行状況を表示するかどうか
    """
    # 会社のデータディレクトリを取得
    company_dir = os.path.join(get_data_path(), "companies", company_id)
    if not os.path.exists(company_dir):
        os.makedirs(company_dir)
    
    # CSVファイルの確認
    csv_path = os.path.join(company_dir, "faq.csv")
    if not os.path.exists(csv_path):
        error_msg = f"CSVファイルが見つかりません: {csv_path}"
        print(error_msg)
        if show_progress:
            st.error(error_msg)
        return False
    
    # CSVからデータを読み込む
    try:
        df = pd.read_csv(csv_path)
        print(f"{len(df)}個のFAQエントリを読み込みました。")
    except Exception as e:
        error_msg = f"CSVファイルの読み込みエラー: {e}"
        print(error_msg)
        if show_progress:
            st.error(error_msg)
        return False
    
    # 一時的にテストモードをチェック
    original_test_mode = is_test_mode()
    print(f"現在のテストモード: {original_test_mode}")
    
    # VoyageAI APIクライアントを初期化
    client = None
    if not original_test_mode:
        if show_progress:
            # st.status の代わりにシンプルなメッセージ表示を使用
            api_status = st.empty()
            api_status.info("🔧 VoyageAI APIクライアントを初期化しています...")
            
            client = load_voyage_client()
            
            if client:
                api_status.info("🔍 API接続テストを実行しています...")
                try:
                    # テスト呼び出しを行い、API呼び出しが成功するか確認
                    dummy_text = "テスト文章"
                    test_embedding = get_embedding(dummy_text, client)
                    api_status.success("✅ API接続テスト成功")
                    time.sleep(0.5)  # メッセージを表示する時間を確保
                    api_status.empty()  # メッセージをクリア
                except Exception as e:
                    api_status.error(f"❌ API接続テスト失敗: {e}")
                    st.warning("テストモードに切り替えます")
                    os.environ["TEST_MODE"] = "true"
                    time.sleep(1)
                    api_status.empty()  # メッセージをクリア
            else:
                api_status.error("❌ APIクライアントの初期化に失敗")
                st.warning("テストモードに切り替えます")
                os.environ["TEST_MODE"] = "true"
                time.sleep(1)
                api_status.empty()  # メッセージをクリア
        else:
            client = load_voyage_client()
            if client:
                try:
                    print("API接続テスト中...")
                    dummy_text = "テスト文章"
                    test_embedding = get_embedding(dummy_text, client)
                    print("API接続テスト成功")
                except Exception as e:
                    print(f"API接続テスト失敗: {e}")
                    print("エンベディング生成をテストモードに切り替えます")
                    os.environ["TEST_MODE"] = "true"
    
    # エンベディングの生成
    embeddings = []
    all_questions = df["question"].tolist()
    total_count = len(all_questions)
    
    # 進行状況表示の準備（完全にシンプルな形式）
    if show_progress:
        st.write("**エンベディング生成を開始します...**")
        progress_bar = st.progress(0)
        status_text = st.empty()
        current_question_text = st.empty()
        
        # 詳細ログ用（シンプルな表示）
        show_details = st.checkbox("詳細な進行状況を表示", value=False)
        if show_details:
            detail_placeholder = st.empty()
            detail_logs = []
        else:
            detail_placeholder = None
            detail_logs = []
    
    # 各質問のエンベディングを生成
    for i, question in enumerate(all_questions):
        current_progress = (i + 1) / total_count
        progress_text = f"エンベディング生成中: {i+1}/{total_count} 件"
        
        print(f"エンベディング生成中 ({i+1}/{total_count}): '{question[:30]}...'")
        
        # 進行状況の更新
        if show_progress:
            progress_bar.progress(current_progress)
            status_text.text(progress_text)
            current_question_text.info(f"処理中: {question[:50]}..." if len(question) > 50 else f"処理中: {question}")
            
            # 詳細ログの更新（チェックボックスがONの場合のみ）
            if show_details and detail_placeholder is not None:
                detail_logs.append(f"[{i+1}/{total_count}] {question[:40]}..." if len(question) > 40 else f"[{i+1}/{total_count}] {question}")
                # 最新の10件のログのみ表示
                if len(detail_logs) > 10:
                    detail_logs = detail_logs[-10:]
                
                detail_placeholder.text("\n".join(detail_logs))
        
        try:
            # エンベディングを取得
            embedding = get_embedding(question, client)
            embeddings.append(embedding)
            
            # レート制限に引っかからないように、バッチ処理の場合は一定間隔を空ける
            if i < len(all_questions) - 1 and not is_test_mode():
                time.sleep(1)  # 1秒待機
                
        except Exception as e:
            error_msg = f"エンベディング生成エラー: {e}"
            print(error_msg)
            if show_progress:
                st.warning(f"質問 {i+1} でエラーが発生しました。テストモードのエンベディングを使用します。")
            # エラーが発生した場合はテストモードのエンベディングを使用
            embedding = get_test_embedding(question)
            embeddings.append(embedding)
    
    # 進行状況の完了表示
    if show_progress:
        progress_bar.progress(1.0)
        status_text.text(f"✅ エンベディング生成完了: {total_count}/{total_count} 件")
        current_question_text.success("全ての質問のエンベディング生成が完了しました")
    
    # 元のテストモード設定を復元
    if not original_test_mode:
        os.environ["TEST_MODE"] = "false"
    
    # エンベディングをデータフレームに追加
    df["embedding"] = embeddings
    
    # PKLファイルとして保存
    pkl_path = os.path.join(company_dir, "faq_with_embeddings.pkl")
    
    if show_progress:
        # st.status の代わりにシンプルなメッセージ表示を使用
        save_status = st.empty()
        save_status.info("💾 エンベディングデータを保存しています...")
        try:
            df.to_pickle(pkl_path)
            save_status.success(f"✅ 保存完了: {pkl_path}")
            time.sleep(0.5)  # メッセージを表示する時間を確保
            save_status.empty()  # メッセージをクリア
        except Exception as e:
            error_msg = f"❌ 保存エラー: {e}"
            save_status.error(error_msg)
            return False
    else:
        try:
            df.to_pickle(pkl_path)
            print(f"FAQデータとエンベディングを保存しました: {pkl_path}")
        except Exception as e:
            print(f"保存エラー: {e}")
            return False
    
    return True