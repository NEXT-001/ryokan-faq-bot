"""
翻訳サービス
services/translation_service.py

Google Cloud TranslationまたはAnthropicを使用した翻訳機能
"""
import os
import re
from typing import Dict, List, Optional, Tuple
import anthropic
from dotenv import load_dotenv

# 動的インポートをモジュールレベルに移動（パフォーマンス改善）
try:
    from services.enhanced_language_detection import enhanced_detect_language_with_confidence
    ENHANCED_DETECTION_AVAILABLE = True
except ImportError:
    ENHANCED_DETECTION_AVAILABLE = False

# Google Cloud Translation V2のインポート
try:
    from google.cloud import translate_v2 as translate
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    print("[TRANSLATION] Google Cloud Translation API が利用できません。pip install google-cloud-translate で インストールしてください。")

load_dotenv()

class TranslationService:
    def __init__(self):
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        self.google_api_key = os.getenv('GOOGLE_API_KEY')  # Google Cloud Translation API Key
        
        # Anthropicクライアント
        self.anthropic_client = None
        if self.anthropic_api_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        
        # Google Cloud Translation クライアント（高速初期化版）
        self.google_translate_client = None
        self.google_available = False
        self._google_validated = False
        
        # 翻訳キャッシュ（パフォーマンス改善）
        self._translation_cache = {}
        self._cache_size_limit = 500
        
        if GOOGLE_TRANSLATE_AVAILABLE:
            try:
                # Google Cloud Translation API の初期化（ブロッキング検証なし）
                google_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                
                if google_credentials_path and os.path.exists(google_credentials_path):
                    # サービスアカウントファイルを使用（接続テストはしない）
                    self.google_translate_client = translate.Client()
                    self.google_available = True  # 初期化成功時にTrueに設定
                    print("[TRANSLATION] Google Cloud Translation API クライアント初期化完了")
                    print("[TRANSLATION] ✅ プライマリ翻訳エンジン: Google翻訳")
                        
                elif google_credentials_path:
                    print(f"[TRANSLATION] Google認証ファイルが見つかりません: {google_credentials_path}")
                    print("[TRANSLATION] ❌ Google翻訳は利用できません。Anthropic翻訳をフォールバックとして使用します。")
                else:
                    print("[TRANSLATION] GOOGLE_APPLICATION_CREDENTIALS が設定されていません")
                    print("[TRANSLATION] ❌ Google翻訳は利用できません。Anthropic翻訳をフォールバックとして使用します。")
                    
            except Exception as e:
                print(f"[TRANSLATION] Google Cloud Translation API 初期化エラー: {e}")
                self.google_translate_client = None
                self.google_available = False
        
        # 言語コードマッピング
        self.language_mapping = {
            'ja': '日本語',
            'en': '英語', 
            'ko': '韓国語',
            'zh': '中国語',
            'zh-cn': '中国語（簡体字）',
            'zh-tw': '中国語（繁体字）',
            'tw': '中国語（繁体字）'  # 独立した繁体字サポート
        }
    
    def _lazy_validate_google(self) -> bool:
        """遅延Google接続検証（初回使用時のみ）"""
        if self._google_validated:
            return self.google_available
        
        # 既に初期化時にTrueに設定されている場合は検証をスキップ
        if self.google_available and self.google_translate_client:
            print("[TRANSLATION] Google翻訳は既に利用可能です（検証スキップ）")
            self._google_validated = True
            return True
            
        if not self.google_translate_client:
            self.google_available = False
            self._google_validated = True
            print("[TRANSLATION] Google翻訳クライアントが利用できません")
            return False
        
        try:
            # 高速接続テスト
            test_result = self.google_translate_client.translate(
                'test', 
                target_language='ja',
                source_language='en'
            )
            
            self.google_available = bool(test_result and 'translatedText' in test_result)
            print(f"[TRANSLATION] Google遅延検証完了: {self.google_available}")
                   
        except Exception as e:
            print(f"[TRANSLATION] Google遅延検証エラー: {e}")
            print("[TRANSLATION] ❌ Google翻訳接続テスト失敗、Anthropic翻訳にフォールバック")
            self.google_available = False
        
        self._google_validated = True
        return self.google_available
    
    def detect_language_and_translate_to_japanese(self, text: str) -> Tuple[str, str]:
        """
        強化された言語検出とユーザー入力の日本語翻訳（キャッシュ最適化版）
        
        Args:
            text: ユーザー入力テキスト
            
        Returns:
            Tuple[str, str]: (翻訳されたテキスト, 元の言語コード)
        """
        # 翻訳キャッシュチェック（最高速化）
        cache_key = f"{text.strip()}->ja"
        if cache_key in self._translation_cache:
            print(f"[TRANSLATION] キャッシュヒット: '{text}'")
            return self._translation_cache[cache_key]
        
        print(f"[TRANSLATION] 入力テキスト: '{text}'")
        
        try:
            # 強化された言語検出を使用（モジュールレベルインポート）
            if ENHANCED_DETECTION_AVAILABLE:
                detection_result = enhanced_detect_language_with_confidence(text)
                detected_language = detection_result['language']
                confidence = detection_result['confidence']
            else:
                # フォールバック処理
                print(f"[TRANSLATION] 強化言語検出が利用できません、フォールバックします")
                return self._fallback_detect_and_translate(text)
            
            print(f"[TRANSLATION] 言語検出: {detected_language} (信頼度: {confidence:.2f}, 方法: {detection_result.get('method', 'unknown')})")
            
            # 日本語の場合は翻訳不要
            if detected_language == 'ja':
                result = (text, 'ja')
                self._add_to_translation_cache(cache_key, result)
                return result
            
            # 信頼度が低い場合のフォールバック
            if confidence < 0.4:  # 閾値を下げて高速化
                print(f"[TRANSLATION] 低信頼度({confidence:.2f})フォールバック")
                result = self._fallback_detect_and_translate(text)
                self._add_to_translation_cache(cache_key, result)
                return result
            
            # 翻訳実行（リトライ回数削減）
            translated_text = self._translate_to_japanese_fast(text, detected_language)
            
            result = (translated_text, detected_language)
            self._add_to_translation_cache(cache_key, result)
            return result
                
        except Exception as e:
            print(f"[TRANSLATION] 言語検出・翻訳エラー: {e}")
            # エラー時はフォールバック
            result = self._fallback_detect_and_translate(text)
            self._add_to_translation_cache(cache_key, result)
            return result
    
    def _add_to_translation_cache(self, key: str, result: Tuple[str, str]) -> None:
        """翻訳結果をキャッシュに追加"""
        if len(self._translation_cache) >= self._cache_size_limit:
            # 最古のエントリを削除
            oldest_key = next(iter(self._translation_cache))
            del self._translation_cache[oldest_key]
        
        self._translation_cache[key] = result
    
    def clear_cache(self) -> int:
        """翻訳キャッシュをクリアして削除件数を返す"""
        cache_size = len(self._translation_cache)
        self._translation_cache.clear()
        print(f"[TRANSLATION_SERVICE] キャッシュクリア完了: {cache_size}件削除")
        return cache_size
    
    def get_cache_stats(self) -> dict:
        """キャッシュ統計情報を取得"""
        return {
            'cache_size': len(self._translation_cache),
            'cache_limit': self._cache_size_limit
        }
    
    def _translate_to_japanese_fast(self, text: str, source_language: str) -> str:
        """
        高速日本語翻訳（品質バリデーション最小限）
        
        Args:
            text: 翻訳対象テキスト
            source_language: 元言語コード
            
        Returns:
            str: 翻訳されたテキスト
        """
        try:
            # Google翻訳優先（遅延検証）
            if self._lazy_validate_google():
                print(f"[TRANSLATION] ✅ プライマリエンジン Google翻訳使用: {source_language} → ja")
                translated = self._google_translate_text_fast(text, 'ja', source_language)
                
                # 簡易品質チェック（必須のみ）
                if translated and len(translated.strip()) > 0:
                    return translated
                    
            # Anthropicフォールバック
            if self.anthropic_client:
                print(f"[TRANSLATION] 🔄 フォールバック Anthropic翻訳使用: {source_language} → ja")
                translated = self._translate_with_anthropic(text, 'ja', source_language)
                return translated
            
            # 翻訳API利用不可
            print(f"[TRANSLATION] 翻訳API利用不可、元のテキストを返します")
            return text
                
        except Exception as e:
            print(f"[TRANSLATION] 高速翻訳エラー: {e}")
            return text
    
    def _google_translate_text_fast(self, text: str, target_language: str, source_language: str) -> str:
        """
        Google Cloud Translation API高速翻訳（検証最小限）
        """
        try:
            # 言語コード正規化
            normalized_target = 'zh-tw' if target_language == 'tw' else target_language
            normalized_source = 'zh-tw' if source_language == 'tw' else source_language
            
            result = self.google_translate_client.translate(
                text,
                target_language=normalized_target,
                source_language=normalized_source,
                format_='text'
            )
            
            translated_text = result.get('translatedText', text)
            print(f"[GOOGLE_TRANSLATE] 高速翻訳: '{text}' → '{translated_text}'")
            return translated_text
            
        except Exception as e:
            print(f"[GOOGLE_TRANSLATE] 高速翻訳エラー: {e}")
            raise e
    
    def _translate_to_japanese_with_retry(self, text: str, source_language: str, max_retries: int = 3) -> str:
        """
        リトライ機能付き日本語翻訳（品質バリデーション含む）
        
        Args:
            text: 翻訳対象テキスト
            source_language: 元言語コード
            max_retries: 最大リトライ回数
            
        Returns:
            str: 翻訳されたテキスト
        """
        for attempt in range(max_retries):
            try:
                print(f"[TRANSLATION] 翻訳試行 {attempt + 1}/{max_retries}")
                
                # 翻訳実行
                if self.google_available and self.google_translate_client:
                    translated = self._google_translate_text_validated(text, 'ja', source_language)
                elif self.anthropic_client:
                    translated = self._translate_with_anthropic(text, 'ja', source_language)
                else:
                    print(f"[TRANSLATION] 利用可能な翻訳APIがありません")
                    return text
                
                # 翻訳品質バリデーション
                if self._validate_translation_quality(text, translated, source_language, 'ja'):
                    print(f"[TRANSLATION] 翻訳成功 (試行 {attempt + 1}): '{text}' → '{translated}'")
                    return translated
                else:
                    print(f"[TRANSLATION] 品質チェック失敗 (試行 {attempt + 1})")
                    if attempt == max_retries - 1:
                        # 最後の試行でも失敗した場合、翻訳結果を返すが警告
                        print(f"[TRANSLATION] 品質は低いが翻訳結果を返します: '{translated}'")
                        return translated
                
            except Exception as e:
                print(f"[TRANSLATION] 翻訳試行 {attempt + 1} でエラー: {e}")
                if attempt == max_retries - 1:
                    # 最後の試行でエラーの場合、元のテキストを返す
                    print(f"[TRANSLATION] 全ての翻訳試行が失敗、元のテキストを返します")
                    return text
        
        return text
    
    def _google_translate_text_validated(self, text: str, target_language: str, source_language: str) -> str:
        """
        Google Cloud Translation APIでテキスト翻訳（検証付き）
        """
        try:
            # 言語コード正規化
            normalized_target = 'zh-tw' if target_language == 'tw' else target_language
            normalized_source = 'zh-tw' if source_language == 'tw' else source_language
            
            result = self.google_translate_client.translate(
                text,
                target_language=normalized_target,
                source_language=normalized_source,
                format_='text'  # HTMLタグを保護
            )
            
            translated_text = result['translatedText']
            print(f"[GOOGLE_TRANSLATE] 翻訳: {normalized_source} → {normalized_target}: '{text}' → '{translated_text}'")
            return translated_text
            
        except Exception as e:
            print(f"[GOOGLE_TRANSLATE] 翻訳エラー: {e}")
            raise e  # エラーを上位に伝播してリトライ機能を動作させる
    
    def _validate_translation_quality(self, original: str, translated: str, source_lang: str, target_lang: str) -> bool:
        """
        翻訳品質バリデーション
        
        Args:
            original: 元のテキスト
            translated: 翻訳されたテキスト
            source_lang: 元言語コード
            target_lang: 翻訳先言語コード
            
        Returns:
            bool: 翻訳品質が適格かどうか
        """
        try:
            # チェック1: 翻訳結果が空でない
            if not translated or len(translated.strip()) == 0:
                print(f"[VALIDATION] 失敗: 翻訳結果が空")
                return False
            
            # チェック2: 元のテキストと同じでない（翻訳が必要な場合）
            if original.strip() == translated.strip() and source_lang != target_lang:
                # ただし、固有名詞のみの場合は例外
                if not self._is_proper_noun_only(original):
                    print(f"[VALIDATION] 失敗: 翻訳されていない")
                    return False
            
            # チェック3: 文字数比率チェック（極端に長すぎる・短すぎる翻訳を除外）
            length_ratio = len(translated) / len(original) if len(original) > 0 else 1.0
            if length_ratio < 0.2 or length_ratio > 5.0:
                print(f"[VALIDATION] 失敗: 不適切な文字数比率 {length_ratio:.2f}")
                return False
            
            # チェック4: ターゲット言語の文字パターンチェック
            if not self._contains_expected_language_patterns(translated, target_lang):
                print(f"[VALIDATION] 失敗: ターゲット言語の文字パターンなし")
                return False
            
            # チェック5: 翻訳エラーパターンの検出
            error_patterns = [
                'translation error', 'エラー', '翻訳できません', 
                'sorry', 'unable to translate', '申し訳'
            ]
            translated_lower = translated.lower()
            for pattern in error_patterns:
                if pattern in translated_lower:
                    print(f"[VALIDATION] 失敗: エラーパターン検出: {pattern}")
                    return False
            
            print(f"[VALIDATION] 成功: 品質チェック通過")
            return True
            
        except Exception as e:
            print(f"[VALIDATION] バリデーションエラー: {e}")
            return False  # エラー時は失敗として扱う
    
    def _is_proper_noun_only(self, text: str) -> bool:
        """固有名詞のみかどうかをチェック"""
        # 簡単な固有名詞パターン（地名、人名など）
        proper_noun_patterns = [
            r'^[A-Z][a-z]+$',  # 英語固有名詞
            r'^[東京大阪京都福岡]{1,3}$',  # 日本の地名
            r'^[ソウル釜山]{2,3}$'  # 韓国の地名
        ]
        
        for pattern in proper_noun_patterns:
            if re.match(pattern, text.strip()):
                return True
        
        return False
    
    def _contains_expected_language_patterns(self, text: str, language: str) -> bool:
        """期待される言語の文字パターンが含まれているかチェック"""
        if language == 'ja':
            # 日本語: ひらがな、カタカナ、または漢字が含まれている
            return bool(re.search(r'[あ-んア-ン一-龯]', text))
        elif language == 'ko':
            # 韓国語: ハングルが含まれている
            return bool(re.search(r'[가-힣]', text))
        elif language == 'en':
            # 英語: アルファベットが含まれている
            return bool(re.search(r'[a-zA-Z]', text))
        elif language in ['zh', 'zh-cn']:
            # 簡体字中国語: 中国語文字が含まれている
            return bool(re.search(r'[一-龯]', text))
        elif language in ['tw', 'zh-tw']:
            # 繁体字中国語: 中国語文字が含まれている
            return bool(re.search(r'[一-龯]', text))
        
        # 不明な言語の場合は通す
        return True
    
    def _translate_with_quality_validation(self, text: str, target_language: str, source_language: str, max_retries: int = 2) -> str:
        """
        品質バリデーション付き翻訳
        
        Args:
            text: 翻訳対象テキスト
            target_language: 翻訳先言語コード
            source_language: 翻訳元言語コード
            max_retries: 最大リトライ回数
            
        Returns:
            str: 翻訳されたテキスト
        """
        for attempt in range(max_retries):
            try:
                # 翻訳実行
                if self.google_available and self.google_translate_client:
                    translated = self._google_translate_text_validated(text, target_language, source_language)
                elif self.anthropic_client:
                    translated = self._translate_with_anthropic(text, target_language, source_language)
                else:
                    print(f"[TRANSLATION] 利用可能な翻訳APIがありません")
                    return text
                
                # 品質バリデーション
                if self._validate_translation_quality(text, translated, source_language, target_language):
                    return translated
                else:
                    print(f"[TRANSLATION] 品質チェック失敗 (試行 {attempt + 1})")
                    if attempt == max_retries - 1:
                        print(f"[TRANSLATION] 品質は低いが翻訳結果を使用: '{translated}'")
                        return translated
                
            except Exception as e:
                print(f"[TRANSLATION] 翻訳試行 {attempt + 1} でエラー: {e}")
                if attempt == max_retries - 1:
                    print(f"[TRANSLATION] 全ての翻訳試行が失敗、元のテキストを返します")
                    return text
        
        return text
    
    def _google_detect_and_translate(self, text: str) -> Tuple[str, str]:
        """
        Google Cloud Translation APIを使用した検出・翻訳
        """
        try:
            # 1. 言語検出
            detection = self.google_translate_client.detect_language(text)
            detected_language = detection['language']
            confidence = detection.get('confidence', 0.0)
            
            print(f"[GOOGLE_TRANSLATE] 検出言語: {detected_language} (信頼度: {confidence})")
            
            # 2. 日本語でない場合は翻訳
            if detected_language != 'ja':
                result = self.google_translate_client.translate(
                    text, 
                    target_language='ja',
                    source_language=detected_language
                )
                translated_text = result['translatedText']
                print(f"[GOOGLE_TRANSLATE] 翻訳: '{text}' → '{translated_text}'")
                return translated_text, detected_language
            else:
                return text, 'ja'
                
        except Exception as e:
            print(f"[GOOGLE_TRANSLATE] エラー: {e}")
            return text, 'ja'
    
    def _fallback_detect_and_translate(self, text: str) -> Tuple[str, str]:
        """
        フォールバック: 既存のlangdetect + Anthropic翻訳
        """
        try:
            # 既存の言語検出ロジックを使用
            from services.tourism_service import detect_language
            detected_language = detect_language(text)
            print(f"[FALLBACK] 検出言語: {detected_language}")
            
            if detected_language != 'ja':
                if self.anthropic_client:
                    # Anthropicで翻訳
                    translated_text = self._translate_with_anthropic(text, 'ja', detected_language)
                    print(f"[FALLBACK] Anthropic翻訳: '{text}' → '{translated_text}'")
                    return translated_text, detected_language
                else:
                    # 翻訳APIが無い場合は、韓国語キーワードがそのまま処理されるようにする
                    print(f"[FALLBACK] 翻訳APIなし、元のテキストを返す（多言語キーワード対応）")
                    return text, detected_language
            else:
                return text, detected_language
                
        except Exception as e:
            print(f"[FALLBACK_TRANSLATE] エラー: {e}")
            return text, 'ja'
    
    def _translate_with_anthropic(self, text: str, target_language: str, source_language: str) -> str:
        """
        Anthropicを使用した翻訳（繁体字対応強化）
        """
        if target_language == source_language:
            return text
        
        try:
            # tw コードの対応
            display_target = 'zh-tw' if target_language == 'tw' else target_language
            display_source = 'zh-tw' if source_language == 'tw' else source_language
            
            target_lang_name = self.language_mapping.get(display_target, '日本語')
            source_lang_name = self.language_mapping.get(display_source, '日本語')
            
            prompt = f"""以下の{source_lang_name}のテキストを{target_lang_name}に翻訳してください。

翻訳対象テキスト:
{text}

重要：「翻訳結果:」などの前置きは一切つけず、翻訳したテキストのみを出力してください。"""

            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            translated_text = response.content[0].text.strip()
            
            # 不要な前置きを除去
            prefixes_to_remove = [
                "翻訳結果:", "번역 결과:", "Translation result:", "翻译结果:",
                "翻訳結果：", "번역 결과：", "Translation result：", "翻译结果："
            ]
            
            for prefix in prefixes_to_remove:
                if translated_text.startswith(prefix):
                    translated_text = translated_text[len(prefix):].strip()
                    break
            
            return translated_text
            
        except Exception as e:
            print(f"[ANTHROPIC_TRANSLATE] エラー: {e}")
            return text
    
    def translate_text(self, text: str, target_language: str, source_language: str = 'ja') -> str:
        """
        テキストを翻訳（地名保護機能付き）
        
        Args:
            text: 翻訳対象テキスト
            target_language: 翻訳先言語コード (ja, en, ko, zh, tw)
            source_language: 翻訳元言語コード (デフォルト: ja)
            
        Returns:
            str: 翻訳されたテキスト
        """
        if target_language == source_language or target_language == 'ja':
            return text
        
        # tw コードを zh-tw に正規化
        normalized_target = 'zh-tw' if target_language == 'tw' else target_language
        normalized_source = 'zh-tw' if source_language == 'tw' else source_language
        
        # 地名を保護するため、翻訳前に置換
        protected_text, location_map = self._protect_location_names(text, target_language)
        
        try:
            # リトライ機能付き翻訳（品質バリデーション含む）
            translated = self._translate_with_quality_validation(
                protected_text, normalized_target, normalized_source
            )
            
            # 地名を元に戻す
            final_text = self._restore_location_names(translated, location_map)
            return final_text
                
        except Exception as e:
            print(f"[TRANSLATION] 翻訳エラー: {e}")
            return text
    
    def _protect_location_names(self, text: str, target_language: str) -> tuple[str, dict]:
        """地名・施設名・住所を翻訳から保護"""
        import re
        
        protected_text = text
        location_map = {}
        
        # 1. 基本地名の翻訳マッピング（繁体字サポート追加）
        location_replacements = {
            'ソウル': {'ko': '서울', 'en': 'Seoul', 'zh': '首尔', 'zh-tw': '首爾', 'tw': '首爾'},
            '東京': {'ko': '도쿄', 'en': 'Tokyo', 'zh': '东京', 'zh-tw': '東京', 'tw': '東京'},
            '大阪': {'ko': '오사카', 'en': 'Osaka', 'zh': '大阪', 'zh-tw': '大阪', 'tw': '大阪'},
            '京都': {'ko': '교토', 'en': 'Kyoto', 'zh': '京都', 'zh-tw': '京都', 'tw': '京都'},
            '釜山': {'ko': '부산', 'en': 'Busan', 'zh': '釜山', 'zh-tw': '釜山', 'tw': '釜山'},
            '別府': {'ko': '벳푸', 'en': 'Beppu', 'zh': '别府', 'zh-tw': '別府', 'tw': '別府'},
            '福岡': {'ko': '후쿠오카', 'en': 'Fukuoka', 'zh': '福冈', 'zh-tw': '福岡', 'tw': '福岡'},
            '湯布院': {'ko': '유후인', 'en': 'Yufuin', 'zh': '由布院', 'zh-tw': '湯布院', 'tw': '湯布院'}
        }
        
        for jp_name, translations in location_replacements.items():
            if jp_name in text and target_language in translations:
                placeholder = f"§§LOC{len(location_map)}§§"
                protected_text = protected_text.replace(jp_name, placeholder)
                location_map[placeholder] = translations[target_language]
        
        # 2. 日本の住所パターンを保護（〒郵便番号、県市区町村、丁目番地など）
        address_patterns = [
            r'〒\d{3}-\d{4}[^、\n]*',  # 郵便番号から始まる住所
            r'日本、[^、\n]*',          # 「日本、」から始まる住所
            r'[都道府県市区町村]\d+[丁目番地号][\d\-−]*',  # 丁目番地パターン
            r'福岡県[^、\n]*',          # 具体的な県名パターン
            r'東京都[^、\n]*',
            r'大阪府[^、\n]*',
            r'京都府[^、\n]*'
        ]
        
        for pattern in address_patterns:
            matches = re.finditer(pattern, protected_text)
            for match in matches:
                address = match.group(0)
                placeholder = f"§§ADR{len(location_map)}§§"
                protected_text = protected_text.replace(address, placeholder)
                location_map[placeholder] = address  # 住所はそのまま保持
        
        # 3. 施設名パターンを保護（具体的な施設名を優先）
        facility_patterns = [
            r'[一-龯ひらがなカタカナａ-ｚＡ-Ｚー・]+(?:公園|タワー|城|寺|神社|館|センター|ビル|モール|空港|駅|橋|川|山|島|温泉|ホテル|旅館)',
            r'キャナルシティ[一-龯ひらがなカタカナー・]*',  # キャナルシティ博多など
            r'マリンワールド[一-龯ひらがなカタカナー・]*',  # マリンワールド海の中道など
            r'[一-龯]+町家[一-龯ひらがなカタカナー・]*',    # 博多町家ふるさと館など
            r'大濠公園',  # 具体的な施設名
            r'福岡タワー',
            r'博多町家ふるさと館',
        ]
        
        for pattern in facility_patterns:
            matches = re.finditer(pattern, protected_text)
            for match in matches:
                facility = match.group(0)
                placeholder = f"§§FAC{len(location_map)}§§"
                protected_text = protected_text.replace(facility, placeholder)
                location_map[placeholder] = facility  # 施設名はそのまま保持
        
        return protected_text, location_map
    
    def _restore_location_names(self, text: str, location_map: dict) -> str:
        """保護された地名を元に戻す（依存関係を考慮した順序で復元）"""
        restored_text = text
        
        # 複数回復元を実行して、ネストされたプレースホルダーも解決
        max_iterations = 5  # 無限ループを防ぐ
        for iteration in range(max_iterations):
            changes_made = False
            for placeholder, actual_name in location_map.items():
                if placeholder in restored_text:
                    restored_text = restored_text.replace(placeholder, actual_name)
                    changes_made = True
            
            # 変更がなければ復元完了
            if not changes_made:
                break
        
        return restored_text
    
    def _google_translate_text(self, text: str, target_language: str, source_language: str) -> str:
        """
        Google Cloud Translation APIでテキスト翻訳
        """
        try:
            result = self.google_translate_client.translate(
                text,
                target_language=target_language,
                source_language=source_language,
                format_='text'  # HTMLタグを保護
            )
            
            translated_text = result['translatedText']
            print(f"[GOOGLE_TRANSLATE] 翻訳: {source_language} → {target_language}")
            return translated_text
            
        except Exception as e:
            print(f"[GOOGLE_TRANSLATE] 翻訳エラー: {e}")
            # フォールバック: Anthropic
            if self.anthropic_client:
                return self._translate_with_anthropic(text, target_language, source_language)
            return text
    
    def translate_places_results(self, places_results: List[Dict], target_language: str) -> List[Dict]:
        """
        Google Places結果の説明文のみ翻訳（店名・住所は保持）
        
        Args:
            places_results: Google Places API結果リスト
            target_language: 翻訳先言語コード
            
        Returns:
            List[Dict]: 翻訳処理済み結果
        """
        if target_language == 'ja':
            return places_results
        
        translated_results = []
        
        for place in places_results:
            translated_place = place.copy()
            
            # 店名・住所・URLは翻訳しない（そのまま保持）
            # name, address, maps_url, google_place_idは保持
            
            # 説明文がある場合のみ翻訳
            if 'description' in place:
                translated_place['description'] = self.translate_text(
                    place['description'], target_language
                )
            
            translated_results.append(translated_place)
        
        return translated_results
    
    def translate_tourism_response(self, response_text: str, target_language: str) -> str:
        """
        観光情報レスポンスを翻訳（リンクと固有名詞は保持）
        
        Args:
            response_text: 翻訳対象レスポンス
            target_language: 翻訳先言語コード
            
        Returns:
            str: 翻訳されたレスポンス
        """
        if target_language == 'ja':
            return response_text
        
        return self.translate_text(response_text, target_language)
    
    def get_language_display_name(self, language_code: str) -> str:
        """言語コードから表示名を取得"""
        return self.language_mapping.get(language_code, language_code)