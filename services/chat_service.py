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
from services.google_places_service import GooglePlacesService, format_google_places_response

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
    import time
    start_time = time.time()
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
            # DBにデータがない場合はエラー（PKL後方互換性は廃止）
            error_msg = f"申し訳ありません。企業ID「{company_id}」のFAQデータが見つかりません。"
            return error_msg, 0, 0
        
        print(f"FAQ データ: {len(faq_data)} 件")
        
        # エンベディングデータの詳細診断
        embedding_stats = {"total": len(faq_data), "with_embedding": 0, "without_embedding": 0}
        for faq in faq_data:
            if faq['embedding'] is not None:
                embedding_stats["with_embedding"] += 1
            else:
                embedding_stats["without_embedding"] += 1
        
        print(f"[EMBEDDING STATS] 総FAQ: {embedding_stats['total']}, エンベディング有: {embedding_stats['with_embedding']}, エンベディング無: {embedding_stats['without_embedding']}")
        
        # レストラン判定は unified_chat_service.py に委譲
        # 二重処理を避けるため、chat_service.py ではレストラン検索を行わない
        UnifiedConfig.log_debug(f"レストラン判定結果: {_is_restaurant_query(user_input)} (unified_chat_serviceに委譲)")
        
        # ユーザー入力のエンベディングを取得
        user_embedding = get_embedding(user_input)
        
        # エンベディングが存在するFAQのみを抽出
        valid_faqs = [faq for faq in faq_data if faq['embedding'] is not None]
        
        if not valid_faqs:
            # エンベディングが見つからない場合の対応
            if len(faq_data) > 0:
                # FAQデータはあるがエンベディングがない場合
                UnifiedConfig.log_warning(f"企業「{company_id}」: FAQデータ{len(faq_data)}件中、有効なエンベディングが0件です")
                
                # テストモードまたはエンベディング生成を提案
                if UnifiedConfig.is_test_mode():
                    # テストモードの場合はキーワードマッチングにフォールバック
                    return _fallback_keyword_search(user_input, faq_data)
                else:
                    error_msg = (f"申し訳ありません。企業ID「{company_id}」のエンベディングデータが見つかりません。\n"
                               f"管理者にエンベディング生成を依頼してください。\n"
                               f"FAQデータ: {len(faq_data)}件, エンベディング: {embedding_stats['with_embedding']}件")
                    return error_msg, 0, 0
            else:
                error_msg = f"申し訳ありません。企業ID「{company_id}」のFAQデータが見つかりません。"
                return error_msg, 0, 0
        
        # コサイン類似度の計算
        embeddings_list = [faq['embedding'] for faq in valid_faqs]
        similarities = cosine_similarity([user_embedding], embeddings_list)
        
        # 類似度の上位10件を表示（デバッグモードのみ）
        top_indices = np.argsort(similarities[0])[::-1][:10]
        
        # 結果をリスト化
        similarity_results = []
        for idx in top_indices:
            if idx < len(valid_faqs):
                similarity_results.append((idx, similarities[0][idx], valid_faqs[idx]['question']))
        
        # ログ出力（環境によって制御）
        UnifiedConfig.log_faq_search_details(similarity_results, 10)
        
        # 最も類似度の高い質問のインデックスを取得
        best_idx = np.argmax(similarities)
        similarity_score = similarities[0][best_idx]
        
        UnifiedConfig.log_debug(f"最適合FAQ: {valid_faqs[best_idx]['question']}")
        UnifiedConfig.log_info(f"FAQマッチング結果: 類似度{similarity_score:.3f}")
        
        # 高信頼度FAQ検索成功時の最適化処理
        if similarity_score >= 0.8:
            UnifiedConfig.log_debug(f"[PERFORMANCE] 高信頼度FAQ検索成功、他の処理をスキップ")
            
            # 対応する回答を取得
            answer = valid_faqs[best_idx]["answer"]
            
            # FAQ回答内の[単語]にBingリンクを追加
            answer = add_bing_links_to_brackets(answer)
            
            user_lang = detect_language(user_input)
            UnifiedConfig.log_info(f"質問言語: {user_lang}")
            
            # 外国語の質問の場合は回答を翻訳
            if user_lang != 'ja':
                translation_service = TranslationService()
                translated_answer = translation_service.translate_text(answer, user_lang, 'ja')
                answer = _preserve_japanese_links_in_translation(answer, translated_answer)
                UnifiedConfig.log_info(f"回答を{user_lang}に翻訳完了")
            
            # パフォーマンス監視
            elapsed_time = time.time() - start_time
            UnifiedConfig.log_info(f"[PERFORMANCE] FAQ検索処理時間: {elapsed_time:.2f}s (高信頼度早期リターン)")
            return answer, len(user_input.split()), len(answer.split())
        
        # 対応する回答を取得（低〜中信頼度の場合の通常処理）
        answer = valid_faqs[best_idx]["answer"]
        
        # FAQ回答内の[単語]にBingリンクを追加
        answer = add_bing_links_to_brackets(answer)
        
        user_lang = detect_language(user_input)
        UnifiedConfig.log_info(f"質問言語: {user_lang}")
        
        # 外国語の質問の場合は回答を翻訳
        if user_lang != 'ja':
            translation_service = TranslationService()
            # 詳細情報リンクは日本語のまま保持し、説明文のみ翻訳
            translated_answer = translation_service.translate_text(answer, user_lang, 'ja')
            # リンク部分は日本語のまま保持するため、元の回答と翻訳された回答を適切に結合
            answer = _preserve_japanese_links_in_translation(answer, translated_answer)
            UnifiedConfig.log_info(f"回答を{user_lang}に翻訳完了")
        
        # 類似度スコアが低すぎる場合
        if similarity_score < SIMILARITY_THRESHOLD:
            # # 非常に低い類似度の場合
            # LINE通知を送信
            UnifiedConfig.log_info(f"類似度低下によるLINE通知送信: {similarity_score:.3f}")
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

        # パフォーマンス監視
        elapsed_time = time.time() - start_time  
        UnifiedConfig.log_info(f"[PERFORMANCE] 総処理時間: {elapsed_time:.2f}s")
        return answer, len(user_input.split()), len(answer.split())
    
    except Exception as e:
        UnifiedConfig.log_error(f"回答取得エラー: {e}")
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
            UnifiedConfig.log_error(f"LINE通知エラー: {line_error}")
        
        # パフォーマンス監視（エラー時）
        elapsed_time = time.time() - start_time
        UnifiedConfig.log_info(f"[PERFORMANCE] エラー処理時間: {elapsed_time:.2f}s")
        return error_message, 0, 0


