"""
統合型会話AIサービス
services/unified_chat_service.py

FAQ → 観光 → LINE通知の統合フロー
"""
import re
from typing import Dict, List, Tuple, Optional
from services.chat_service import get_response
from services.tourism_service import (
    detect_language, 
    generate_tourism_response_by_city
)
from services.line_notification_service import LineNotificationService
from services.specialized_link_service import SpecializedLinkService
from services.enhanced_location_service import EnhancedLocationService
from services.google_places_service import GooglePlacesService, format_google_places_response
from services.translation_service import TranslationService

# 信頼度しきい値
HIGH_CONFIDENCE_THRESHOLD = 0.8
MEDIUM_CONFIDENCE_THRESHOLD = 0.5

# 観光・グルメキーワード（多言語対応）
TOURISM_KEYWORDS = [
    # 日本語
    '観光', '観光地', '観光スポット', 'スポット', '名所', '見どころ',
    '散歩', '散策', 'ドライブ', '旅行', '旅', '見学', 
    # 英語
    'sightseeing', 'tourist', 'tourism', 'attraction', 'spots', 'places',
    'visit', 'travel', 'explore', 'landmark',
    # 韓国語
    '관광', '관광지', '관광스팟', '명소', '볼거리', '여행', '관광명소', 
    '구경', '둘러보기', '산책', '드라이브', '투어',
    # 中国語
    '观光', '旅游', '景点', '名胜', '游览', '参观', '旅行'
]

# 旅館内vs外部レストランの判別キーワード
INTERNAL_RESTAURANT_KEYWORDS = [
    '旅館', 'こちら', 'ここ', '館内', '内', '朝食', '夕食', '食事', '料理',
    'お食事', '懐石', '会席', '膳', 'お膳', '宿', 'hotel', 'ryokan'
]

EXTERNAL_RESTAURANT_KEYWORDS = [
    '周辺', '近く', '外', '外食', '街', '市内', '地域', 'エリア', 'around', 
    'nearby', '行ける', '歩いて', '車で', 'おすすめ', 'お勧め'
]

GENERAL_RESTAURANT_KEYWORDS = [
    # 日本語
    'レストラン', 'グルメ', 'ランチ', 'ディナー', 
    '美味しい', 'おいしい', 'カフェ', '居酒屋', '食事', '料理', '飲食',
    # 英語
    'restaurant', 'food', 'dining', 'lunch', 'dinner', 'cafe', 'gourmet',
    'delicious', 'tasty', 'eat', 'meal',
    # 韓国語
    '레스토랑', '맛집', '음식', '음식점', '식당', '카페', '점심', '저녁',
    '맛있는', '식사', '그루메', '미식', '먹을곳',
    # 中国語
    '餐厅', '美食', '餐饮', '午餐', '晚餐', '咖啡厅', '好吃', '餐馆'
]

