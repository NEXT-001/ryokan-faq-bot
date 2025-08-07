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
    # 中国語（簡体字・繁体字）
    '餐厅', '美食', '餐饮', '午餐', '晚餐', '咖啡厅', '好吃', '餐馆',
    '推荐', '推薦', '信息', '資訊', '饮食', '飲食', '餐厅推荐', '餐廳推薦',
    '美食推荐', '美食推薦', '美食信息', '美食資訊', '餐廳', '餐館',
    '小吃', '特色菜', '当地美食', '當地美食', '有什么', '有什麼'
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
        location_context: Dict = None,
        previous_language: str = None
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
        # Step 1: 言語自動検出 & 日本語翻訳（改善版）
        if previous_language and previous_language != 'ja':
            # 前回が外国語の場合、同一言語の可能性を考慮
            print(f"[UNIFIED_CHAT] 前回言語: {previous_language}, 継続使用を検討")
            # 簡単な言語一致チェック（ハングル、英語アルファベット等）
            if self._matches_previous_language(user_input, previous_language):
                print(f"[UNIFIED_CHAT] 前回言語継続使用: {previous_language}")
                # 前回言語を使って日本語に翻訳
                translated_input = self.translation_service._translate_to_japanese_fast(user_input, previous_language)
                original_language = previous_language
            else:
                # 言語が変わった場合は通常検出
                translated_input, original_language = self.translation_service.detect_language_and_translate_to_japanese(user_input)
        else:
            # 初回の場合は確実な言語検出を実行
            print(f"[UNIFIED_CHAT] 初回検索または前回日本語: 言語検出を実行")
            translated_input, original_language = self.translation_service.detect_language_and_translate_to_japanese(user_input)
            
            # 英語検出の追加確認（初回の英語検出改善）
            if original_language == 'ja' and self._likely_english(user_input):
                print(f"[UNIFIED_CHAT] 英語パターン再検出: '{user_input}'")
                try:
                    translated_input = self.translation_service.translate_text(user_input, 'ja', 'en')
                    original_language = 'en'
                    print(f"[UNIFIED_CHAT] 英語として再処理: '{user_input}' → '{translated_input}'")
                except Exception as e:
                    print(f"[UNIFIED_CHAT] 英語再検出失敗: {e}, 日本語として処理継続")
        
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
        
        # Step 4: 観光・グルメ意図検出（原文と翻訳済みテキスト両方で実行）
        tourism_intent = (self._detect_tourism_intent(user_input) or 
                         self._detect_tourism_intent(translated_input))
        restaurant_analysis_original = self._analyze_restaurant_intent(user_input)
        restaurant_analysis_translated = self._analyze_restaurant_intent(translated_input)
        
        # 原文または翻訳後のどちらかでレストラン意図が検出された場合を統合
        restaurant_analysis = {
            'has_intent': restaurant_analysis_original['has_intent'] or restaurant_analysis_translated['has_intent'],
            'context': restaurant_analysis_original['context'] if restaurant_analysis_original['has_intent'] else restaurant_analysis_translated['context'],
            'confidence': max(restaurant_analysis_original['confidence'], restaurant_analysis_translated['confidence'])
        }
        
        print(f"[DEBUG] 意図検出統合結果 - 観光: {tourism_intent}, レストラン: {restaurant_analysis}")
        
        # Step 5: インテリジェントなレスポンス生成（日本語で生成）
        response = self._generate_intelligent_response(
            faq_result, translated_input, location_info, original_language,
            tourism_intent, restaurant_analysis, company_id, user_info
        )
        
        # Step 6: レスポンスの最終調整（スマート翻訳判定）
        print(f"[UNIFIED_CHAT] === 翻訳判定開始 ===")
        print(f"[UNIFIED_CHAT] original_language: {original_language}")
        print(f"[UNIFIED_CHAT] response_type: {response.get('response_type')}")
        print(f"[UNIFIED_CHAT] response_answer (最初の100文字): {response['answer'][:100]}...")
        
        # レスポンスタイプに関係なく、日本語コンテンツが含まれている場合は翻訳を適用
        if original_language != 'ja':
            needs_translation = self._response_needs_translation(response['answer'], original_language)
            print(f"[UNIFIED_CHAT] 翻訳必要性判定結果: {needs_translation}")
            
            if needs_translation:
                print(f"[UNIFIED_CHAT] 🔄 日本語コンテンツ検出、翻訳実行開始")
                print(f"[UNIFIED_CHAT] 翻訳前: {response['answer'][:100]}...")
                
                response['answer'] = self._translate_response_preserving_links(
                    response['answer'], 
                    original_language
                )
                print(f"[UNIFIED_CHAT] 翻訳後: {response['answer'][:100]}...")
                print(f"[UNIFIED_CHAT] ✅ 翻訳完了")
            else:
                print(f"[UNIFIED_CHAT] ⏭️ 翻訳不要と判定、スキップ")
        else:
            print(f"[UNIFIED_CHAT] 🇯🇵 日本語クエリのため翻訳スキップ")
        
        print(f"[UNIFIED_CHAT] === 翻訳判定終了 ===")
        
        # 追加情報を返す
        response['original_language'] = original_language
        response['translated_input'] = translated_input
        
        return response
    
    def _generate_localized_links(self, translated_input: str, location: Dict, intent_type: str, display_language: str) -> List[Dict]:
        """
        多言語対応リンク生成（URL日本語、ラベル多言語）
        
        Args:
            translated_input: 翻訳済み日本語テキスト
            location: 位置情報
            intent_type: 'tourism' または 'restaurant' 
            display_language: ラベル表示言語
            
        Returns:
            List[Dict]: 多言語対応リンクリスト
        """
        # URLは日本語で生成（検索精度向上）
        links = self.link_service.generate_specialized_links(
            translated_input, location, intent_type, 'ja'
        )
        
        # ラベルを表示言語に変更
        for link in links:
            original_site_type = link.get('site_type', 'Google Maps')
            link['name'] = self.link_service._get_localized_site_name(
                original_site_type, display_language
            )
        
        return links
    
    def _matches_previous_language(self, text: str, previous_language: str) -> bool:
        """
        テキストが前回と同じ言語かチェック
        
        Args:
            text: チェック対象テキスト
            previous_language: 前回の言語コード
            
        Returns:
            bool: 同一言語の可能性が高いかどうか
        """
        import re
        
        if previous_language == 'ko':
            # 韓国語: ハングル文字があるかチェック
            return bool(re.search(r'[가-힣]', text))
        elif previous_language == 'en':
            # 英語: より柔軟な条件（30%以上のアルファベット または 英語的なパターン）
            if not text:
                return False
            
            # アルファベット比率チェック（閾値を50% → 30%に緩和）
            alphabet_ratio = len(re.findall(r'[a-zA-Z]', text)) / len(text)
            
            # 英語的なパターン（英単語、疑問詞等）
            english_patterns = [
                r'\b(where|what|how|when|why|who|which|are|is|do|does|can|will|would|there)\b',
                r'\b(popular|restaurant|tourist|spot|place|food|good|best|near|around)\b',
                r'\b(the|and|or|in|on|at|to|for|with|of|from)\b'
            ]
            has_english_pattern = any(re.search(pattern, text.lower()) for pattern in english_patterns)
            
            # アルファベット30%以上 または 明確な英語パターンがある場合
            return alphabet_ratio >= 0.3 or has_english_pattern
        elif previous_language in ['zh', 'zh-cn', 'zh-tw', 'tw']:
            # 中国語: 中国語文字があるかチェック
            return bool(re.search(r'[一-龯]', text))
        elif previous_language == 'ja':
            # 日本語: ひらがな、カタカナがあるかチェック
            return bool(re.search(r'[あ-んア-ン]', text))
        
        return False
    
    def _likely_english(self, text: str) -> bool:
        """
        テキストが英語である可能性を判定（初回検出用）
        """
        if not text:
            return False
            
        import re
        text = text.strip()
        
        # アルファベット比率チェック（30%以上）
        alphabet_ratio = len(re.findall(r'[a-zA-Z]', text)) / len(text)
        
        # 強力な英語パターン（疑問詞、一般的な英単語）
        strong_english_patterns = [
            r'\b(where|what|how|when|why|who|which)\b',  # 疑問詞
            r'\b(are|is|do|does|can|will|would|there)\b',  # 基本動詞・助動詞
            r'\b(popular|restaurant|tourist|spot|place|food|good|best|near|around)\b',  # 観光・レストラン関連
            r'\b(the|and|or|in|on|at|to|for|with|of|from)\b'  # 前置詞・冠詞
        ]
        
        has_strong_pattern = any(re.search(pattern, text.lower()) for pattern in strong_english_patterns)
        
        # 日本語文字が含まれているかチェック
        has_japanese = bool(re.search(r'[あ-んア-ンー一-龯]', text))
        
        # アルファベット30%以上 AND 強い英語パターン AND 日本語文字なし
        return alphabet_ratio >= 0.3 and has_strong_pattern and not has_japanese
    
    def _response_needs_translation(self, response_text: str, target_language: str) -> bool:
        """
        レスポンステキストに翻訳が必要な日本語コンテンツが含まれているかチェック
        
        Args:
            response_text: チェック対象のレスポンステキスト
            target_language: ターゲット言語コード
            
        Returns:
            bool: 翻訳が必要かどうか
        """
        if target_language == 'ja':
            return False
        
        # 日本語特有パターンの検出
        japanese_patterns = [
            # 助詞・語尾
            'を', 'に', 'は', 'が', 'で', 'と', 'から', 'まで', 'より',
            'です', 'ます', 'である', 'だった', 'でした', 'ました',
            # 観光・レストラン関連の日本語
            '観光地', '観光スポット', '見どころ', '名所', '詳細情報', '情報源',
            'レストラン', 'グルメ情報', '美味しい', 'おすすめ', 'お店',
            '旅館', 'ホテル', 'フロント', 'スタッフ', 'お客様',
            # 一般的な日本語表現
            'について', 'に関して', 'ございます', 'いただく', 'させて',
            '周辺', '地域', '場所', '近く', '付近'
        ]
        
        # 日本語パターンの存在チェック
        has_japanese = any(pattern in response_text for pattern in japanese_patterns)
        
        if not has_japanese:
            return False
        
        # ターゲット言語特有パターンの存在チェック
        target_patterns = {
            'ko': ['정보', '관광', '맛집', '레스토랑', '자세한', '추천', '지역', '주변', '확인'],
            'en': ['information', 'tourism', 'restaurant', 'detailed', 'recommended', 'area', 'around', 'check'],
            'zh': ['信息', '旅游', '餐厅', '详细', '推荐', '地区', '周围', '确认'],
            'tw': ['資訊', '觀光', '餐廳', '詳細', '推薦', '地區', '周圍', '確認']
        }
        
        target_words = target_patterns.get(target_language, [])
        has_target_language = any(pattern in response_text for pattern in target_words)
        
        # 日本語があるがターゲット言語が不足している場合は翻訳が必要
        japanese_ratio = sum(1 for pattern in japanese_patterns if pattern in response_text)
        target_ratio = sum(1 for pattern in target_words if pattern in response_text)
        
        # 翻訳判定条件を緩和（より積極的に翻訳）
        # 条件1: 日本語パターンが存在し、ターゲット言語パターンより多い場合
        # 条件2: 日本語が3つ以上でターゲット言語が2つ以下の場合
        # 条件3: 日本語特有の助詞・語尾が含まれている場合
        japanese_grammar = sum(1 for pattern in ['を', 'に', 'は', 'が', 'です', 'ます', 'である'] if pattern in response_text)
        
        needs_translation = (
            has_japanese and (
                japanese_ratio > target_ratio or  # 日本語の方が多い
                (japanese_ratio >= 3 and target_ratio <= 2) or  # 日本語が多くターゲット言語が少ない
                japanese_grammar >= 2  # 日本語文法要素が多い
            )
        )
        
        print(f"[TRANSLATION_CHECK] === 詳細分析結果 ===")
        print(f"[TRANSLATION_CHECK] 分析対象テキスト: '{response_text[:200]}...'")
        print(f"[TRANSLATION_CHECK] テキスト長: {len(response_text)}")
        
        # 検出された日本語パターンを表示
        found_japanese = [pattern for pattern in japanese_patterns if pattern in response_text]
        print(f"[TRANSLATION_CHECK] 検出された日本語パターン: {found_japanese[:10]}...")  # 最初の10個
        
        # 検出されたターゲット言語パターンを表示  
        found_target = [pattern for pattern in target_words if pattern in response_text]
        print(f"[TRANSLATION_CHECK] 検出された{target_language}パターン: {found_target}")
        
        print(f"[TRANSLATION_CHECK] 日本語パターン検出数: {japanese_ratio}")
        print(f"[TRANSLATION_CHECK] {target_language}パターン検出数: {target_ratio}")
        print(f"[TRANSLATION_CHECK] 日本語文法要素数: {japanese_grammar}")
        print(f"[TRANSLATION_CHECK] 日本語あり: {has_japanese}")
        print(f"[TRANSLATION_CHECK] ターゲット言語あり: {has_target_language}")
        print(f"[TRANSLATION_CHECK] 判定条件1: japanese_ratio > target_ratio = {japanese_ratio > target_ratio}")
        print(f"[TRANSLATION_CHECK] 判定条件2: (japanese_ratio >= 3 and target_ratio <= 2) = {japanese_ratio >= 3 and target_ratio <= 2}")
        print(f"[TRANSLATION_CHECK] 判定条件3: japanese_grammar >= 2 = {japanese_grammar >= 2}")
        print(f"[TRANSLATION_CHECK] 最終判定: {needs_translation}")
        print(f"[TRANSLATION_CHECK] === 分析終了 ===")
        
        return needs_translation
    
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
        # 中国語の場合、大小文字変換が不要なので元のテキストも確認
        has_restaurant_keywords = any(
            keyword.lower() in text_lower or keyword in text 
            for keyword in GENERAL_RESTAURANT_KEYWORDS
        )
        
        print(f"[DEBUG] レストラン意図分析 - 元テキスト: '{text}', 小文字: '{text_lower}', キーワード検出: {has_restaurant_keywords}")
        if has_restaurant_keywords:
            matching_keywords = [k for k in GENERAL_RESTAURANT_KEYWORDS if k.lower() in text_lower or k in text]
            print(f"[DEBUG] マッチしたレストランキーワード: {matching_keywords}")
        else:
            print(f"[DEBUG] 利用可能なレストランキーワード（一部）: {GENERAL_RESTAURANT_KEYWORDS[:10]}")
        
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
            # 多言語対応ヘッダー
            hotel_meal_headers = {
                'en': "🏨 **Hotel Dining:**\n",
                'ko': "🏨 **료칸 식사에 대해서:**\n", 
                'zh': "🏨 **旅馆用餐:**\n",
                'tw': "🏨 **旅館用餐:**\n"
            }
            header = hotel_meal_headers.get(language, "🏨 **旅館のお食事について:**\n")
            
            if faq_result['confidence'] >= MEDIUM_CONFIDENCE_THRESHOLD:
                response_text = f"{header}{faq_result['answer']}"
                response_type = "internal_restaurant"
            else:
                # 多言語対応メッセージ
                front_desk_messages = {
                    'en': "For detailed dining information, please feel free to ask our front desk staff.",
                    'ko': "식사에 관한 자세한 내용은 프론트 데스크에 문의해 주세요.",
                    'zh': "有关用餐的详细信息，请随时询问前台工作人员。",
                    'tw': "有關用餐的詳細資訊，請隨時詢問櫃檯工作人員。"
                }
                message = front_desk_messages.get(language, "お食事に関する詳細は、フロントまでお気軽にお尋ねください。")
                response_text = f"{header}{message}"
                response_type = "internal_restaurant_unknown"
        
        # 外部（周辺レストラン）への質問
        elif context == 'external' and location_info:
            # FAQは関連性が低いため表示しない
            city_name = location_info.get('location', {}).get('city', '不明な地域')
            
            try:
                # Google Places APIでレストラン検索
                google_restaurants = self.google_places.search_restaurants(city_name, translated_input, language)
                
                if google_restaurants:
                    # Google Places APIの結果を使用（元言語で表示）
                    query_type_map = {
                        'ko': "레스토랑",
                        'en': "restaurant", 
                        'zh': "餐厅",
                        'tw': "餐廳"
                    }
                    query_type_translated = query_type_map.get(language, "レストラン")
                    response_text = format_google_places_response(google_restaurants, city_name, query_type_translated, language)
                    
                    # 追加の専門リンクも提供（URL日本語、ラベル多言語）
                    links = self._generate_localized_links(
                        translated_input, location_info['location'], 'restaurant', language
                    )
                    specialized_links.extend(links)
                    
                    if links:
                        # 統一された多言語対応ヘッダー
                        detail_headers = {
                            'en': "\n\n📍 **Detailed Information:**\n",
                            'ko': "\n\n📍 **자세한 정보:**\n",
                            'zh': "\n\n📍 **详细信息:**\n",
                            'tw': "\n\n📍 **詳細資訊:**\n"
                        }
                        header = detail_headers.get(language, "\n\n📍 **詳細情報:**\n")
                        response_text += header
                        
                        for link in links[:2]:
                            response_text += f"• **[{link['name']}]({link['url']})**\n"
                else:
                    # フォールバック: 従来のリンク生成（URL日本語、ラベル多言語）
                    links = self._generate_localized_links(
                        translated_input, location_info['location'], 'restaurant', language
                    )
                    specialized_links.extend(links)
                    
                    # ヘッダー（多言語対応）
                    if language == 'ko':
                        response_text = f"🍽️ **{city_name} 맛집정보:**\n"
                    elif language == 'en':
                        response_text = f"🍽️ **{city_name} Restaurant Information:**\n"
                    elif language in ['zh', 'zh-cn']:
                        response_text = f"🍽️ **{city_name}美食信息:**\n"
                    elif language in ['tw', 'zh-tw']:
                        response_text = f"🍽️ **{city_name}美食資訊:**\n"
                    else:
                        response_text = f"🍽️ **{city_name}のグルメ情報:**\n"
                    
                    for link in links[:5]:
                        response_text += f"• **[{link['name']}]({link['url']})**\n"
                
                # フッター（多言語対応）
                if language == 'ko':
                    response_text += "\n\n💡 현지 맛집을 찾고 계신다면 프론트 직원에게 문의해주세요!"
                elif language == 'en':
                    response_text += "\n\n💡 For local restaurant recommendations, please feel free to ask our front desk staff!"
                elif language in ['zh', 'zh-cn']:
                    response_text += "\n\n💡 如需当地美食推荐，请随时咨询前台工作人员!"
                elif language in ['tw', 'zh-tw']:
                    response_text += "\n\n💡 如需當地美食推薦，請隨時諮詢櫃檯工作人員!"
                else:
                    response_text += "\n\n💡 地元の美味しいお店をお探しでしたら、フロントスタッフにもお気軽にお声がけください！"
                response_type = "external_restaurant"
                
            except Exception as e:
                print(f"Google Places API エラー: {e}")
                # エラー時のフォールバック（URL日本語、ラベル多言語）
                links = self._generate_localized_links(
                    translated_input, location_info['location'], 'restaurant', language
                )
                specialized_links.extend(links)
                
                # エラー時ヘッダーの多言語対応
                error_headers = {
                    'en': f"🍽️ **{city_name} Restaurant Information:**\n",
                    'ko': f"🍽️ **{city_name} 맛집정보:**\n",
                    'zh': f"🍽️ **{city_name}美食信息:**\n",
                    'tw': f"🍽️ **{city_name}美食資訊:**\n"
                }
                header = error_headers.get(language, f"🍽️ **{city_name}のグルメ情報:**\n")
                response_text = header
                for link in links[:5]:
                    response_text += f"• **[{link['name']}]({link['url']})**\n"
                
                # エラー時フッター（多言語対応）
                error_footers = {
                    'en': "\n💡 For local restaurant recommendations, please feel free to ask our front desk staff!",
                    'ko': "\n💡 현지 맛집을 찾고 계신다면 프론트 직원에게 문의해주세요!",
                    'zh': "\n💡 如需当地美食推荐，请随时咨询前台工作人员!",
                    'tw': "\n💡 如需當地美食推薦，請隨時諮詢櫃檯工作人員!"
                }
                footer = error_footers.get(language, "\n💡 地元の美味しいお店をお探しでしたら、フロントスタッフにもお気軽にお声がけください！")
                response_text += footer
                response_type = "external_restaurant"
        
        else:
            # 位置情報なしまたは曖昧な場合（多言語対応）
            general_headers = {
                'en': "🍽️ **Dining Information:**\n",
                'ko': "🍽️ **식사 정보:**\n",
                'zh': "🍽️ **用餐信息:**\n",
                'tw': "🍽️ **用餐資訊:**\n"
            }
            response_text = general_headers.get(language, "🍽️ **お食事について:**\n")
            
            if faq_result['confidence'] >= MEDIUM_CONFIDENCE_THRESHOLD:
                hotel_meal_labels = {
                    'en': "• Hotel dining: ",
                    'ko': "• 호텔 식사: ",
                    'zh': "• 酒店用餐: ",
                    'tw': "• 酒店用餐: "
                }
                label = hotel_meal_labels.get(language, "• 館内でのお食事: ")
                response_text += f"{label}{faq_result['answer']}\n\n"
                
            location_messages = {
                'en': "• Restaurant information: Please set your location to get local restaurant information.",
                'ko': "• 주변 레스토랑 정보: 위치를 설정하시면 지역 맛집 정보를 안내해드릴 수 있습니다.",
                'zh': "• 周边餐厅信息: 请设置位置，我们将为您提供当地美食信息。",
                'tw': "• 周邊餐廳資訊: 請設置位置，我們將為您提供當地美食資訊。"
            }
            message = location_messages.get(language, "• 周辺レストラン情報: 位置情報を設定していただくと、地域のグルメ情報をご案内できます。")
            response_text += message
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
            links = self._generate_localized_links(
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
            # 多言語対応メッセージ
            no_location_messages = {
                'en': "🌸 **Tourism Information:**\nPlease set your location to get detailed tourist information.",
                'ko': "🌸 **관광정보:**\n위치를 설정하시면 더 자세한 관광정보를 안내해드릴 수 있습니다.",
                'zh': "🌸 **旅游信息:**\n请设置您的位置，我们将为您提供更详细的旅游信息。",
                'tw': "🌸 **觀光資訊:**\n請設定您的位置，我們將為您提供更詳細的觀光資訊。"
            }
            message = no_location_messages.get(language, "🌸 **観光情報について:**\n位置情報を設定していただくと、より詳しい観光情報をご案内できます。")
            
            return {
                "answer": message,
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
                # Google Places APIの結果を使用（元の言語で表示）
                response_text = format_google_places_response(google_places, city_name, "観光スポット", language)
                
                # 追加の専門リンクも提供（URL日本語、ラベル多言語）
                print(f"[DEBUG] 専門リンク生成開始: translated_input='{translated_input}', location={location_info['location']}")
                links = self._generate_localized_links(
                    translated_input, location_info['location'], 'tourism', language
                )
                print(f"[DEBUG] 専門リンク生成結果: {len(links)}件")
                for i, link in enumerate(links[:3]):
                    print(f"[DEBUG] リンク{i+1}: {link['name']} -> {link['url']}")
                
                if links:
                    # 多言語対応ヘッダー
                    detail_headers = {
                        'en': "\n\n📍 **Detailed Information:**\n",
                        'ko': "\n\n📍 **자세한 정보:**\n",
                        'zh': "\n\n📍 **详细信息:**\n",
                        'tw': "\n\n📍 **詳細資訊:**\n"
                    }
                    header = detail_headers.get(language, "\n\n📍 **詳細情報:**\n")
                    response_text += header
                    for link in links[:2]:
                        response_text += f"• **[{link['name']}]({link['url']})**\n"
                else:
                    print(f"[DEBUG] 専門リンクが生成されませんでした")
            else:
                print(f"[DEBUG] Google Places APIから結果なし、フォールバック開始")
                # フォールバック: 従来の観光情報生成（元の言語で生成）
                tourism_response, tourism_links = generate_tourism_response_by_city(
                    translated_input, city_name, language
                )
                print(f"[DEBUG] フォールバック観光レスポンス生成: '{tourism_response[:100]}...'")
                
                # 専門リンク生成（翻訳済み日本語でURL生成、ラベルは元言語）
                print(f"[DEBUG] フォールバック専門リンク生成開始: location={location_info['location']}")
                links = self._generate_localized_links(
                    translated_input, location_info['location'], 'tourism', language
                )
                print(f"[DEBUG] フォールバック専門リンク数: {len(links)}")
                for i, link in enumerate(links[:3]):
                    print(f"[DEBUG] フォールバックリンク{i+1}: {link['name']} -> {link['url']}")
                
                # ヘッダーを元言語に対応
                if language == 'ko':
                    response_text = f"🌸 **{city_name} 관광정보:**\n{tourism_response}\n\n"
                elif language == 'en':
                    response_text = f"🌸 **{city_name} Tourism Information:**\n{tourism_response}\n\n"
                elif language in ['zh', 'zh-cn']:
                    response_text = f"🌸 **{city_name}旅游信息:**\n{tourism_response}\n\n"
                elif language in ['tw', 'zh-tw']:
                    response_text = f"🌸 **{city_name}觀光資訊:**\n{tourism_response}\n\n"
                else:
                    response_text = f"🌸 **{city_name}の観光情報:**\n{tourism_response}\n\n"
                
                if links:
                    # 「詳細情報」ヘッダーを多言語対応
                    if language == 'ko':
                        response_text += "📍 **자세한 정보:**\n"
                    elif language == 'en':
                        response_text += "📍 **Detailed Information:**\n"
                    elif language in ['zh', 'zh-cn']:
                        response_text += "📍 **详细信息:**\n"
                    elif language in ['tw', 'zh-tw']:
                        response_text += "📍 **詳細資訊:**\n"
                    else:
                        response_text += "📍 **詳細情報:**\n"
                    
                    for link in links[:5]:
                        response_text += f"• **[{link['name']}]({link['url']})**\n"
                else:
                    if language == 'ko':
                        response_text += "📍 **자세한 정보를 가져올 수 없습니다**\n"
                    elif language == 'en':
                        response_text += "📍 **Unable to retrieve detailed information**\n"
                    elif language in ['zh', 'zh-cn']:
                        response_text += "📍 **无法获取详细信息**\n"
                    elif language in ['tw', 'zh-tw']:
                        response_text += "📍 **無法取得詳細資訊**\n"
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
                links = self._generate_localized_links(
                    translated_input, location_info['location'], 'tourism', language
                )
                specialized_links.extend(links)
                
            if restaurant_intent:
                links = self._generate_localized_links(
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
                    links = self._generate_localized_links(
                        translated_input, location_info['location'], 'tourism', language
                    )
                    specialized_links.extend(links)
                
                if restaurant_intent:
                    # グルメ専門リンク
                    links = self._generate_localized_links(
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
            # マークダウンリンクを含む行を保護する改良版
            lines = response_text.split('\n')
            protected_lines = []
            translatable_lines = []
            
            for i, line in enumerate(lines):
                line_strip = line.strip()
                # リンクを含む行、詳細情報行、特定の絵文字で始まる行を保護
                if (('[' in line and '](' in line) or 
                    line_strip.startswith('📍') or 
                    line_strip.startswith('•') and '[' in line or
                    line_strip.startswith('🍽️') or
                    line_strip.startswith('🌸') or
                    line_strip.startswith('💡')):
                    protected_lines.append((i, line))
                    translatable_lines.append("")  # プレースホルダー
                else:
                    translatable_lines.append(line)
            
            # 翻訳可能なコンテンツを結合（空行は除く）
            translatable_content = '\n'.join([l for l in translatable_lines if l.strip()])
            
            if translatable_content.strip():
                translated_content = self.translation_service.translate_text(
                    translatable_content, target_language, 'ja'
                )
                translated_lines = translated_content.split('\n')
            else:
                translated_lines = []
            
            # 結果を再構築
            result_lines = []
            translated_index = 0
            
            for i, original_line in enumerate(lines):
                # 保護された行があるかチェック
                protected_line = next((line for pos, line in protected_lines if pos == i), None)
                if protected_line is not None:
                    result_lines.append(protected_line)
                elif original_line.strip():
                    if translated_index < len(translated_lines):
                        result_lines.append(translated_lines[translated_index])
                        translated_index += 1
                    else:
                        result_lines.append(original_line)
                else:
                    result_lines.append(original_line)
            
            final_result = '\n'.join(result_lines)
            print(f"[TRANSLATE] リンク保護翻訳完了: '{final_result[:100]}...'")
            
            # フォールバック: 旧ロジック
            if not final_result.strip():
                detail_pattern = r'📍\s*\*?\*?詳細情報[：:]\*?\*?.*'
                detail_match = re.search(detail_pattern, response_text, re.DOTALL)
                
                if detail_match:
                    detail_section = detail_match.group(0)
                    main_content = response_text[:detail_match.start()].strip()
                else:
                    main_content = response_text
                    detail_section = ""
                
                if main_content:
                    translated_main = self.translation_service.translate_text(
                        main_content, target_language, 'ja'
                    )
                else:
                    translated_main = ""
                
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