def _fallback_keyword_search(user_input, faq_data):
    """エンベディングが利用できない場合のキーワードマッチング検索"""
    try:
        print(f"[FALLBACK] キーワード検索開始: '{user_input}'")
        
        # キーワードベースの簡易検索
        user_keywords = user_input.lower().replace("？", "").replace("?", "").strip()
        
        best_match = None
        best_score = 0
        
        for faq in faq_data:
            question = faq['question'].lower()
            answer = faq['answer']
            
            # キーワードマッチングスコアを計算
            score = 0
            
            # 完全一致
            if user_keywords in question:
                score += 10
            
            # 部分的なキーワードマッチング
            user_words = user_keywords.split()
            for word in user_words:
                if len(word) >= 2 and word in question:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = faq
        
        if best_match and best_score > 0:
            print(f"[FALLBACK] マッチ見つかりました: スコア{best_score}, 質問: {best_match['question']}")
            answer = best_match['answer']
            answer = add_bing_links_to_brackets(answer)
            return answer, len(user_input.split()), len(answer.split())
        else:
            print(f"[FALLBACK] マッチしませんでした")
            fallback_msg = (
                "申し訳ございません。現在、エンベディングシステムが利用できないため、"
                "簡易検索を行いましたが、適切な回答が見つかりませんでした。\n"
                "スタッフにお問い合わせください。"
            )
            return fallback_msg, len(user_input.split()), len(fallback_msg.split())
            
    except Exception as e:
        print(f"[FALLBACK] キーワード検索エラー: {e}")
        error_msg = "検索処理でエラーが発生しました。スタッフにお問い合わせください。"
        return error_msg, 0, 0


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
    アレルギーや健康関連の文脈がある場合は除外する
    """
    query_lower = query.lower()
    
    # アレルギー・健康関連キーワードがある場合は除外
    allergy_keywords = [
        "アレルギー", "アレルギ", "allergy", "allergies", "allergic",
        "알레르기", "过敏", "過敏", "健康", "health", "医療", "medical",
        "病気", "illness", "体調", "condition"
    ]
    
    # アレルギー・健康関連の文脈がある場合はレストラン検索対象外
    if any(keyword in query_lower for keyword in allergy_keywords):
        return False
    
    # レストラン・グルメ関連キーワード
    restaurant_keywords = [
        "レストラン", "グルメ", "ランチ", "ディナー", "飲食", "料理", 
        "カフェ", "居酒屋", "食べ物", "美味しい", "おすすめ", "食べる",
        "restaurant", "eat", "dinner", "lunch", "cafe", "gourmet",
        "맛집", "음식", "식당", "레스토랑", "카페", "먹다",
        "餐厅", "美食", "吃", "料理", "咖啡厅"
    ]
    
    # 単純な「food」は除外し、より具体的なレストラン関連キーワードのみ対象とする
    # 「食事」も宿泊施設のサービスの一部なのでレストラン検索対象外とする
    restaurant_specific_keywords = [
        "レストラン", "グルメ", "ランチ", "ディナー", "カフェ", "居酒屋", 
        "美味しい", "おすすめ", "食べる",
        "restaurant", "eat", "dinner", "lunch", "cafe", "gourmet",
        "맛집", "식당", "레스토랑", "카페", "먹다",
        "餐厅", "美食", "吃", "咖啡厅"
    ]
    
    return any(keyword in query_lower for keyword in restaurant_specific_keywords)


def _generate_gnavi_response(query: str, user_lang: str) -> str:
    """
    Google Places APIを使用してレストラン情報を検索し、10件表示する
    """
    try:
        # Google Places Serviceを初期化
        places_service = GooglePlacesService()
        
        # クエリから地域名を抽出（デフォルトは「別府」）
        location = _extract_location_from_query(query)
        print(f"[RESTAURANT_SEARCH] 抽出された地域: {location}")
        
        # レストラン検索実行
        restaurants = places_service.search_restaurants(location, "レストラン", user_lang)
        
        if restaurants:
            # Google Places APIの結果をフォーマット
            formatted_response = format_google_places_response(
                restaurants, location, "レストラン", user_lang
            )
            
            # 追加の詳細情報リンクを付加
            additional_info = _get_additional_restaurant_info(location, user_lang)
            
            return f"{formatted_response}\n\n{additional_info}"
        else:
            # フォールバック: 従来のぐるなびリンク
            return _generate_fallback_restaurant_response(location, user_lang)
            
    except Exception as e:
        print(f"[RESTAURANT_SEARCH] エラー: {e}")
        # エラー時は従来のぐるなびリンクにフォールバック
        return _generate_fallback_restaurant_response("別府", user_lang)


def _extract_location_from_query(query: str) -> str:
    """
    クエリから地域名を抽出する（多言語対応）
    """
    # 地域名のパターンマッチング（日本語・英語・韓国語・中国語）
    location_patterns = [
        # 九州の主要都市
        (r'別府|別府市|Beppu', '別府'),
        (r'大分|大分市|Oita', '大分'), 
        (r'湯布院|由布院|Yufuin', '湯布院'),
        (r'福岡|博多|Fukuoka|Hakata', '福岡'),
        (r'熊本|Kumamoto', '熊本'),
        (r'鹿児島|Kagoshima', '鹿児島'),
        (r'長崎|Nagasaki', '長崎'),
        (r'佐賀|Saga', '佐賀'),
        (r'宮崎|Miyazaki', '宮崎'),
        (r'沖縄|Okinawa', '沖縄'),
        
        # 関西
        (r'京都|京都市|Kyoto', '京都'),
        (r'大阪|大阪市|Osaka', '大阪'),
        (r'神戸|Kobe', '神戸'),
        (r'奈良|Nara', '奈良'),
        
        # 関東  
        (r'東京|Tokyo', '東京'),
        (r'横浜|Yokohama', '横浜'),
        (r'千葉|Chiba', '千葉'),
        (r'埼玉|Saitama', '埼玉'),
        
        # その他主要都市
        (r'名古屋|Nagoya', '名古屋'),
        (r'金沢|Kanazawa', '金沢'),
        (r'札幌|Sapporo', '札幌'),
        (r'仙台|Sendai', '仙台'),
        
        # 韓国・中国語の主要都市
        (r'서울|Seoul|首尔', 'ソウル'),
        (r'부산|Busan|釜山', '釜山'),
        (r'도쿄|东京', '東京'),
        (r'오사카|大阪', '大阪'),
        (r'교토|京都', '京都')
    ]
    
    # 大文字小文字を区別しない検索
    query_lower = query.lower()
    
    for pattern, location_name in location_patterns:
        if re.search(pattern, query_lower, re.IGNORECASE):
            print(f"[LOCATION_EXTRACT] パターン '{pattern}' が '{query}' でマッチ → '{location_name}'")
            return location_name
    
    print(f"[LOCATION_EXTRACT] 地域名が見つからなかったため、デフォルトの '別府' を使用")
    # デフォルトは「別府」
    return "別府"


def _get_additional_restaurant_info(location: str, user_lang: str) -> str:
    """
    追加のレストラン情報リンクを生成
    """
    # ぐるなび検索URL
    gnavi_url = f"https://r.gnavi.co.jp/area/jp/rs/?fwp={urllib.parse.quote(location)}"
    
    # 食べログ検索URL  
    tabelog_url = f"https://tabelog.com/{location}/"
    
    # 多言語対応のラベル
    labels = {
        "ja": {
            "detail_info": "📍 詳細情報:",
            "gnavi": "🍽️ グルメ情報（ぐるなび）",
            "tabelog": "⭐ レストラン口コミ（食べログ）",
            "footer": "💡 地元の美味しいお店をお探しでしたら、フロントスタッフにもお気軽にお声がけください！"
        },
        "en": {
            "detail_info": "📍 Detailed Information:",
            "gnavi": "🍽️ Gourmet Information (Gurunavi)",
            "tabelog": "⭐ Restaurant Reviews (Tabelog)",
            "footer": "💡 If you're looking for delicious local restaurants, please feel free to ask our front desk staff!"
        },
        "ko": {
            "detail_info": "📍 상세 정보:",
            "gnavi": "🍽️ 맛집 정보 (구루나비)",
            "tabelog": "⭐ 레스토랑 리뷰 (타베로그)",
            "footer": "💡 현지 맛집을 찾고 계신다면, 프론트 직원에게 언제든지 문의해주세요!"
        },
        "zh": {
            "detail_info": "📍 详细信息:",
            "gnavi": "🍽️ 美食信息 (GURUNAVI)",
            "tabelog": "⭐ 餐厅评价 (食べログ)",
            "footer": "💡 如需寻找当地美食，请随时向前台工作人员咨询！"
        }
    }
    
    lang_labels = labels.get(user_lang, labels["ja"])
    
    return f"""{lang_labels['detail_info']}
• [{lang_labels['gnavi']}]({gnavi_url})
• [{lang_labels['tabelog']}]({tabelog_url})

{lang_labels['footer']}"""


def _generate_fallback_restaurant_response(location: str, user_lang: str) -> str:
    """
    Google Places APIが利用できない場合のフォールバック レスポンス
    """
    # デフォルトの案内文
    default_responses = {
        "ja": f"{location}のレストラン情報をお探しですね。以下のリンクから詳細情報をご確認いただけます。",
        "en": f"Looking for restaurant information in {location}. Please check the links below for detailed information.",
        "ko": f"{location}의 레스토랑 정보를 찾고 계시는군요. 아래 링크에서 자세한 정보를 확인하실 수 있습니다.",
        "zh": f"正在寻找{location}的餐厅信息。请通过以下链接查看详细信息。"
    }
    
    base_text = default_responses.get(user_lang, default_responses["ja"])
    additional_info = _get_additional_restaurant_info(location, user_lang)
    
    return f"{base_text}\n\n{additional_info}"