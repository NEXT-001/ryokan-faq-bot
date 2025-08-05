"""
チャットサービス - ユーザーの質問に対する回答を提供
chat_service.py
"""
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import os
import streamlit as st
import urllib.parse
import openai
import re
from dotenv import load_dotenv
from config.unified_config import UnifiedConfig
from services.embedding_service import get_embedding
from services.line_service import send_line_message  # LINE送信機能をインポート
from services.faq_migration import get_faq_data_from_db, init_faq_migration
from services.tourism_service import detect_language, generate_tourism_response_by_city
from services.translation_service import TranslationService

# 環境変数読み込み
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 類似度のしきい値（これを下回る場合は不明確な回答となる）
SIMILARITY_THRESHOLD = 0.6
# 非常に低い類似度のしきい値（この場合はLINE通知を送る）
LOW_SIMILARITY_THRESHOLD = 0.4

def add_bing_links_to_brackets(text):
    """
    FAQ回答内の[単語]形式の文字列にBing検索リンクを追加
    例: [金閣寺] → [金閣寺](https://www.bing.com/search?q=金閣寺)
    """
    def replace_bracket_with_link(match):
        word = match.group(1)  # [と]の間の文字を取得
        encoded_word = urllib.parse.quote(word)
        bing_url = f"https://www.bing.com/search?q={encoded_word}"
        return f"[{word}]({bing_url})"
    
    # [文字列]のパターンをMarkdownリンクに変換
    pattern = r'\[([^\[\]]+)\]'
    result = re.sub(pattern, replace_bracket_with_link, text)
    
    return result

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
    if UnifiedConfig.is_test_mode():
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
        default_response = (
            "申し訳ございません。その質問については担当者に確認する必要があります。"
            "しばらくお待ちいただけますでしょうか。\n\n"
            "I apologize, but I need to check with our staff regarding that question. "
            "Could you please wait a moment?"
        )
        # テストモードでもLINE通知をシミュレート
        print(f"テストモード: LINEメッセージをシミュレートします - ユーザー情報: {user_info}, 質問: {user_input}")
        
        return default_response, len(user_input.split()), len(default_response.split())
    
    # 本番モード - DBからFAQデータを取得
    try:
        # FAQマイグレーション用テーブルの初期化
        init_faq_migration()
        
        # DBからFAQデータを取得
        faq_data = get_faq_data_from_db(company_id)
        
        if not faq_data:
            # DBにデータがない場合は、従来のPKLファイルから読み込みを試行
            company_path = os.path.join(UnifiedConfig.get_data_path(), "companies", company_id)
            faq_path = os.path.join(company_path, "faq_with_embeddings.pkl")
            
            if os.path.exists(faq_path):
                # PKLファイルが存在する場合は読み込み（後方互換性）
                df = pd.read_pickle(faq_path)
                print(f"PKL FAQ データ（後方互換）: {len(df)} 件")
                
                # データをDBに移行
                from services.faq_migration import migrate_company_faq_data
                if migrate_company_faq_data(company_id, show_progress=False):
                    print(f"PKLデータをDBに移行しました: {company_id}")
                    # 移行後にDBからデータを再取得
                    faq_data = get_faq_data_from_db(company_id)
                else:
                    # 移行に失敗した場合はPKLデータをそのまま使用
                    faq_data = df.to_dict('records')
                    for i, row in enumerate(faq_data):
                        row['id'] = i + 1
            else:
                error_msg = f"申し訳ありません。企業ID「{company_id}」のFAQデータが見つかりません。"
                return error_msg, 0, 0
        
        print(f"FAQ データ: {len(faq_data)} 件")
        
        # ユーザー入力のエンベディングを取得
        user_embedding = get_embedding(user_input)
        
        # エンベディングが存在するFAQのみを抽出
        valid_faqs = [faq for faq in faq_data if faq['embedding'] is not None]
        
        if not valid_faqs:
            error_msg = f"申し訳ありません。企業ID「{company_id}」のエンベディングデータが見つかりません。"
            return error_msg, 0, 0
        
        # コサイン類似度の計算
        embeddings_list = [faq['embedding'] for faq in valid_faqs]
        similarities = cosine_similarity([user_embedding], embeddings_list)
        
        # 類似度の上位5件を表示
        top_indices = np.argsort(similarities[0])[::-1][:5]
        print("\n上位5件の類似質問:")
        for idx in top_indices:
            if idx < len(valid_faqs):
                print(f"類似度: {similarities[0][idx]:.4f}, 質問: {valid_faqs[idx]['question'][:50]}...")
        
        # 最も類似度の高い質問のインデックスを取得
        best_idx = np.argmax(similarities)
        similarity_score = similarities[0][best_idx]
        
        print(f"\n最も類似度の高い質問: {valid_faqs[best_idx]['question']}")
        print(f"類似度スコア: {similarity_score:.4f}")
        
        # 対応する回答を取得
        answer = valid_faqs[best_idx]["answer"]
        
        # FAQ回答内の[単語]にBingリンクを追加
        answer = add_bing_links_to_brackets(answer)
        
        user_lang = detect_language(user_input)
        print(f"質問した言語: {user_lang}")
        
        # 外国語の質問の場合は回答を翻訳
        if user_lang != 'ja':
            translation_service = TranslationService()
            # 詳細情報リンクは日本語のまま保持し、説明文のみ翻訳
            translated_answer = translation_service.translate_text(answer, user_lang, 'ja')
            # リンク部分は日本語のまま保持するため、元の回答と翻訳された回答を適切に結合
            answer = _preserve_japanese_links_in_translation(answer, translated_answer)
            print(f"回答を{user_lang}に翻訳しました")
        
        # 類似度スコアが低すぎる場合
        if similarity_score < SIMILARITY_THRESHOLD:
            # # 非常に低い類似度の場合
            # LINE通知を送信
            print(f"類似度が低いため、LINE通知を送信します: {similarity_score:.4f}")
            send_line_message(
                question=user_input,
                answer="適切な回答が見つかりませんでした。\n\n申し訳ございません。その質問については担当者に確認する必要があります。",
                similarity_score=similarity_score,
                room_number=user_info,
                company_id=company_id
            )
            
            # 観光・グルメ関連質問の場合、ぐるなび検索を提案
            if _is_restaurant_query(user_input):
                answer = _generate_gnavi_response(user_input, user_lang)
            else:
                # エラーメッセージも言語に応じて翻訳
                if user_lang == 'en':
                    answer = "I apologize, but I need to check with our staff regarding that question. Could you please wait a moment?"
                elif user_lang == 'ko':
                    answer = "죄송합니다. 해당 질문에 대해서는 담당자에게 확인이 필요합니다. 잠시만 기다려 주시겠어요?"
                elif user_lang == 'zh':
                    answer = "很抱歉，关于这个问题需要与工作人员确认。请稍等片刻。"
                else:
                    answer = (
                        "申し訳ございません。その質問については担当者に確認する必要があります。"
                        "しばらくお待ちいただけますでしょうか。"
                    )

        return answer, len(user_input.split()), len(answer.split())
    
    except Exception as e:
        print(f"回答取得エラー: {e}")
        error_message = f"エラーが発生しました。スタッフにお問い合わせください。"
        
        # エラー発生時もLINE通知
        try:
            send_line_message(
                question=user_input,
                answer=f"エラー: {str(e)}",
                similarity_score=0.0,
                room_number=user_info,
                company_id=company_id
            )
        except Exception as line_error:
            print(f"LINE通知エラー: {line_error}")
        
        return error_message, 0, 0


