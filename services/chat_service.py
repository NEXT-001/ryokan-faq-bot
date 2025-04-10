import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
import anthropic
from config.settings import load_api_key, is_test_mode
from services.line_bot_service import send_line_message

# グローバル変数
client = None
# 類似度のしきい値（これを下回る場合はLINE通知）
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.6"))

def get_embeddings(text):
    """
    テキストのエンベディングを取得する
    """
    # テストモードの場合はダミーのエンベディングを返す
    if is_test_mode():
        import hashlib
        # テキストのハッシュ値を使って擬似的に一貫性のあるベクトルを生成
        hash_obj = hashlib.md5(text.encode())
        hash_val = int(hash_obj.hexdigest(), 16)
        np.random.seed(hash_val)
        return np.random.rand(1536).tolist()  # 1536次元のランダムなベクトル
    
    # 本番モード
    try:
        global client
        if client is None:
            client = load_api_key()
            
        if client is None:  # APIキーがロードできなかった場合
            # テストモードに切り替えてダミーのエンベディングを返す
            os.environ["TEST_MODE"] = "true"
            return get_embeddings(text)
            
        response = client.embeddings.create(
            model="claude-3-sonnet-20240229",
            input=text
        )
        return response.embedding
    except Exception as e:
        print(f"エンベディング取得エラー: {e}")
        # エラーが発生した場合はダミーのエンベディングを返す
        return [0] * 1536  # 標準的なサイズ

def get_response(user_input):
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
            "温泉": "TEST当館の温泉は神経痛、筋肉痛、関節痛、五十肩、運動麻痺、関節のこわばり、うちみ、くじき、慢性消化器病、痔疾、冷え性、病後回復期、疲労回復、健康増進に効果があります。",
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
        
        # ユーザー入力のエンベディングを取得
        user_embedding = get_embeddings(user_input)
        
        # コサイン類似度の計算
        similarities = cosine_similarity([user_embedding], df["embedding"].tolist())
        
        # 最も類似度の高い質問のインデックスを取得
        best_idx = np.argmax(similarities)
        similarity_score = similarities[0][best_idx]
        
        # 対応する回答を取得
        answer = df.iloc[best_idx]["answer"]
        
        # 類似度スコアが低すぎる場合
        if similarity_score < SIMILARITY_THRESHOLD:
            # LINE通知を送信
            send_line_message(
                question=user_input,
                answer=answer,
                similarity_score=similarity_score
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
            similarity_score=0.0
        )
        return error_message, 0, 0