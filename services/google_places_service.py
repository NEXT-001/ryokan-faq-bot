"""
Google Places API サービス
services/google_places_service.py

観光地・レストラン情報をGoogle Places APIから取得
多言語対応・地名正規化機能付き
"""
import os
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv
from services.enhanced_location_service import EnhancedLocationService
from services.translation_service import TranslationService

load_dotenv()

class GooglePlacesService:
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        self.base_url = 'https://maps.googleapis.com/maps/api/place'
        self.location_service = EnhancedLocationService()
        self.translation_service = TranslationService()
    
    def search_tourism_spots(self, location: str, query: str = "観光", language: str = "ja") -> List[Dict]:
        """
        観光スポットを検索（多言語対応・地名正規化）
        
        Args:
            location (str): 検索対象地域（多言語対応）
            query (str): 検索クエリ
            language (str): ユーザー言語コード
            
        Returns:
            List[Dict]: 観光スポット情報のリスト
        """
        if not self.api_key:
            print("[GOOGLE_PLACES] APIキーが設定されていません")
            return []
        
        try:
            # ステップ1: 地名を正規化（多言語→日本語）
            normalized_location = self._normalize_location_input(location)
            print(f"[GOOGLE_PLACES] 正規化: '{location}' → '{normalized_location}'")
            
            # ステップ2: 正規化された日本語地名でGoogle APIにリクエスト
            search_query = f"{normalized_location} 観光"
            url = f"{self.base_url}/textsearch/json"
            
            params = {
                'query': search_query,
                'language': 'ja',  # 常に日本語でリクエスト（正規化された地名のため）
                'key': self.api_key,
                'type': 'tourist_attraction'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK':
                results = data.get('results', [])
                formatted_results = self._format_places_results(results, 'tourism')
                
                # ステップ3: 結果の説明文を翻訳（店名・住所は保持）
                if language != 'ja':
                    formatted_results = self._translate_results_descriptions(formatted_results, language)
                
                return formatted_results
            else:
                print(f"[GOOGLE_PLACES] API エラー: {data.get('status')}")
                return []
                
        except Exception as e:
            print(f"[GOOGLE_PLACES] 観光スポット検索エラー: {e}")
            return []
    
    def search_restaurants(self, location: str, query: str = "レストラン", language: str = "ja") -> List[Dict]:
        """
        レストランを検索（多言語対応・地名正規化）
        
        Args:
            location (str): 検索対象地域（多言語対応）
            query (str): 検索クエリ
            language (str): ユーザー言語コード
            
        Returns:
            List[Dict]: レストラン情報のリスト
        """
        if not self.api_key:
            print("[GOOGLE_PLACES] APIキーが設定されていません")
            return []
        
        try:
            # ステップ1: 地名を正規化（多言語→日本語）
            normalized_location = self._normalize_location_input(location)
            print(f"[GOOGLE_PLACES] 正規化: '{location}' → '{normalized_location}'")
            
            # ステップ2: 正規化された日本語地名でGoogle APIにリクエスト
            search_query = f"{normalized_location} レストラン"
            url = f"{self.base_url}/textsearch/json"
            
            params = {
                'query': search_query,
                'language': 'ja',  # 常に日本語でリクエスト
                'key': self.api_key,
                'type': 'restaurant'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK':
                results = data.get('results', [])
                formatted_results = self._format_places_results(results, 'restaurant')
                
                # ステップ3: 結果の説明文を翻訳（店名・住所は保持）
                if language != 'ja':
                    formatted_results = self._translate_results_descriptions(formatted_results, language)
                
                return formatted_results
            else:
                print(f"[GOOGLE_PLACES] API エラー: {data.get('status')}")
                return []
                
        except Exception as e:
            print(f"[GOOGLE_PLACES] レストラン検索エラー: {e}")
            return []
    
    def _format_places_results(self, results: List[Dict], place_type: str) -> List[Dict]:
        """
        Google Places APIの結果をフォーマット
        
        Args:
            results (List[Dict]): APIの生結果
            place_type (str): 場所のタイプ ('tourism' or 'restaurant')
            
        Returns:
            List[Dict]: フォーマットされた結果
        """
        formatted_results = []
        
        for place in results[:5]:  # 上位5件
            try:
                # 基本情報
                name = place.get('name', '不明')
                address = place.get('formatted_address', '住所不明')
                rating = place.get('rating', 0)
                price_level = place.get('price_level', 0)
                
                # Google Maps URL
                place_id = place.get('place_id', '')
                maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else ""
                
                # 営業状況
                opening_hours = place.get('opening_hours', {})
                is_open = opening_hours.get('open_now', None)
                
                # タイプ別のアイコン
                if place_type == 'tourism':
                    icon = '🏛️' if 'museum' in str(place.get('types', [])) else '🌸'
                else:  # restaurant
                    icon = '🍽️'
                
                formatted_place = {
                    'name': name,
                    'address': address,
                    'rating': rating,
                    'price_level': price_level,
                    'maps_url': maps_url,
                    'is_open': is_open,
                    'icon': icon,
                    'place_type': place_type,
                    'google_place_id': place_id
                }
                
                formatted_results.append(formatted_place)
                
            except Exception as e:
                print(f"[GOOGLE_PLACES] 結果フォーマットエラー: {e}")
                continue
        
        return formatted_results
    
    def get_place_details(self, place_id: str, language: str = "ja") -> Optional[Dict]:
        """
        場所の詳細情報を取得
        
        Args:
            place_id (str): Google Places ID
            language (str): 言語コード
            
        Returns:
            Optional[Dict]: 詳細情報
        """
        if not self.api_key or not place_id:
            return None
        
        try:
            url = f"{self.base_url}/details/json"
            
            params = {
                'place_id': place_id,
                'language': language,
                'key': self.api_key,
                'fields': 'name,formatted_address,rating,opening_hours,website,formatted_phone_number,photos'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK':
                return data.get('result', {})
            else:
                print(f"[GOOGLE_PLACES] 詳細取得エラー: {data.get('status')}")
                return None
                
        except Exception as e:
            print(f"[GOOGLE_PLACES] 詳細取得エラー: {e}")
            return None
    
    def _normalize_location_input(self, location_input: str) -> str:
        """
        多言語地名入力を正規化された日本語地名に変換
        
        Args:
            location_input: ユーザー入力地名（多言語対応）
            
        Returns:
            str: 正規化された日本語地名
        """
        try:
            # location_serviceのvalidate_location_inputを使用
            location_data = self.location_service.validate_location_input(location_input)
            if location_data and 'city' in location_data:
                # '市'を除去して検索に使用
                city_name = location_data['city']
                if city_name.endswith('市'):
                    return city_name[:-1]  # '大分市' → '大分'
                return city_name
            
            # フォールバック: 入力をそのまま返す
            return location_input.strip()
            
        except Exception as e:
            print(f"[GOOGLE_PLACES] 地名正規化エラー: {e}")
            return location_input.strip()
    
    def _translate_results_descriptions(self, results: List[Dict], target_language: str) -> List[Dict]:
        """
        検索結果の説明文のみを翻訳（店名・住所は保持）
        
        Args:
            results: Google Places検索結果
            target_language: 翻訳先言語コード
            
        Returns:
            List[Dict]: 翻訳処理済み結果
        """
        if target_language == 'ja':
            return results
        
        translated_results = []
        
        for result in results:
            translated_result = result.copy()
            
            # name, address, maps_url などの固有情報は翻訳しない
            # 必要に応じて今後追加の翻訳可能フィールドを定義
            
            translated_results.append(translated_result)
        
        return translated_results

def _get_display_location_name(location: str, language: str) -> str:
    """
    地名を表示用に変換（言語に応じて適切な地名を返す）
    
    Args:
        location: 正規化された日本語地名
        language: 表示言語コード
        
    Returns:
        str: 表示用地名
    """
    # 地名マッピング（日本語 → 各言語表示名）
    location_names = {
        'ソウル': {
            'ja': 'ソウル',
            'en': 'Seoul', 
            'ko': '서울',
            'zh': '首尔'
        },
        '釜山': {
            'ja': '釜山',
            'en': 'Busan',
            'ko': '부산', 
            'zh': '釜山'
        },
        '東京': {
            'ja': '東京',
            'en': 'Tokyo',
            'ko': '도쿄',
            'zh': '东京'
        },
        '大阪': {
            'ja': '大阪',
            'en': 'Osaka',
            'ko': '오사카',
            'zh': '大阪'
        },
        '京都': {
            'ja': '京都',
            'en': 'Kyoto',
            'ko': '교토',
            'zh': '京都'
        }
    }
    
    if location in location_names and language in location_names[location]:
        return location_names[location][language]
    else:
        # マッピングにない場合はそのまま返す
        return location

def format_google_places_response(places: List[Dict], location: str, query_type: str = "観光", language: str = "ja") -> str:
    """
    Google Places APIの結果を読みやすい形式にフォーマット（多言語対応）
    
    Args:
        places (List[Dict]): Google Places検索結果
        location (str): 検索地域（正規化された日本語地名）
        query_type (str): クエリタイプ
        language (str): 表示言語コード
        
    Returns:
        str: フォーマットされたレスポンス
    """
    # 地名を表示用に変換（韓国語入力の場合）
    display_location = _get_display_location_name(location, language)
    
    if not places:
        # 多言語対応のエラーメッセージ
        error_messages = {
            'ja': f"申し訳ございません。{display_location}の{query_type}情報が見つかりませんでした。",
            'en': f"Sorry, no {query_type} information found for {display_location}.",
            'ko': f"죄송합니다. {display_location}의 {query_type} 정보를 찾을 수 없습니다.",
            'zh': f"抱歉，找不到{display_location}的{query_type}信息。"
        }
        return error_messages.get(language, error_messages['ja'])
    
    # 多言語対応のヘッダー
    headers = {
        'ja': f"📍 **{display_location}の{query_type}情報（Google）:**\n\n",
        'en': f"📍 **{query_type} Information for {display_location} (Google):**\n\n",
        'ko': f"📍 **{display_location} {query_type} 정보 (Google):**\n\n",
        'zh': f"📍 **{display_location}的{query_type}信息 (Google):**\n\n"
    }
    
    response = headers.get(language, headers['ja'])
    
    for i, place in enumerate(places[:5], 1):
        name = place['name']  # 店名は翻訳しない
        rating = place['rating']
        address = place['address']  # 住所は翻訳しない
        maps_url = place['maps_url']
        icon = place['icon']
        
        response += f"{i}. {icon} **[{name}]({maps_url})**\n"
        
        if rating > 0:
            stars = "⭐" * int(rating)
            # 評価ラベルの翻訳
            rating_labels = {
                'ja': "評価",
                'en': "Rating",
                'ko': "평가",
                'zh': "评价"
            }
            rating_label = rating_labels.get(language, rating_labels['ja'])
            response += f"   {rating_label}: {stars} ({rating:.1f})\n"
        
        response += f"   📍 {address}\n"
        
        # 営業状況の翻訳
        if place.get('is_open') is not None:
            if place['is_open']:
                status_messages = {
                    'ja': "営業中",
                    'en': "Open",
                    'ko': "영업중",
                    'zh': "营业中"
                }
            else:
                status_messages = {
                    'ja': "営業時間外",
                    'en': "Closed",
                    'ko': "영업시간 외",
                    'zh': "营业时间外"
                }
            
            status = status_messages.get(language, status_messages['ja'])
            response += f"   🕒 {status}\n"
        
        response += "\n"
    
    # 多言語対応のフッター
    footers = {
        'ja': "💡 より詳しい情報は各リンクをクリックしてご確認ください。",
        'en': "💡 Click each link for more detailed information.",
        'ko': "💡 자세한 정보는 각 링크를 클릭하여 확인해주세요.",
        'zh': "💡 请点击各个链接查看更详细的信息。"
    }
    
    response += footers.get(language, footers['ja'])
    
    return response