def _preserve_japanese_links_in_translation(original_text: str, translated_text: str) -> str:
    """
    翻訳された回答の中で、日本語の詳細情報リンクを保持する
    
    Args:
        original_text: 元の日本語回答
        translated_text: 翻訳された回答
        
    Returns:
        str: 日本語リンクが保持された翻訳済み回答
    """
    import re
    
    # 詳細情報リンクのパターンを抽出
    link_patterns = [
        r'📍\s*詳細情報[：:][^】]*',
        r'🗾\s*観光情報[（\(][^）\)]*[）\)]',
        r'🗺️\s*地図情報[（\(][^）\)]*[）\)]',
        r'📖\s*[^（\(]*[（\(][^）\)]*[）\)]',
        r'🍽️\s*[^（\(]*[（\(][^）\)]*[）\)]'
    ]
    
    # 元のテキストから日本語リンクを抽出
    japanese_links = []
    for pattern in link_patterns:
        matches = re.findall(pattern, original_text)
        japanese_links.extend(matches)
    
    # 翻訳されたテキストの末尾に日本語の詳細情報を追加
    if japanese_links and '📍' not in translated_text:
        translated_text += "\n\n📍 詳細情報:\n"
        for link in japanese_links:
            if link not in translated_text:
                translated_text += f"• {link}\n"
    
    return translated_text


def _is_restaurant_query(query: str) -> bool:
    """
    質問がレストラン・グルメ関連かを判定
    """
    restaurant_keywords = [
        "レストラン", "食事", "グルメ", "ランチ", "ディナー", "飲食", "料理", 
        "カフェ", "居酒屋", "食べ物", "美味しい", "おすすめ", "食べる",
        "restaurant", "food", "eat", "dinner", "lunch", "cafe", "gourmet",
        "맛집", "음식", "식당", "레스토랑", "카페", "먹다",
        "餐厅", "美食", "吃", "料理", "咖啡厅"
    ]
    return any(keyword in query.lower() for keyword in restaurant_keywords)


def _generate_gnavi_response(query: str, user_lang: str) -> str:
    """
    ぐるなび検索案内の多言語対応レスポンスを生成
    """
    # デフォルトの案内文
    default_responses = {
        "ja": "周辺のおすすめレストランはこちらです。以下のリンクをご参照ください。",
        "en": "Here are recommended restaurants in the area. Please refer to the link below.",
        "ko": "주변 추천 레스토랑은 여기 있습니다. 아래 링크를 참조해주세요.",
        "zh": "这里是周边推荐餐厅。请参考以下链接。"
    }
    
    base_text = default_responses.get(user_lang, default_responses["ja"])
    
    # OpenAI APIが利用可能な場合は翻訳を試行
    if openai.api_key:
        try:
            language_instruction = {
                "ja": "次の文章を日本語で自然に出力してください。",
                "en": "Please output the following sentence naturally in English.",
                "ko": "다음 문장을 자연스러운 한국어로 출력해주세요.",
                "zh": "请用自然的中文输出以下句子。"
            }.get(user_lang, "Please output the following sentence naturally in English.")
            
            prompt = f"{language_instruction}\n\n{base_text}"
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100
            )
            base_text = response['choices'][0]['message']['content']
        except Exception as e:
            print(f"翻訳エラー: {e}")
    
    # ぐるなび検索URL生成（クエリから場所を抽出または既定値を使用）
    location_param = "レストラン"
    gnavi_url = f"https://www.gnavi.co.jp/search/k/?word={urllib.parse.quote(location_param)}"
    
    return f"**{base_text}**\n\n👉 [ぐるなびでレストランを見る]({gnavi_url})"