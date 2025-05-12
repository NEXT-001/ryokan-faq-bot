"""
チャットサービス - ユーザーの質問に対する回答を提供
chat_service.py
"""
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
import streamlit as st
from config.settings import is_test_mode, get_data_path
from services.embedding_service import get_embedding
from services.line_service import send_line_message  # LINE送信機能をインポート

# 類似度のしきい値（これを下回る場合は不明確な回答となる）
SIMILARITY_THRESHOLD = 0.6
# 非常に低い類似度のしきい値（この場合はLINE通知を送る）
LOW_SIMILARITY_THRESHOLD = 0.4

def get_response(user_input, company_id=None, user_info=""):
    """
    ユーザー入力に対する最適な回答を取得する
    
    Args:
        user_input (str): ユーザーからの質問
        company_id (str, optional): 会社ID（指定がない場合はデモ企業）
        user_info (str, optional): ユーザー情報（お部屋番号など）
        
    Returns:
        tuple: (回答, 入力トークン数, 出力トークン数)
    """
    # 会社IDが指定されていない場合はデモ企業を使用
    if not company_id:
        company_id = "demo-company"
    
    # テストモードの場合
    if is_test_mode():
        print(f"テストモードで実行中 - 会社ID: {company_id}")
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
        print(f"テストモード: LINEメッセージをシミュレートします - ユーザー情報: {user_info}, 質問: {user_input}")
        
        return default_response, len(user_input.split()), len(default_response.split())
    
    # 本番モード
    # 会社のFAQデータパスを取得
    company_path = os.path.join(get_data_path(), "companies", company_id)
    faq_path = os.path.join(company_path, "faq_with_embeddings.pkl")
    
    # FAQデータの存在確認
    if not os.path.exists(faq_path):
        error_msg = f"申し訳ありません。企業ID「{company_id}」のFAQデータが見つかりません。"
        return error_msg, 0, 0
    
    try:
        # FAQデータを読み込む
        df = pd.read_pickle(faq_path)
        
        # データフレームの内容を確認
        print(f"FAQ データ: {len(df)} 件")
        
        # ユーザー入力のエンベディングを取得
        user_embedding = get_embedding(user_input)
        
        # コサイン類似度の計算
        embeddings_list = df["embedding"].tolist()
        similarities = cosine_similarity([user_embedding], embeddings_list)
        
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
            # 非常に低い類似度の場合
            if similarity_score < LOW_SIMILARITY_THRESHOLD:
                # LINE通知を送信
                print(f"類似度が低いため、LINE通知を送信します: {similarity_score:.4f}")
                send_line_message(
                    question=user_input,
                    answer="適切な回答が見つかりませんでした。",
                    similarity_score=similarity_score,
                    room_number=user_info
                )
                
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
            room_number=user_info
        )
        
        return error_message, 0, 0