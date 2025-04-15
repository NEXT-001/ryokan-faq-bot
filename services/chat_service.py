"""
チャットサービス - ユーザーの質問に対する回答を提供
"""
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
import voyageai
from config.settings import is_test_mode
from services.line_service import send_line_message  # 修正: 統合されたline_serviceから関数をインポート

# グローバル変数
voyage_client = None
# 類似度のしきい値（これを下回る場合はLINE通知）
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.6"))

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

def get_embeddings(text):
    """
    テキストのエンベディングを取得する
    """
    # テストモードの場合はダミーのエンベディングを返す
    if is_test_mode():
        import hashlib
        # テキストのハッシュ値を使って擬似的に一貫性のあるベクトルを生成
        hash_obj = hashlib.md5(text.encode())
        hash_val = int(hash_obj.hexdigest(), 16) % (2**32 - 1)  # 範囲を制限
        np.random.seed(hash_val)
        vector = np.random.rand(1024)  # VoyageAIのvoyage-3は1024次元
        # ベクトルを正規化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()
    
    # 本番モード - VoyageAIを使用
    try:
        global voyage_client
        if voyage_client is None:
            voyage_client = load_voyage_client()
            
        if voyage_client is None:
            print("VoyageAI APIキーの読み込みに失敗しました。テストモードに切り替えます。")
            os.environ["TEST_MODE"] = "true"
            return get_embeddings(text)
        
        # VoyageAIのエンベディング取得（修正後の正しい呼び出し方法）
        result = voyage_client.embed(
            [text],  # リストとして渡す
            model="voyage-3",
            input_type="document"
        )
        
        # 成功時のメッセージ
        embedding = result.embeddings[0]  # 最初の要素を取得
        print(f"VoyageAIエンベディング取得成功: {len(embedding)}次元")
        return embedding
        
    except Exception as e:
        print(f"VoyageAIエンベディング取得エラー: {e}")
        print("エラー詳細:", repr(e))
        
        # エラーが発生した場合はテストモードに切り替える
        print("テストモードに切り替えます")
        os.environ["TEST_MODE"] = "true"
        return get_embeddings(text)
    
def get_response(user_input, room_number=""):
    """
    ユーザー入力に対する最適な回答を取得する
    """
    # テストモードの場合
    if is_test_mode():
        print("テストモードで実行中")
        # テスト用の回答セット
        test_responses = {
            "チェックイン": "チェックインは15:00〜19:00です。事前にご連絡いただければ、遅いチェックインにも対応可能です。",
            "チェックアウト": "チェックアウトは10:00となっております。レイトチェックアウトをご希望の場合は、フロントにご相談ください。",
            "駐車場": "はい、無料の駐車場を提供しています。大型車の場合は事前にご連絡ください。",
            "wi-fi": "全客室でWi-Fiを無料でご利用いただけます。接続情報はチェックイン時にお渡しします。",
            "アレルギー": "はい、アレルギーがある場合は予約時にお知らせください。可能な限り対応いたします。",
            "部屋": "和室と洋室の両方をご用意しています。和室は8畳・10畳・12畳、洋室はシングル・ツイン・ダブルがございます。",
            "温泉": "当館の温泉は神経痛、筋肉痛、関節痛、五十肩、運動麻痺、関節のこわばり、うちみ、くじき、慢性消化器病、痔疾、冷え性、病後回復期、疲労回復、健康増進に効果があります。",
            "食事": "地元の新鮮な食材を使った会席料理をご提供しています。朝食は和食または洋食からお選びいただけます。",
            "子供": "はい、お子様連れのお客様も大歓迎です。お子様用の浴衣やスリッパ、食事用の椅子もご用意しております。",
            "観光": "当館から車で15分以内に、○○神社、△△美術館、□□公園などがございます。詳しい情報はフロントでご案内しております。"
        }
        
        # 簡易的なキーワードマッチング
        for keyword, response in test_responses.items():
            if keyword in user_input:
                return response, len(user_input.split()), len(response.split())
        
        # デフォルトの回答
        default_response = "申し訳ございません。その質問については担当者に確認する必要があります。しばらくお待ちいただけますでしょうか。"
        
        # テストモードでもLINE通知をシミュレート
        print("テストモード: LINEメッセージをシミュレートします")
        # 実際には送信しない
        
        return default_response, len(user_input.split()), len(default_response.split())
    
    # 本番モード
    # FAQデータの読み込み (存在確認)
    if not os.path.exists("data/faq_with_embeddings.pkl"):
        return "申し訳ありません。FAQデータがまだ準備されていません。", 0, 0
    
    try:
        df = pd.read_pickle("data/faq_with_embeddings.pkl")
        
        # データフレームの内容を確認
        print(f"FAQ データ: {len(df)} 件")
        print(f"FAQ データのカラム: {df.columns.tolist()}")
        
        # ユーザー入力のエンベディングを取得
        user_embedding = get_embeddings(user_input)
        
        # コサイン類似度の計算
        similarities = cosine_similarity([user_embedding], df["embedding"].tolist())
        
        # 類似度の上位5件を表示
        top_indices = np.argsort(similarities[0])[::-1][:5]
        print("\n上位5件の類似質問:")
        for idx in top_indices:
            print(f"類似度: {similarities[0][idx]:.4f}, 質問: {df.iloc[idx]['question'][:50]}...")
        
        # 最も類似度の高い質問のインデックスを取得
        best_idx = np.argmax(similarities)
        similarity_score = similarities[0][best_idx]
        
        print(f"\n最も類似度の高い質問: {df.iloc[best_idx]['question']}")
        print(f"類似度スコア: {similarity_score:.4f}")
        
        # 対応する回答を取得
        answer = df.iloc[best_idx]["answer"]
        
        # 類似度スコアが低すぎる場合
        if similarity_score < SIMILARITY_THRESHOLD:
            # LINE通知を送信
            send_line_message(
                question=user_input,
                answer=answer,
                similarity_score=similarity_score,
                room_number=room_number  # 部屋番号の情報を追加
            )
        
        # ユーザーへの回答
        if similarity_score < 0.4:  # 非常に低い類似度の場合
            answer = "申し訳ございません。その質問については担当者に確認する必要があります。しばらくお待ちいただけますでしょうか。"
        else:  # 中程度の類似度の場合は回答を表示するが、不確かさを伝える
            answer = f"{answer}\n\n※この回答に不明点がある場合は、直接スタッフにお問い合わせください。"
    
        return answer, len(user_input.split()), len(answer.split())
    
    except Exception as e:
        print(f"回答取得エラー: {e}")
        error_message = f"エラーが発生しました。スタッフにお問い合わせください。"
        # エラー発生時もLINE通知
        send_line_message(
            question=user_input,
            answer=f"エラー: {str(e)}",
            similarity_score=0.0,
            room_number=room_number  # 部屋番号の情報を追加
        )
        return error_message, 0, 0

# フォームからの入力を処理する関数例
def process_form_input(request):
    """
    Webフォームからの入力を処理する関数例
    実際の実装はフレームワークによって異なります
    """
    user_input = request.form.get('user_question', '')
    room_number = request.form.get('room_number', '')  # 部屋番号の入力フィールドを追加
    
    # 入力検証
    if not user_input:
        return "質問を入力してください。"
    
    # 部屋番号が未入力の場合のデフォルト処理（オプション）
    # room_number = room_number or "不明"
    
    # 回答を取得
    answer, q_words, a_words = get_response(user_input, room_number)
    
    return answer