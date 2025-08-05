"""
翻訳サービス
services/translation_service.py

Google Cloud TranslationまたはAnthropicを使用した翻訳機能
"""
import os
from typing import Dict, List, Optional, Tuple
import anthropic
from dotenv import load_dotenv

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
        
        # Google Cloud Translation クライアント
        self.google_translate_client = None
        if GOOGLE_TRANSLATE_AVAILABLE:
            try:
                # Google Cloud Translation API の初期化
                # API キーまたはサービスアカウントキーファイル
                google_credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                
                # if self.google_api_key:
                #     # API キーを使用
                #     self.google_translate_client = translate.Client(api_key=self.google_api_key)
                #     print("[TRANSLATION] Google Cloud Translation API (API Key) 初期化成功")
                if google_credentials_path:
                    # サービスアカウントファイルを使用
                    self.google_translate_client = translate.Client()
                    print("[TRANSLATION] Google Cloud Translation API (Service Account) 初期化成功")
                else:
                    print("[TRANSLATION] Google Cloud Translation API キーまたは認証ファイルが設定されていません")
                    
            except Exception as e:
                print(f"[TRANSLATION] Google Cloud Translation API 初期化エラー: {e}")
                self.google_translate_client = None
        
        # 言語コードマッピング
        self.language_mapping = {
            'ja': '日本語',
            'en': '英語', 
            'ko': '韓国語',
            'zh': '中国語',
            'zh-cn': '中国語（簡体字）',
            'zh-tw': '中国語（繁体字）'
        }
    
    def detect_language_and_translate_to_japanese(self, text: str) -> Tuple[str, str]:
        """
        ユーザー入力を言語検出し、日本語に翻訳
        
        Args:
            text: ユーザー入力テキスト
            
        Returns:
            Tuple[str, str]: (翻訳されたテキスト, 元の言語コード)
        """
        print(f"[TRANSLATION] 入力テキスト: '{text}'")
        print(f"[TRANSLATION] Google Translate利用可能: {self.google_translate_client is not None}")
        print(f"[TRANSLATION] Anthropic利用可能: {self.anthropic_client is not None}")
        
        try:
            # Google Cloud Translation API優先
            if self.google_translate_client:
                result = self._google_detect_and_translate(text)
                print(f"[TRANSLATION] Google結果: {result}")
                return result
            # フォールバック: 既存の言語検出ライブラリ
            else:
                result = self._fallback_detect_and_translate(text)
                print(f"[TRANSLATION] フォールバック結果: {result}")
                return result
                
        except Exception as e:
            print(f"[TRANSLATION] 言語検出・翻訳エラー: {e}")
            # エラー時はそのまま日本語として扱う
            return text, 'ja'
    
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
        Anthropicを使用した翻訳（既存メソッド）
        """
        if target_language == source_language:
            return text
        
        try:
            target_lang_name = self.language_mapping.get(target_language, '日本語')
            source_lang_name = self.language_mapping.get(source_language, '日本語')
            
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
            target_language: 翻訳先言語コード (ja, en, ko, zh)
            source_language: 翻訳元言語コード (デフォルト: ja)
            
        Returns:
            str: 翻訳されたテキスト
        """
        if target_language == source_language or target_language == 'ja':
            return text
        
        # 地名を保護するため、翻訳前に置換
        protected_text, location_map = self._protect_location_names(text, target_language)
        
        try:
            # Google Cloud Translation API 優先
            if self.google_translate_client:
                translated = self._google_translate_text(protected_text, target_language, source_language)
            # フォールバック: Anthropic
            elif self.anthropic_client:
                translated = self._translate_with_anthropic(protected_text, target_language, source_language)
            else:
                print("[TRANSLATION] 翻訳APIが設定されていません")
                translated = protected_text
            
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
        
        # 1. 基本地名の翻訳マッピング
        location_replacements = {
            'ソウル': {'ko': '서울', 'en': 'Seoul', 'zh': '首尔'},
            '東京': {'ko': '도쿄', 'en': 'Tokyo', 'zh': '东京'},
            '大阪': {'ko': '오사카', 'en': 'Osaka', 'zh': '大阪'},
            '京都': {'ko': '교토', 'en': 'Kyoto', 'zh': '京都'},
            '釜山': {'ko': '부산', 'en': 'Busan', 'zh': '釜山'}
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