class UnifiedChatService:
    def __init__(self):
        self.line_service = LineNotificationService()
        self.link_service = SpecializedLinkService()
        self.location_service = EnhancedLocationService()
        self.google_places = GooglePlacesService()
        self.translation_service = TranslationService()
    
    def get_unified_response(
        self, 
        user_input: str, 
        company_id: str, 
        user_info: str = "",
        location_context: Dict = None
    ) -> Dict:
        """
        統合会話レスポンス（自動多言語対応）
        
        Returns:
            Dict: {
                "answer": str,
                "confidence_score": float,
                "response_type": str,
                "specialized_links": List[Dict],
                "needs_human_support": bool,
                "location_enhanced": bool,
                "original_language": str,  # 追加
                "translated_input": str   # 追加
            }
        """
        # Step 1: 言語自動検出 & 日本語翻訳
        translated_input, original_language = self.translation_service.detect_language_and_translate_to_japanese(user_input)
        print(f"[UNIFIED_CHAT] 言語検出: {original_language}, 翻訳: '{user_input}' → '{translated_input}'")
        
        # デバッグ：翻訳結果のキーワードチェック
        print(f"[DEBUG] 翻訳後の観光キーワード検出: {any(keyword in translated_input.lower() for keyword in TOURISM_KEYWORDS)}")
        print(f"[DEBUG] 翻訳後のレストランキーワード検出: {any(keyword in translated_input.lower() for keyword in GENERAL_RESTAURANT_KEYWORDS)}")
        
        # Step 2: 位置情報の正規化（多言語対応）
        location_info = self._get_optimized_location(location_context, company_id)
        
        # ユーザーが特定の地名を入力した場合は、それを最優先で使用
        if location_context and location_context.get('manual_location'):
            original_location = location_context['manual_location']
            # ユーザー入力位置を直接検証・使用
            user_location_data = self.location_service.validate_location_input(original_location)
            if user_location_data:
                # ユーザー入力の位置情報で上書き
                location_info = {
                    'source': 'user_input_priority',
                    'location': user_location_data,
                    'confidence': 0.98
                }
                print(f"[DEBUG] ユーザー入力位置を優先使用: {user_location_data}")
            else:
                # フォールバック: 従来の正規化処理
                normalized_location = self._normalize_location_for_context(original_location)
                if normalized_location != original_location:
                    location_context['manual_location'] = normalized_location
                    location_info = self._get_optimized_location(location_context, company_id)
        
        # Step 3: FAQ検索（翻訳済みテキストで実行）
        faq_result = self._get_faq_with_confidence(translated_input, company_id, user_info)
        
        # Step 4: 観光・グルメ意図検出（翻訳済みテキストで実行）
        tourism_intent = self._detect_tourism_intent(translated_input)
        restaurant_analysis = self._analyze_restaurant_intent(translated_input)
        
        # Step 5: インテリジェントなレスポンス生成（日本語で生成）
        response = self._generate_intelligent_response(
            faq_result, translated_input, location_info, original_language,
            tourism_intent, restaurant_analysis, company_id, user_info
        )
        
        # Step 6: レスポンスを元言語に翻訳（詳細情報リンクは日本語のまま保持）
        if original_language != 'ja':
            # メインの回答文は翻訳するが、詳細情報リンクは日本語のまま保持
            response['answer'] = self._translate_response_preserving_links(
                response['answer'], 
                original_language
            )
        
        # 追加情報を返す
        response['original_language'] = original_language
        response['translated_input'] = translated_input
        
        return response
    
    def _normalize_location_for_context(self, location_input: str) -> str:
        """
        位置情報入力を正規化（多言語→日本語地名）
        """
        print(f"[DEBUG] 位置情報正規化開始: '{location_input}'")
        try:
            location_data = self.location_service.validate_location_input(location_input)
            print(f"[DEBUG] validate_location_input結果: {location_data}")
            
            if location_data and 'city' in location_data:
                # '市'を除去して返す
                city_name = location_data['city']
                if city_name.endswith('市'):
                    normalized = city_name[:-1]  # '福岡市' → '福岡'
                    print(f"[DEBUG] 市除去後: '{city_name}' → '{normalized}'")
                    return normalized
                print(f"[DEBUG] そのまま返す: '{city_name}'")
                return city_name
            
            print(f"[DEBUG] 正規化失敗、元の入力を返す: '{location_input}'")
            return location_input
        except Exception as e:
            print(f"[UNIFIED_CHAT] 位置情報正規化エラー: {e}")
            return location_input
    
    def _get_faq_with_confidence(self, user_input: str, company_id: str, user_info: str) -> Dict:
        """FAQ検索（信頼度スコア付き）"""
        try:
            response, input_tokens, output_tokens = get_response(
                user_input, company_id, user_info
            )
            
            # 簡易的な信頼度計算（より精密な実装が必要）
            confidence = self._calculate_faq_confidence(user_input, response)
            
            return {
                "answer": response,
                "confidence": confidence,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        except Exception as e:
            print(f"FAQ検索エラー: {e}")
            return {
                "answer": "申し訳ございません。現在システムに問題が発生しております。",
                "confidence": 0.0,
                "input_tokens": 0,
                "output_tokens": 0
            }
    
    def _calculate_faq_confidence(self, question: str, answer: str) -> float:
        """FAQ信頼度の簡易計算"""
        # システムデフォルト応答の場合は低信頼度
        if "申し訳ございません" in answer and "システムに問題" in answer:
            return 0.1
        
        if "現在システムに問題が発生" in answer:
            return 0.1
            
        # 具体的な情報が含まれている場合は高信頼度
        if any(word in answer for word in ["時間", "料金", "場所", "方法", "サービス"]):
            return 0.9
            
        # 短すぎる回答は低信頼度
        if len(answer) < 20:
            return 0.3
            
        # デフォルト中程度信頼度
        return 0.6
    
    def _detect_tourism_intent(self, text: str) -> bool:
        """観光意図検出（多言語対応）"""
        # 大文字小文字を区別しない検索
        text_lower = text.lower()
        
        # 日本語・英語・韓国語・中国語のキーワードチェック
        has_tourism_keyword = any(keyword.lower() in text_lower for keyword in TOURISM_KEYWORDS)
        
        print(f"[DEBUG] 観光意図検出 - テキスト: '{text}', 結果: {has_tourism_keyword}")
        if has_tourism_keyword:
            matching_keywords = [k for k in TOURISM_KEYWORDS if k.lower() in text_lower]
            print(f"[DEBUG] マッチしたキーワード: {matching_keywords}")
        
        return has_tourism_keyword
    
    def _analyze_restaurant_intent(self, text: str) -> Dict:
        """レストラン意図の詳細分析（多言語対応）"""
        text_lower = text.lower()
        
        # 基本的なレストラン関連キーワードの検出（多言語）
        has_restaurant_keywords = any(keyword.lower() in text_lower for keyword in GENERAL_RESTAURANT_KEYWORDS)
        
        print(f"[DEBUG] レストラン意図分析 - テキスト: '{text}', キーワード検出: {has_restaurant_keywords}")
        if has_restaurant_keywords:
            matching_keywords = [k for k in GENERAL_RESTAURANT_KEYWORDS if k.lower() in text_lower]
            print(f"[DEBUG] マッチしたレストランキーワード: {matching_keywords}")
        
        if not has_restaurant_keywords:
            return {
                'has_intent': False,
                'context': 'none',
                'confidence': 0.0
            }
        
        # 内部（旅館内）を示すキーワード
        internal_signals = sum(1 for keyword in INTERNAL_RESTAURANT_KEYWORDS if keyword in text_lower)
        
        # 外部（周辺）を示すキーワード
        external_signals = sum(1 for keyword in EXTERNAL_RESTAURANT_KEYWORDS if keyword in text_lower)
        
        # コンテキスト判定
        if internal_signals > external_signals:
            context = 'internal'  # 旅館内の食事について
            confidence = 0.8 + (internal_signals * 0.1)
        elif external_signals > internal_signals:
            context = 'external'  # 周辺レストランについて
            confidence = 0.8 + (external_signals * 0.1)
        else:
            # 曖昧な場合：「おすすめのレストランは？」のような質問
            # デフォルトで外部レストランと判定（一般的な使用パターン）
            context = 'external'
            confidence = 0.6
        
        return {
            'has_intent': True,
            'context': context,
            'confidence': min(confidence, 1.0),
            'internal_signals': internal_signals,
            'external_signals': external_signals
        }
    
    def _get_optimized_location(self, location_context: Dict, company_id: str) -> Dict:
        """最適化された位置情報取得"""
        if not location_context:
            location_context = {}
            
        return self.location_service.get_accurate_location(
            user_input_location=location_context.get('manual_location'),
            gps_coords=location_context.get('gps_coords'),
            company_id=company_id
        )
    
    def _generate_intelligent_response(
        self, faq_result: Dict, translated_input: str, location_info: Dict,
        language: str, tourism_intent: bool, restaurant_analysis: Dict,
        company_id: str, user_info: str
    ) -> Dict:
        """インテリジェントなレスポンス生成"""
        
        # 高信頼度FAQ + 適切な追加情報
        if faq_result['confidence'] >= HIGH_CONFIDENCE_THRESHOLD:
            return self._handle_high_confidence_with_smart_addition(
                faq_result, translated_input, location_info, language,
                tourism_intent, restaurant_analysis
            )
        
        # レストラン質問の専用処理
        if restaurant_analysis['has_intent']:
            return self._handle_restaurant_specific_query(
                faq_result, translated_input, location_info, language,
                restaurant_analysis, company_id, user_info
            )
        
        # 観光質問の専用処理
        if tourism_intent:
            print(f"[DEBUG] 観光質問として処理開始")
            return self._handle_tourism_specific_query(
                faq_result, translated_input, location_info, language,
                company_id, user_info
            )
        
        # 中程度信頼度FAQまたは混合質問
        if faq_result['confidence'] >= MEDIUM_CONFIDENCE_THRESHOLD:
            return self._handle_medium_confidence_faq(
                faq_result, translated_input, location_info, language
            )
        
        # 未知クエリ
        return self._handle_unknown_query(
            translated_input, company_id, user_info, language
        )
    
    def _handle_restaurant_specific_query(
        self, faq_result: Dict, translated_input: str, location_info: Dict,
        language: str, restaurant_analysis: Dict, company_id: str, user_info: str
    ) -> Dict:
        """レストラン専用クエリ処理"""
        
        context = restaurant_analysis['context']
        response_text = ""
        specialized_links = []
        response_type = "restaurant"
        
        # 内部（旅館内食事）への質問
        if context == 'internal':
            if faq_result['confidence'] >= MEDIUM_CONFIDENCE_THRESHOLD:
                response_text = f"🏨 **旅館のお食事について:**\n{faq_result['answer']}"
                response_type = "internal_restaurant"
            else:
                response_text = "🏨 **旅館のお食事について:**\nお食事に関する詳細は、フロントまでお気軽にお尋ねください。"
                response_type = "internal_restaurant_unknown"
        
        # 外部（周辺レストラン）への質問
        elif context == 'external' and location_info:
            # FAQは関連性が低いため表示しない
            city_name = location_info.get('location', {}).get('city', '不明な地域')
            
            try:
                # Google Places APIでレストラン検索
                google_restaurants = self.google_places.search_restaurants(city_name, translated_input, language)
                
                if google_restaurants:
                    # Google Places APIの結果を使用（日本語表示固定）
                    # 観光・レストラン検索結果は常に日本語で表示
                    query_type_translated = "レストラン"
                    response_text = format_google_places_response(google_restaurants, city_name, query_type_translated, 'ja')
                    
                    # 追加の専門リンクも提供（日本語固定）
                    links = self.link_service.generate_specialized_links(
                        translated_input, location_info['location'], 'restaurant', 'ja'
                    )
                    specialized_links.extend(links)
                    
                    if links:
                        # その他のグルメ情報（日本語固定）
                        response_text += "\n\n📍 **その他のグルメ情報:**\n"
                        for link in links[:2]:
                            response_text += f"• **[{link['name']}]({link['url']})**\n"
                else:
                    # フォールバック: 従来のリンク生成（日本語固定）
                    links = self.link_service.generate_specialized_links(
                        translated_input, location_info['location'], 'restaurant', 'ja'
                    )
                    specialized_links.extend(links)
                    
                    # ヘッダー（日本語固定）
                    response_text = f"🍽️ **{city_name}のグルメ情報:**\n"
                    for link in links[:5]:
                        response_text += f"• **[{link['name']}]({link['url']})**\n"
                
                # フッター（日本語固定）
                response_text += "\n\n💡 地元の美味しいお店をお探しでしたら、フロントスタッフにもお気軽にお声がけください！"
                response_type = "external_restaurant"
                
            except Exception as e:
                print(f"Google Places API エラー: {e}")
                # エラー時のフォールバック（日本語固定）
                links = self.link_service.generate_specialized_links(
                    translated_input, location_info['location'], 'restaurant', 'ja'
                )
                specialized_links.extend(links)
                
                response_text = f"🍽️ **{city_name}のグルメ情報:**\n"
                for link in links[:5]:
                    response_text += f"• **[{link['name']}]({link['url']})**\n"
                
                # フッター（日本語固定）
                response_text += "\n💡 地元の美味しいお店をお探しでしたら、フロントスタッフにもお気軽にお声がけください！"
                response_type = "external_restaurant"
        
        else:
            # 位置情報なしまたは曖昧な場合
            response_text = "🍽️ **お食事について:**\n"
            if faq_result['confidence'] >= MEDIUM_CONFIDENCE_THRESHOLD:
                response_text += f"• 館内でのお食事: {faq_result['answer']}\n\n"
            response_text += "• 周辺レストラン情報: 位置情報を設定していただくと、地域のグルメ情報をご案内できます。"
            response_type = "restaurant_general"
        
        return {
            "answer": response_text,
            "confidence_score": restaurant_analysis['confidence'],
            "response_type": response_type,
            "specialized_links": specialized_links,
            "needs_human_support": False,
            "location_enhanced": bool(location_info and specialized_links)
        }
    
    def _handle_high_confidence_with_smart_addition(
        self, faq_result: Dict, translated_input: str, location_info: Dict,
        language: str, tourism_intent: bool, restaurant_analysis: Dict
    ) -> Dict:
        """高信頼度FAQ + スマートな追加情報"""
        response_text = faq_result["answer"]
        specialized_links = []
        
        # 観光関連の場合のみ追加情報を提供
        if tourism_intent and location_info:
            links = self.link_service.generate_specialized_links(
                translated_input, location_info['location'], 'tourism', language
            )
            specialized_links.extend(links)
            
            response_text += f"\n\n📍 **{location_info.get('location', {}).get('city', '不明な地域')}周辺の観光情報:**\n"
            for link in specialized_links[:2]:
                response_text += f"• **[{link['name']}]({link['url']})**\n"
        
        return {
            "answer": response_text,
            "confidence_score": faq_result["confidence"],
            "response_type": "faq_enhanced",
            "specialized_links": specialized_links,
            "needs_human_support": False,
            "location_enhanced": bool(location_info and specialized_links)
        }
    
    def _handle_tourism_specific_query(
        self, faq_result: Dict, translated_input: str, location_info: Dict,
        language: str, company_id: str, user_info: str
    ) -> Dict:
        """観光専用クエリ処理"""
        
        print(f"[DEBUG] 観光専用クエリ処理開始")
        print(f"[DEBUG] location_info: {location_info}")
        print(f"[DEBUG] language: {language}")
        print(f"[DEBUG] translated_input: '{translated_input}'")
        
        if not location_info:
            print(f"[DEBUG] 位置情報なしのため早期終了")
            return {
                "answer": "🌸 **観光情報について:**\n位置情報を設定していただくと、より詳しい観光情報をご案内できます。",
                "confidence_score": 0.5,
                "response_type": "tourism_no_location",
                "specialized_links": [],
                "needs_human_support": False,
                "location_enhanced": False
            }
        
        city_name = location_info.get('location', {}).get('city', '不明な地域')
        print(f"[DEBUG] 検索対象都市: '{city_name}'")
        
        try:
            # Google Places APIで観光スポット検索
            print(f"[DEBUG] Google Places API検索開始: city='{city_name}', query='{translated_input}', language='{language}'")
            google_places = self.google_places.search_tourism_spots(city_name, translated_input, language)
            print(f"[DEBUG] Google Places API結果数: {len(google_places) if google_places else 0}")
            
            if google_places:
                print(f"[DEBUG] Google Places APIから結果取得、フォーマット開始")
                # Google Places APIの結果を使用（日本語固定）
                response_text = format_google_places_response(google_places, city_name, "観光スポット", 'ja')
                
                # 追加の専門リンクも提供（日本語固定）
                print(f"[DEBUG] 専門リンク生成開始: translated_input='{translated_input}', location={location_info['location']}")
                links = self.link_service.generate_specialized_links(
                    translated_input, location_info['location'], 'tourism', 'ja'
                )
                print(f"[DEBUG] 専門リンク生成結果: {len(links)}件")
                for i, link in enumerate(links[:3]):
                    print(f"[DEBUG] リンク{i+1}: {link['name']} -> {link['url']}")
                
                if links:
                    response_text += "\n\n📍 **その他の情報源:**\n"
                    for link in links[:2]:
                        response_text += f"• **[{link['name']}]({link['url']})**\n"
                else:
                    print(f"[DEBUG] 専門リンクが生成されませんでした")
            else:
                print(f"[DEBUG] Google Places APIから結果なし、フォールバック開始")
                # フォールバック: 従来の観光情報生成（日本語固定）
                tourism_response, tourism_links = generate_tourism_response_by_city(
                    translated_input, city_name, 'ja'
                )
                print(f"[DEBUG] フォールバック観光レスポンス生成: '{tourism_response[:100]}...'")
                
                # 専門リンク生成（日本語固定）
                print(f"[DEBUG] フォールバック専門リンク生成開始: location={location_info['location']}")
                links = self.link_service.generate_specialized_links(
                    translated_input, location_info['location'], 'tourism', 'ja'
                )
                print(f"[DEBUG] フォールバック専門リンク数: {len(links)}")
                for i, link in enumerate(links[:3]):
                    print(f"[DEBUG] フォールバックリンク{i+1}: {link['name']} -> {link['url']}")
                
                response_text = f"🌸 **{city_name}の観光情報:**\n{tourism_response}\n\n"
                if links:
                    response_text += "📍 **詳細情報:**\n"
                    for link in links[:5]:
                        response_text += f"• **[{link['name']}]({link['url']})**\n"
                else:
                    response_text += "📍 **詳細情報を取得できませんでした**\n"
            
            return {
                "answer": response_text,
                "confidence_score": 0.8,
                "response_type": "tourism",
                "specialized_links": links,
                "needs_human_support": False,
                "location_enhanced": True
            }
            
        except Exception as e:
            print(f"観光情報取得エラー: {e}")
            return {
                "answer": f"🌸 **{city_name}の観光情報:**\n申し訳ございません。現在観光情報の取得に問題が発生しております。フロントスタッフにお尋ねください。",
                "confidence_score": 0.3,
                "response_type": "tourism_error",
                "specialized_links": [],
                "needs_human_support": True,
                "location_enhanced": False
            }
    
    def _handle_medium_confidence_faq(
        self, faq_result: Dict, translated_input: str, location_info: Dict, language: str
    ) -> Dict:
        """中程度信頼度FAQ処理"""
        
        response_text = f"📋 **FAQ回答:**\n{faq_result['answer']}\n\n"
        response_text += "💡 **他にもお手伝いできることがあれば、お気軽にお声がけください！**"
        
        return {
            "answer": response_text,
            "confidence_score": faq_result["confidence"],
            "response_type": "faq_medium",
            "specialized_links": [],
            "needs_human_support": False,
            "location_enhanced": False
        }
    
    def _handle_high_confidence_faq(
        self, faq_result: Dict, translated_input: str, location_info: Dict,
        language: str, tourism_intent: bool, restaurant_intent: bool
    ) -> Dict:
        """高信頼度FAQ処理"""
        response_text = faq_result["answer"]
        specialized_links = []
        
        # 観光・グルメ関連の場合は専門リンクを追加
        if (tourism_intent or restaurant_intent) and location_info:
            if tourism_intent:
                links = self.link_service.generate_specialized_links(
                    translated_input, location_info['location'], 'tourism', language
                )
                specialized_links.extend(links)
                
            if restaurant_intent:
                links = self.link_service.generate_specialized_links(
                    translated_input, location_info['location'], 'restaurant', language
                )
                specialized_links.extend(links)
            
            # 位置情報付き回答の拡張
            response_text += f"\n\n📍 **{location_info.get('location', {}).get('city', '不明な地域')}周辺の詳細情報:**\n"
            for link in specialized_links[:5]:  # 上位5件
                response_text += f"• **[{link['name']}]({link['url']})**\n"
        
        return {
            "answer": response_text,
            "confidence_score": faq_result["confidence"],
            "response_type": "faq",
            "specialized_links": specialized_links,
            "needs_human_support": False,
            "location_enhanced": bool(location_info and specialized_links)
        }
    
    def _handle_mixed_response(
        self, faq_result: Dict, translated_input: str, location_info: Dict,
        language: str, tourism_intent: bool, restaurant_intent: bool
    ) -> Dict:
        """混合レスポンス処理"""
        combined_response = ""
        specialized_links = []
        
        # FAQ部分
        if faq_result["confidence"] >= MEDIUM_CONFIDENCE_THRESHOLD:
            combined_response += f"📋 **FAQ回答:**\n{faq_result['answer']}\n\n"
        
        # 観光・グルメ情報追加
        if (tourism_intent or restaurant_intent) and location_info:
            try:
                city_name = location_info.get('location', {}).get('city', '不明な地域')
                
                if tourism_intent:
                    tourism_response, tourism_links = generate_tourism_response_by_city(
                        translated_input, city_name, language
                    )
                    combined_response += f"🌸 **観光情報:**\n{tourism_response}\n\n"
                    
                    # 専門リンク追加
                    links = self.link_service.generate_specialized_links(
                        translated_input, location_info['location'], 'tourism', language
                    )
                    specialized_links.extend(links)
                
                if restaurant_intent:
                    # グルメ専門リンク
                    links = self.link_service.generate_specialized_links(
                        translated_input, location_info['location'], 'restaurant', language
                    )
                    specialized_links.extend(links)
                    
                    combined_response += "🍽️ **グルメ情報:**\n"
                    for link in links[:2]:
                        combined_response += f"• **[{link['name']}]({link['url']})**\n"
                    combined_response += "\n"
                    
            except Exception as e:
                print(f"観光・グルメ情報取得エラー: {e}")
        
        # フォローアップ提案
        combined_response += "💡 **他にもお手伝いできることがあれば、お気軽にお声がけください！**"
        
        return {
            "answer": combined_response,
            "confidence_score": max(faq_result["confidence"], 0.7),
            "response_type": "mixed",
            "specialized_links": specialized_links,
            "needs_human_support": False,
            "location_enhanced": bool(location_info and specialized_links)
        }
    
    def _handle_unknown_query(
        self, translated_input: str, company_id: str, user_info: str, language: str
    ) -> Dict:
        """未知クエリ処理（LINE通知）"""
        # LINE通知送信
        notification_context = {
            'detected_language': language,
            'timestamp': self._get_current_timestamp(),
            'suggested_response': 'システムで回答できませんでした'
        }
        
        try:
            self.line_service.notify_staff_unknown_query(
                translated_input, company_id, user_info, notification_context
            )
        except Exception as e:
            print(f"LINE通知エラー: {e}")
        
        return {
            "answer": "申し訳ございません。その件については、担当者が確認いたします。しばらくお待ちください。\n\n💡 別のご質問がございましたら、お気軽にお尋ねください。",
            "confidence_score": 0.0,
            "response_type": "unknown",
            "specialized_links": [],
            "needs_human_support": True,
            "location_enhanced": False
        }
    
    def _get_current_timestamp(self) -> str:
        """現在時刻取得"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _translate_response_preserving_links(self, response_text: str, target_language: str) -> str:
        """
        回答を翻訳しつつ、詳細情報リンクは日本語のまま保持
        
        Args:
            response_text: 翻訳対象の回答テキスト
            target_language: 翻訳先言語コード
            
        Returns:
            str: 翻訳された回答（日本語リンク保持）
        """
        import re
        
        try:
            # 詳細情報セクションを分離
            # パターン1: 📍 **詳細情報:** または 📍 詳細情報:
            detail_pattern = r'📍\s*\*?\*?詳細情報[：:]\*?\*?.*'
            detail_match = re.search(detail_pattern, response_text, re.DOTALL)
            
            if detail_match:
                # 詳細情報部分とメイン部分を分離
                detail_section = detail_match.group(0)
                main_content = response_text[:detail_match.start()].strip()
                
                print(f"[TRANSLATE] 分離 - メイン: '{main_content[:50]}...', 詳細: '{detail_section[:50]}...'")
            else:
                # 詳細情報がない場合は全体を翻訳
                main_content = response_text
                detail_section = ""
                print(f"[TRANSLATE] 詳細情報なし、全体翻訳: '{main_content[:50]}...'")
            
            # メイン部分のみ翻訳
            if main_content:
                translated_main = self.translation_service.translate_text(
                    main_content, target_language, 'ja'
                )
                print(f"[TRANSLATE] 翻訳結果: '{translated_main[:50]}...'")
            else:
                translated_main = ""
            
            # 翻訳されたメイン部分 + 日本語の詳細情報を結合
            if detail_section:
                final_result = f"{translated_main}\n\n{detail_section}"
            else:
                final_result = translated_main
                
            print(f"[TRANSLATE] 最終結果: '{final_result[:100]}...'")
            return final_result
            
        except Exception as e:
            print(f"[TRANSLATE] 翻訳エラー: {e}")
            # エラー時は元のテキストを返す
            return response_text