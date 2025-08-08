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
        観光スポットを検索（多言語対応・地名正規化・地理的境界制限付き）
        
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
            
            # ステップ1.5: 位置情報から地理的境界を取得
            location_data = self.location_service.validate_location_input(location)
            location_bounds = self._get_location_bounds(location_data) if location_data else None
            print(f"[GOOGLE_PLACES] 地理的境界: {location_bounds}")
            
            # ステップ2: 正規化された日本語地名でGoogle APIにリクエスト
            search_query = f"{normalized_location} 観光"
            url = f"{self.base_url}/textsearch/json"
            
            params = {
                'query': search_query,
                'language': 'ja',  # 常に日本語でリクエスト（正規化された地名のため）
                'key': self.api_key,
                'type': 'tourist_attraction'
            }
            
            # 地理的境界を追加（より正確な検索のため）
            if location_bounds:
                params['location'] = f"{location_bounds['lat']},{location_bounds['lng']}"
                params['radius'] = location_bounds.get('radius', 20000)  # 20km圏内
                print(f"[GOOGLE_PLACES] 地理的制限追加: location={params['location']}, radius={params['radius']}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 'OK':
                results = data.get('results', [])
                
                # 地理的フィルタリングを追加
                filtered_results = self._filter_results_by_location(results, location_data) if location_data else results
                print(f"[GOOGLE_PLACES] 観光地 - 地理的フィルタリング後: {len(filtered_results)}件")
                
                formatted_results = self._format_places_results(filtered_results, 'tourism')
                
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
        レストランを検索（多言語対応・地名正規化・地理的境界制限付き）
        
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
            
            # ステップ1.5: 位置情報から地理的境界を取得
            location_data = self.location_service.validate_location_input(location)
            location_bounds = self._get_location_bounds(location_data) if location_data else None
            print(f"[GOOGLE_PLACES] 地理的境界: {location_bounds}")
            
            # ステップ2: 正規化された日本語地名でGoogle APIにリクエスト
            # より具体的なクエリを生成
            if '市' not in normalized_location:
                search_query = f"{normalized_location}市 レストラン"
            else:
                search_query = f"{normalized_location} レストラン"
            url = f"{self.base_url}/textsearch/json"
            
            params = {
                'query': search_query,
                'language': 'ja',  # 常に日本語でリクエスト
                'key': self.api_key
            }
            
            # 地理的境界を追加（より正確な検索のため）
            if location_bounds:
                params['location'] = f"{location_bounds['lat']},{location_bounds['lng']}"
                params['radius'] = location_bounds.get('radius', 20000)  # 20km圏内
                print(f"[GOOGLE_PLACES] 地理的制限追加: location={params['location']}, radius={params['radius']}")
            
            # 代替クエリのリストを試行
            alternative_queries = [
                f"{normalized_location}市 レストラン",
                f"{normalized_location} 料理",
                f"{normalized_location} 飲食店",
                f"restaurant in {normalized_location}",
                normalized_location  # 地名のみ
            ]
            
            # 複数のクエリを順次試行
            for i, query_text in enumerate([search_query] + alternative_queries):
                if i > 0:  # 最初のクエリ以降
                    params['query'] = query_text
                
                print(f"[GOOGLE_PLACES] レストラン検索試行 {i+1}: {query_text}")
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                print(f"[GOOGLE_PLACES] レスポンスステータス: {data.get('status')}")
                
                if data.get('status') == 'OK':
                    results = data.get('results', [])
                    print(f"[GOOGLE_PLACES] レストラン検索結果数: {len(results)}")
                    
                    if results:  # 結果がある場合
                        # 地理的フィルタリングを追加
                        filtered_results = self._filter_results_by_location(results, location_data) if location_data else results
                        print(f"[GOOGLE_PLACES] 地理的フィルタリング後: {len(filtered_results)}件")
                        
                        if filtered_results:
                            formatted_results = self._format_places_results(filtered_results, 'restaurant')
                            print(f"[GOOGLE_PLACES] フォーマット後結果数: {len(formatted_results)}")
                            
                            # ステップ3: 結果の説明文を翻訳（店名・住所は保持）
                            if language != 'ja':
                                formatted_results = self._translate_results_descriptions(formatted_results, language)
                            
                            return formatted_results
                        else:
                            print(f"[GOOGLE_PLACES] クエリ {i+1} は地理的フィルタリング後に結果なし、次を試行")
                    else:
                        print(f"[GOOGLE_PLACES] クエリ {i+1} は結果なし、次を試行")
                else:
                    print(f"[GOOGLE_PLACES] クエリ {i+1} でAPI エラー: {data.get('status')}")
                    if i == 0:  # 最初のクエリでエラーが出た場合のみ詳細表示
                        print(f"[GOOGLE_PLACES] エラー詳細: {data}")
                
                # ZERO_RESULTSや軽微なエラーの場合は次のクエリを試行
                if data.get('status') in ['ZERO_RESULTS', 'INVALID_REQUEST']:
                    continue
                
            print(f"[GOOGLE_PLACES] すべてのクエリで結果が得られませんでした")
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
    
    def _get_location_bounds(self, location_data: Dict) -> Optional[Dict]:
        """
        地域データから地理的境界を取得
        
        Args:
            location_data: 位置情報データ
            
        Returns:
            Optional[Dict]: 緯度経度と検索半径
        """
        # 主要都市の座標データ
        city_coordinates = {
            # 関西
            '京都': {'lat': 35.0116, 'lng': 135.7681, 'radius': 15000},
            '京都市': {'lat': 35.0116, 'lng': 135.7681, 'radius': 15000},
            '大阪': {'lat': 34.6937, 'lng': 135.5023, 'radius': 15000},
            '大阪市': {'lat': 34.6937, 'lng': 135.5023, 'radius': 15000},
            '奈良': {'lat': 34.6851, 'lng': 135.8048, 'radius': 15000},
            '神戸': {'lat': 34.6901, 'lng': 135.1956, 'radius': 15000},
            
            # 関東
            '東京': {'lat': 35.6762, 'lng': 139.6503, 'radius': 25000},
            '横浜': {'lat': 35.4437, 'lng': 139.6380, 'radius': 20000},
            
            # 九州 - 主要都市
            '福岡': {'lat': 33.5904, 'lng': 130.4017, 'radius': 15000},
            '大分': {'lat': 33.2382, 'lng': 131.6126, 'radius': 15000},
            '別府': {'lat': 33.2840, 'lng': 131.4897, 'radius': 10000},
            '湯布院': {'lat': 33.2662, 'lng': 131.3641, 'radius': 8000},
            '熊本': {'lat': 32.8031, 'lng': 130.7076, 'radius': 15000},
            '鹿児島': {'lat': 31.5966, 'lng': 130.5571, 'radius': 15000},
            '佐賀': {'lat': 33.2494, 'lng': 130.2989, 'radius': 12000},
            '長崎': {'lat': 32.7503, 'lng': 129.8677, 'radius': 15000},
            '宮崎': {'lat': 31.9111, 'lng': 131.4239, 'radius': 15000},
            
            # 九州の主要温泉地
            '黒川温泉': {'lat': 33.0579, 'lng': 131.0979, 'radius': 8000},
            '嬉野温泉': {'lat': 33.1306, 'lng': 129.9964, 'radius': 6000},
            '別府温泉': {'lat': 33.2840, 'lng': 131.4897, 'radius': 8000},
            '雲仙温泉': {'lat': 32.7611, 'lng': 130.2644, 'radius': 8000},
            '霧島温泉': {'lat': 31.9306, 'lng': 130.8631, 'radius': 10000},
            '山鹿温泉': {'lat': 33.0157, 'lng': 130.6888, 'radius': 6000},
            '平山温泉': {'lat': 33.0181, 'lng': 130.6811, 'radius': 5000},
            '内牧温泉': {'lat': 32.8431, 'lng': 131.1075, 'radius': 6000},
            '南阿蘇温泉': {'lat': 32.8306, 'lng': 131.0561, 'radius': 8000},
            '武雄温泉': {'lat': 33.1944, 'lng': 129.9906, 'radius': 5000},
            '原鶴温泉': {'lat': 33.4181, 'lng': 130.7125, 'radius': 5000},
            '筑後川温泉': {'lat': 33.3431, 'lng': 130.6831, 'radius': 5000},
            '日田温泉': {'lat': 33.3225, 'lng': 130.9417, 'radius': 6000},
            '筋湯温泉': {'lat': 33.2025, 'lng': 131.2389, 'radius': 5000},
            '長湯温泉': {'lat': 33.0681, 'lng': 131.4061, 'radius': 5000},
            '久住高原温泉': {'lat': 33.0819, 'lng': 131.2881, 'radius': 8000},
            '天ヶ瀬温泉': {'lat': 33.3194, 'lng': 130.9392, 'radius': 6000},
            '杖立温泉': {'lat': 33.0650, 'lng': 131.0981, 'radius': 5000},
            '植木温泉': {'lat': 32.8156, 'lng': 130.7556, 'radius': 5000},
            '玉名温泉': {'lat': 32.9325, 'lng': 130.5706, 'radius': 5000},
            '菊池温泉': {'lat': 32.9775, 'lng': 130.8194, 'radius': 5000},
            '人吉温泉': {'lat': 32.2078, 'lng': 130.7639, 'radius': 5000},
            '湯の児温泉': {'lat': 32.3431, 'lng': 130.7194, 'radius': 5000},
            '小浜温泉': {'lat': 32.7406, 'lng': 130.1881, 'radius': 5000},
            '島原温泉': {'lat': 32.7631, 'lng': 130.3681, 'radius': 5000},
            '平戸温泉': {'lat': 33.3694, 'lng': 129.5531, 'radius': 5000},
            '鉄輪温泉': {'lat': 33.2850, 'lng': 131.4886, 'radius': 5000},
            '明礬温泉': {'lat': 33.2892, 'lng': 131.4364, 'radius': 5000},
            '湯の花温泉': {'lat': 33.2681, 'lng': 131.3681, 'radius': 5000},
            '塚原温泉': {'lat': 33.2850, 'lng': 131.3875, 'radius': 5000},
            '湯平温泉': {'lat': 33.2581, 'lng': 131.3656, 'radius': 5000},
            'えびの高原温泉': {'lat': 32.0075, 'lng': 130.8194, 'radius': 8000},
            '青島温泉': {'lat': 31.8019, 'lng': 131.4694, 'radius': 5000},
            '北郷温泉': {'lat': 31.6131, 'lng': 131.3856, 'radius': 5000},
            '砂むし温泉': {'lat': 31.2519, 'lng': 130.6444, 'radius': 5000},
            '山川温泉': {'lat': 31.1881, 'lng': 130.6431, 'radius': 5000},
            '池田湖温泉': {'lat': 31.3031, 'lng': 130.6319, 'radius': 5000},
            '日当山温泉': {'lat': 31.9244, 'lng': 130.8575, 'radius': 5000},
            '妙見温泉': {'lat': 31.9419, 'lng': 130.8581, 'radius': 5000},
            '川内高城温泉': {'lat': 31.8181, 'lng': 130.3131, 'radius': 5000},
            
            # 中部
            '名古屋': {'lat': 35.1815, 'lng': 136.9066, 'radius': 15000},
            '金沢': {'lat': 36.5944, 'lng': 136.6256, 'radius': 12000},
            
            # 北海道
            '札幌': {'lat': 43.0642, 'lng': 141.3469, 'radius': 20000},
            '函館': {'lat': 41.7687, 'lng': 140.7290, 'radius': 12000}
        }
        
        if not location_data:
            return None
            
        city = location_data.get('city', '').replace('市', '')
        
        if city in city_coordinates:
            return city_coordinates[city]
        
        # 都道府県レベルの大まかな座標
        prefecture_coordinates = {
            '京都府': {'lat': 35.0116, 'lng': 135.7681, 'radius': 30000},
            '大阪府': {'lat': 34.6937, 'lng': 135.5023, 'radius': 30000},
            '大分県': {'lat': 33.2382, 'lng': 131.6126, 'radius': 50000},
            '福岡県': {'lat': 33.5904, 'lng': 130.4017, 'radius': 50000},
            '東京都': {'lat': 35.6762, 'lng': 139.6503, 'radius': 40000},
            '佐賀県': {'lat': 33.2494, 'lng': 130.2989, 'radius': 40000},
            '長崎県': {'lat': 32.7503, 'lng': 129.8677, 'radius': 40000},
            '熊本県': {'lat': 32.7898, 'lng': 130.7417, 'radius': 50000},
            '宮崎県': {'lat': 31.9111, 'lng': 131.4239, 'radius': 50000},
            '鹿児島県': {'lat': 31.5602, 'lng': 130.5581, 'radius': 50000}
        }
        
        prefecture = location_data.get('prefecture', '')
        if prefecture in prefecture_coordinates:
            return prefecture_coordinates[prefecture]
            
        return None
    
    def _filter_results_by_location(self, results: List[Dict], location_data: Dict) -> List[Dict]:
        """
        検索結果を地理的に フィルタリング
        
        Args:
            results: Google Places API の検索結果
            location_data: 目標地域のデータ
            
        Returns:
            List[Dict]: フィルタリング後の結果
        """
        if not location_data:
            return results
            
        target_prefecture = location_data.get('prefecture', '')
        target_city = location_data.get('city', '')
        
        print(f"[GOOGLE_PLACES] フィルタリング条件: 都道府県={target_prefecture}, 市={target_city}")
        
        filtered_results = []
        
        for result in results:
            address = result.get('formatted_address', '')
            print(f"[GOOGLE_PLACES] 結果チェック: {result.get('name', '不明')} - 住所: {address}")
            
            # 住所に目標都道府県が含まれているかチェック
            if target_prefecture and target_prefecture in address:
                # より詳細な市レベルのチェック
                if target_city:
                    city_name_base = target_city.replace('市', '')
                    if city_name_base in address:
                        filtered_results.append(result)
                        print(f"[GOOGLE_PLACES] 市レベル一致で採用: {result.get('name')}")
                    else:
                        print(f"[GOOGLE_PLACES] 市レベル不一致で除外: {result.get('name')}")
                else:
                    # 市指定なしの場合は都道府県一致のみで OK
                    filtered_results.append(result)
                    print(f"[GOOGLE_PLACES] 都道府県レベル一致で採用: {result.get('name')}")
            else:
                print(f"[GOOGLE_PLACES] 都道府県不一致で除外: {result.get('name')} (対象: {target_prefecture})")
                
        print(f"[GOOGLE_PLACES] フィルタリング結果: {len(results)} → {len(filtered_results)}")
        return filtered_results

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


    def search_shopping_centers(self, location: str, query: str = "ショッピング", language: str = "ja") -> List[Dict]:
        """
        ショッピングセンターを検索（多言語対応）
        
        Args:
            location (str): 検索対象地域
            query (str): 検索クエリ
            language (str): ユーザー言語コード
            
        Returns:
            List[Dict]: ショッピング施設情報のリスト
        """
        if not self.api_key:
            print("[GOOGLE_PLACES] APIキーが設定されていません")
            return []
        
        try:
            # 地名正規化
            normalized_location = self._normalize_location_input(location)
            print(f"[GOOGLE_PLACES] ショッピング検索: '{location}' → '{normalized_location}'")
            
            # ショッピング関連の検索クエリ
            search_query = f"{normalized_location} ショッピングモール 百貨店"
            url = f"{self.base_url}/textsearch/json"
            
            params = {
                'query': search_query,
                'type': 'shopping_mall',
                'key': self.api_key,
                'language': 'ja'
            }
            
            print(f"[GOOGLE_PLACES] ショッピング検索リクエスト: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                print(f"[GOOGLE_PLACES] ショッピング検索成功: {len(data['results'])}件")
                return self._process_places_results(data['results'][:5])
            else:
                print(f"[GOOGLE_PLACES] ショッピング検索結果なし: status={data.get('status')}")
                return []
                
        except Exception as e:
            print(f"[GOOGLE_PLACES] ショッピング検索エラー: {e}")
            return []

    def search_activities(self, location: str, query: str = "体験", language: str = "ja") -> List[Dict]:
        """
        体験・アクティビティを検索（多言語対応）
        
        Args:
            location (str): 検索対象地域
            query (str): 検索クエリ
            language (str): ユーザー言語コード
            
        Returns:
            List[Dict]: アクティビティ情報のリスト
        """
        if not self.api_key:
            print("[GOOGLE_PLACES] APIキーが設定されていません")
            return []
        
        try:
            # 地名正規化
            normalized_location = self._normalize_location_input(location)
            print(f"[GOOGLE_PLACES] アクティビティ検索: '{location}' → '{normalized_location}'")
            
            # アクティビティ関連の検索クエリ
            search_query = f"{normalized_location} 体験 アクティビティ ワークショップ"
            url = f"{self.base_url}/textsearch/json"
            
            params = {
                'query': search_query,
                'type': 'point_of_interest',
                'key': self.api_key,
                'language': 'ja'
            }
            
            print(f"[GOOGLE_PLACES] アクティビティ検索リクエスト: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == 'OK' and data.get('results'):
                print(f"[GOOGLE_PLACES] アクティビティ検索成功: {len(data['results'])}件")
                return self._process_places_results(data['results'][:5])
            else:
                print(f"[GOOGLE_PLACES] アクティビティ検索結果なし: status={data.get('status')}")
                return []
                
        except Exception as e:
            print(f"[GOOGLE_PLACES] アクティビティ検索エラー: {e}")
            return []