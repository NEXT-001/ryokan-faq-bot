"""
強化された多層言語検出サービス
services/enhanced_language_detection.py

複数の手法を組み合わせて言語検出の精度を向上
"""
import re
from typing import Dict, List, Tuple, Optional
from collections import Counter
import os

# langdetectは既存依存関係
try:
    from langdetect import detect, detect_langs
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

class EnhancedLanguageDetection:
    def __init__(self):
        """多層言語検出システムの初期化（パフォーマンス最適化版）"""
        
        # パフォーマンスキャッシュ
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_size_limit = 1000
        
        # 文字パターン定義（層1: 文字分析用）
        self.char_patterns = {
            'ja': {
                'hiragana': r'[あ-ん]',
                'katakana': r'[ア-ン]',
                'kanji_japanese': r'[観光旅行温泉神社寺院公園美術館博物館レストラン食事グルメ料理おすすめ人気予約宿泊]'
            },
            'ko': {
                'hangul': r'[가-힣]',
                'korean_patterns': r'[관광여행맛집음식점식당레스토랑카페]'
            },
            'zh': {
                'simplified': r'[观光旅游景点游览餐厅美食餐饮午餐晚餐咖啡厅好吃餐馆推荐信息饮食当地美食有什么]'
            },
            'tw': {
                'traditional': r'[觀光旅遊景點遊覽餐廳美食餐飲午餐晚餐咖啡廳好吃餐館推薦資訊飲食當地美食有什麼]',
                'taiwan_specific': r'[餐廳資訊資料觀光飯店風景歷史傳統當地營業時間價格優質評價推薦環境發展經濟國際機場車站]'
            },
            'en': {
                'alphabet': r'[a-zA-Z]',
                'english_keywords': r'\b(tourism|restaurant|food|dining|sightseeing|attractions|hotel|travel)\b'
            }
        }
        
        # キーワード辞書（層2: キーワードマッチング用）
        self.keyword_dictionaries = {
            'tourism': {
                'ja': ['観光', '旅行', '見どころ', 'スポット', '名所', '観光地', '観光スポット', '見学', '散策'],
                'en': ['tourism', 'sightseeing', 'attractions', 'visit', 'tour', 'travel', 'destination'],
                'ko': ['관광', '여행', '관광지', '볼거리', '명소', '관광스폿', '구경', '여행지'],
                'zh': ['观光', '旅游', '景点', '游览', '名胜', '旅行', '景区', '参观'],
                'tw': ['觀光', '旅遊', '景點', '遊覽', '名勝', '旅行', '景區', '參觀']
            },
            'restaurant': {
                'ja': ['レストラン', '食事', 'グルメ', '料理', '飲食', '食べ物', '食堂', 'カフェ'],
                'en': ['restaurant', 'food', 'dining', 'cuisine', 'meal', 'eat', 'cafe', 'gourmet'],
                'ko': ['레스토랑', '맛집', '음식', '음식점', '식당', '카페', '식사', '그루메'],
                'zh': ['餐厅', '美食', '餐饮', '午餐', '晚餐', '咖啡厅', '好吃', '餐馆'],
                'tw': ['餐廳', '美食', '餐飲', '午餐', '晚餐', '咖啡廳', '好吃', '餐館']
            }
        }
        
        # 言語固有パターン強度
        self.pattern_weights = {
            'hiragana': 0.9,    # ひらがなは日本語確定
            'katakana': 0.8,    # カタカナも高い確度で日本語
            'hangul': 0.9,      # ハングルは韓国語確定
            'traditional': 0.7,  # 繁体字特有文字
            'simplified': 0.6,   # 簡体字
            'alphabet': 0.3,    # アルファベットは複数言語で使用
            'keywords': 0.5     # キーワードマッチング
        }
    
    def detect_language_multilayer(self, text: str) -> Dict[str, any]:
        """
        多層言語検出メイン機能（キャッシュ最適化版）
        
        Args:
            text: 分析対象テキスト
            
        Returns:
            Dict: 検出結果と信頼度情報
        """
        if not text or len(text.strip()) == 0:
            return {'language': 'ja', 'confidence': 0.0, 'method': 'default_empty'}
        
        # キャッシュチェック（高速化）
        cache_key = hash(text.strip())
        if cache_key in self._cache:
            self._cache_hits += 1
            result = self._cache[cache_key].copy()
            result['method'] += '_cached'
            return result
        
        self._cache_misses += 1
        text_stripped = text.strip()
        
        # 高速早期終了（最重要最適化）
        # 日本語文字が含まれていれば即座に日本語判定
        if re.search(r'[あ-んア-ン]', text_stripped):
            result = {'language': 'ja', 'confidence': 0.95, 'method': 'fast_japanese'}
            self._add_to_cache(cache_key, result)
            return result
        
        # 韓国語文字が含まれていれば即座に韓国語判定
        if re.search(r'[가-힣]', text_stripped):
            result = {'language': 'ko', 'confidence': 0.95, 'method': 'fast_korean'}
            self._add_to_cache(cache_key, result)
            return result
        
        # 短いテキストは簡略化処理
        if len(text_stripped) <= 5:
            result = self._handle_short_text_optimized(text_stripped)
            self._add_to_cache(cache_key, result)
            return result
        
        # 完全分析は本当に必要な場合のみ
        result = self._perform_full_analysis_optimized(text_stripped)
        self._add_to_cache(cache_key, result)
        
        return result
    
    def _add_to_cache(self, key: str, result: Dict) -> None:
        """キャッシュサイズ制限付きで結果を追加"""
        if len(self._cache) >= self._cache_size_limit:
            # 最古のエントリを削除（LRU風）
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[key] = result
    
    def clear_cache(self) -> int:
        """言語検出キャッシュをクリアして削除件数を返す"""
        cache_size = len(self._cache)
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        print(f"[LANGUAGE_DETECTION] キャッシュクリア完了: {cache_size}件削除")
        return cache_size
    
    def get_cache_stats(self) -> dict:
        """キャッシュ統計情報を取得"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        return {
            'cache_size': len(self._cache),
            'cache_limit': self._cache_size_limit,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': round(hit_rate, 2)
        }
    
    def _handle_short_text_optimized(self, text: str) -> Dict[str, any]:
        """最適化された短いテキスト処理"""
        # 繁体字特有文字チェック（高速版）
        if re.search(r'[餐廳資訊觀光]', text):
            return {'language': 'tw', 'confidence': 0.8, 'method': 'short_traditional_fast'}
        
        # 簡体字チェック（高速版）
        if re.search(r'[餐厅信息观光]', text):
            return {'language': 'zh', 'confidence': 0.8, 'method': 'short_simplified_fast'}
        
        # 英語のみ
        if re.match(r'^[a-zA-Z\s]+$', text):
            return {'language': 'en', 'confidence': 0.6, 'method': 'short_english_fast'}
        
        # デフォルト
        return {'language': 'ja', 'confidence': 0.3, 'method': 'short_default_fast'}
    
    def _perform_full_analysis_optimized(self, text: str) -> Dict[str, any]:
        """必要最小限の完全分析"""
        # 簡易版：最も重要なパターンのみチェック
        language_scores = {}
        
        # 日本語パターン（重要度高）
        japanese_score = 0.0
        if re.search(r'[観光旅行温泉神社寺院公園レストラン食事グルメ]', text):
            japanese_score += 0.5
        if re.search(r'[一-龯]', text):
            japanese_score += 0.3
        language_scores['ja'] = japanese_score
        
        # 韓国語パターン
        korean_score = 0.0
        if re.search(r'[관광여행맛집음식점식당]', text):
            korean_score += 0.5
        language_scores['ko'] = korean_score
        
        # 中国語（簡体字）パターン
        chinese_score = 0.0
        if re.search(r'[餐厅美食餐饮推荐信息观光旅游景点]', text):
            chinese_score += 0.5
        # 簡体字特有文字の検出強化
        if re.search(r'[首尔北京上海广州深圳]', text):
            chinese_score += 0.4
        language_scores['zh'] = chinese_score
        
        # 繁体字中国語パターン
        traditional_score = 0.0
        if re.search(r'[餐廳美食餐飲推薦資訊]', text):
            traditional_score += 0.5
        language_scores['tw'] = traditional_score
        
        # 英語パターン
        english_score = 0.0
        if re.search(r'\b(tourism|restaurant|food|travel|tourist|attractions|sightseeing|seoul)\b', text.lower()):
            english_score += 0.5
        # 英語でよく使われる場所名
        if re.search(r'\b(Seoul|Tokyo|Osaka|Kyoto|Fukuoka)\b', text):
            english_score += 0.3
        language_scores['en'] = english_score
        
        # 最高スコアを選択
        if not language_scores or max(language_scores.values()) == 0:
            return {'language': 'ja', 'confidence': 0.3, 'method': 'fallback_optimized'}
        
        best_language = max(language_scores, key=language_scores.get)
        best_score = language_scores[best_language]
        
        return {
            'language': best_language,
            'confidence': min(best_score, 0.9),  # 上限設定
            'method': 'optimized_pattern_match'
        }
    
    def _handle_short_text(self, text: str) -> Dict[str, any]:
        """短いテキストの特別処理"""
        text = text.strip()
        
        # 日本語文字が含まれているかチェック
        if re.search(r'[あ-んア-ン一-龯]', text):
            return {'language': 'ja', 'confidence': 0.8, 'method': 'short_japanese_chars'}
        
        # 韓国語文字チェック
        if re.search(r'[가-힣]', text):
            return {'language': 'ko', 'confidence': 0.9, 'method': 'short_hangul'}
        
        # 英語アルファベットのみ
        if re.match(r'^[a-zA-Z\s]+$', text):
            return {'language': 'en', 'confidence': 0.6, 'method': 'short_alphabet'}
        
        # 中国語文字（繁体字優先チェック）
        if re.search(r'[餐廳資訊觀光]', text):
            return {'language': 'tw', 'confidence': 0.8, 'method': 'short_traditional'}
        
        if re.search(r'[餐厅信息观光]', text):
            return {'language': 'zh', 'confidence': 0.8, 'method': 'short_simplified'}
        
        # デフォルト
        return {'language': 'ja', 'confidence': 0.3, 'method': 'short_default'}
    
    def _analyze_character_patterns(self, text: str) -> Dict[str, float]:
        """文字パターン分析（層1）"""
        scores = {}
        
        for language, patterns in self.char_patterns.items():
            lang_score = 0.0
            pattern_count = 0
            
            for pattern_name, pattern_regex in patterns.items():
                matches = len(re.findall(pattern_regex, text))
                if matches > 0:
                    weight = self.pattern_weights.get(pattern_name, 0.5)
                    # マッチ数に応じてスコア計算（上限あり）
                    pattern_score = min(matches / len(text) * 10, 1.0) * weight
                    lang_score += pattern_score
                    pattern_count += 1
            
            # 複数パターンにマッチした場合のボーナス
            if pattern_count > 1:
                lang_score *= 1.2
            
            scores[language] = min(lang_score, 1.0)
        
        return scores
    
    def _analyze_keywords(self, text: str) -> Dict[str, float]:
        """キーワード分析（層2）"""
        scores = {lang: 0.0 for lang in ['ja', 'en', 'ko', 'zh', 'tw']}
        
        # テキストを小文字に変換（英語キーワード用）
        text_lower = text.lower()
        
        for intent_type, lang_keywords in self.keyword_dictionaries.items():
            for language, keywords in lang_keywords.items():
                matches = 0
                for keyword in keywords:
                    # 大文字小文字を区別しない検索
                    if language == 'en':
                        if re.search(rf'\b{re.escape(keyword.lower())}\b', text_lower):
                            matches += 1
                    else:
                        if keyword in text:
                            matches += 1
                
                if matches > 0:
                    # マッチした キーワード数に基づくスコア
                    keyword_score = min(matches / len(keywords), 1.0) * self.pattern_weights['keywords']
                    scores[language] += keyword_score
        
        return scores
    
    def _analyze_with_langdetect(self, text: str) -> Dict[str, float]:
        """langdetectライブラリ分析（層3）"""
        if not LANGDETECT_AVAILABLE:
            return {}
        
        try:
            # 複数候補での検出
            detections = detect_langs(text)
            scores = {}
            
            for detection in detections:
                lang_code = detection.lang
                confidence = detection.prob
                
                # 言語コードの正規化
                if lang_code == 'zh-cn':
                    lang_code = 'zh'
                elif lang_code == 'zh-tw':
                    lang_code = 'tw'
                
                scores[lang_code] = confidence
            
            return scores
            
        except Exception as e:
            print(f"[LANG_DETECT] langdetectエラー: {e}")
            return {}
    
    def _integrate_analysis_results(self, text: str, results: Dict) -> Dict[str, any]:
        """分析結果統合（最終判定）"""
        
        # 各言語の総合スコア計算
        language_scores = {}
        all_languages = ['ja', 'en', 'ko', 'zh', 'tw']
        
        for lang in all_languages:
            total_score = 0.0
            score_count = 0
            
            # 文字パターンスコア（重み: 0.4）
            if results['char_analysis'].get(lang, 0) > 0:
                total_score += results['char_analysis'][lang] * 0.4
                score_count += 1
            
            # キーワードスコア（重み: 0.3）
            if results['keyword_analysis'].get(lang, 0) > 0:
                total_score += results['keyword_analysis'][lang] * 0.3
                score_count += 1
            
            # langdetectスコア（重み: 0.3）
            if results['langdetect_analysis'].get(lang, 0) > 0:
                total_score += results['langdetect_analysis'][lang] * 0.3
                score_count += 1
            
            # スコアが存在する場合のみ記録
            if score_count > 0:
                language_scores[lang] = total_score
        
        # 最高スコアの言語を選択
        if not language_scores:
            return {'language': 'ja', 'confidence': 0.1, 'method': 'fallback_default', 'debug': results}
        
        best_language = max(language_scores, key=language_scores.get)
        best_score = language_scores[best_language]
        
        # 特別な後処理ルール
        best_language, best_score = self._apply_post_processing_rules(
            text, best_language, best_score, results
        )
        
        return {
            'language': best_language,
            'confidence': best_score,
            'method': 'multilayer_integrated',
            'debug': {
                'all_scores': language_scores,
                'layer_results': results
            }
        }
    
    def _apply_post_processing_rules(self, text: str, detected_lang: str, confidence: float, results: Dict) -> Tuple[str, float]:
        """後処理ルール適用"""
        
        # ルール1: 日本語固有文字があれば日本語確定
        if re.search(r'[あ-んア-ン]', text):
            return 'ja', max(confidence, 0.9)
        
        # ルール2: 韓国語固有文字があれば韓国語確定
        if re.search(r'[가-힣]', text):
            return 'ko', max(confidence, 0.9)
        
        # ルール3: 繁体字特有文字の強い存在
        traditional_specific = len(re.findall(r'[餐廳資訊觀光風景歷史傳統當營業時間價格優質評價推薦環境]', text))
        simplified_specific = len(re.findall(r'[餐厅信息观光风景历史传统当营业时间价格优质评价推荐环境]', text))
        
        if traditional_specific > simplified_specific and traditional_specific > 0:
            return 'tw', max(confidence, 0.8)
        elif simplified_specific > 0:
            return 'zh', max(confidence, 0.8)
        
        # ルール4: 漢字のみで韓国語判定された場合は日本語に修正
        has_chinese_chars = bool(re.search(r'[一-龯]', text))
        has_korean_chars = bool(re.search(r'[가-힣]', text))
        
        if detected_lang == 'ko' and has_chinese_chars and not has_korean_chars:
            return 'ja', max(confidence * 0.8, 0.5)  # 信頼度を下げて日本語に
        
        return detected_lang, confidence


# 統合関数（既存コードとの互換性）
def enhanced_detect_language(text: str) -> str:
    """
    強化言語検出の統合関数
    
    Args:
        text: 検出対象テキスト
        
    Returns:
        str: 検出された言語コード
    """
    detector = EnhancedLanguageDetection()
    result = detector.detect_language_multilayer(text)
    
    print(f"[ENHANCED_LANG_DETECT] '{text}' → {result['language']} (信頼度: {result['confidence']:.2f}, 方法: {result['method']})")
    
    return result['language']


def enhanced_detect_language_with_confidence(text: str) -> Dict[str, any]:
    """
    信頼度情報付き言語検出
    
    Args:
        text: 検出対象テキスト
        
    Returns:
        Dict: 言語コード、信頼度、詳細情報
    """
    detector = EnhancedLanguageDetection()
    return detector.detect_language_multilayer(text)