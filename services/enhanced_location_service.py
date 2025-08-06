"""
高精度位置情報サービス
services/enhanced_location_service.py
"""
import os
import hashlib
from typing import Dict, Optional, List, Tuple
import urllib.parse
from core.database import fetch_dict_one
from services.company_service import get_company_name

class EnhancedLocationService:
    def __init__(self):
        self.location_cache = {}
        self.prefecture_mapping = self._load_prefecture_mapping()
    
    def get_accurate_location(
        self, 
        user_input_location: Optional[str] = None,
        gps_coords: Optional[Tuple[float, float]] = None,
        company_id: Optional[str] = None
    ) -> Optional[Dict]:
        """
        複数の方法で位置情報を特定
        
        Returns:
            Dict: {
                'source': str,
                'location': Dict,
                'confidence': float
            }
        """
        location_candidates = []
        
        # Method 1: ユーザー手動入力（最優先）
        if user_input_location:
            validated_location = self.validate_location_input(user_input_location)
            if validated_location:
                location_candidates.append({
                    'source': 'user_input',
                    'location': validated_location,
                    'confidence': 0.95
                })
        
        # Method 2: 会社住所からの推定
        if company_id:
            company_location = self._get_company_base_location(company_id)
            if company_location:
                location_candidates.append({
                    'source': 'company_base',
                    'location': company_location,
                    'confidence': 0.8
                })
        
        # Method 3: GPS（補完用・精度チェック付き）
        if gps_coords and self._is_gps_reasonable(gps_coords, company_id):
            gps_location = self._coords_to_location(gps_coords)
            if gps_location:
                location_candidates.append({
                    'source': 'gps',
                    'location': gps_location,
                    'confidence': 0.6
                })
        
        # 最も信頼度の高い位置情報を選択
        if location_candidates:
            best_location = max(location_candidates, key=lambda x: x['confidence'])
            return best_location
        
        return None
    
    def validate_location_input(self, location_text: str) -> Optional[Dict]:
        """
        ユーザー入力の地名を検証・正規化
        """
        # 入力テキストをクリーニング
        cleaned_text = location_text.strip()
        
        # 日本の主要都市・地域マッピング
        normalized_locations = {
            '東京': {'city':'東京都','prefecture':'東京都','region':'関東','type':'city',
                'english':'Tokyo',
                'alias':['Tokyo','도쿄','东京','東京']},
            '横浜': {'city':'横浜市','prefecture':'神奈川県','region':'関東','type':'city',
                'english':'Yokohama',
                'alias':['Yokohama','요코하마','横滨','橫濱']},
            '鎌倉': {'city':'鎌倉市','prefecture':'神奈川県','region':'関東','type':'city',
                'english':'Kamakura',
                'alias':['Kamakura','가마쿠라','镰仓','鎌倉']},
            '箱根': {'city':'箱根町','prefecture':'神奈川県','region':'関東','type':'area',
                'english':'Hakone',
                'alias':['Hakone','하코네','箱根','箱根']},
            '日光': {'city':'日光市','prefecture':'栃木県','region':'関東','type':'city',
                'english':'Nikko',
                'alias':['Nikko','닛코','日光','日光']},

            '大阪': {'city':'大阪市','prefecture':'大阪府','region':'関西','type':'city',
                'english':'Osaka',
                'alias':['Osaka','오사카','大阪','大阪']},
            '京都': {'city':'京都市','prefecture':'京都府','region':'関西','type':'city',
                'english':'Kyoto',
                'alias':['Kyoto','교토','京都','京都']},
            '嵐山': {'city':'京都市','prefecture':'京都府','region':'関西','type':'area',
                'english':'Arashiyama',
                'alias':['Arashiyama','아라시야마','岚山','嵐山']},
            '奈良': {'city':'奈良市','prefecture':'奈良県','region':'関西','type':'city',
                'english':'Nara',
                'alias':['Nara','나라','奈良','奈良']},
            '宇治': {'city':'宇治市','prefecture':'京都府','region':'関西','type':'city',
                'english':'Uji',
                'alias':['Uji','우지','宇治','宇治']},
            '神戸': {'city':'神戸市','prefecture':'兵庫県','region':'関西','type':'city',
                'english':'Kobe',
                'alias':['Kobe','고베','神户','神戶']},

            '名古屋': {'city':'名古屋市','prefecture':'愛知県','region':'中部','type':'city',
                'english':'Nagoya',
                'alias':['Nagoya','나고야','名古屋','名古屋']},
            '白川郷': {'city':'白川村','prefecture':'岐阜県','region':'中部','type':'area',
                'english':'Shirakawago',
                'alias':['Shirakawa-go','Shirakawago','시라카와고·','白川乡','白川鄉']},
            '高山': {'city':'高山市','prefecture':'岐阜県','region':'中部','type':'city',
                'english':'Takayama',
                'alias':['Takayama','다카야마','高山','高山']},
            '松本': {'city':'松本市','prefecture':'長野県','region':'中部','type':'city',
                'english':'Matsumoto',
                'alias':['Matsumoto','마츠모토','松本','松本']},
            '富良野': {'city':'富良野市','prefecture':'北海道','region':'北海道','type':'city',
                'english':'Furano',
                'alias':['Furano','후라노','富良野','富良野']},

            '札幌': {'city':'札幌市','prefecture':'北海道','region':'北海道','type':'city',
                'english':'Sapporo',
                'alias':['Sapporo','삿포로','札幌','札幌']},
            '小樽': {'city':'小樽市','prefecture':'北海道','region':'北海道','type':'city',
                'english':'Otaru',
                'alias':['Otaru','오타루','小樽','小樽']},
            '函館': {'city':'函館市','prefecture':'北海道','region':'北海道','type':'city',
                'english':'Hakodate',
                'alias':['Hakodate','하코다테','函館','函館']},
            '旭川': {'city':'旭川市','prefecture':'北海道','region':'北海道','type':'city',
                'english':'Asahikawa',
                'alias':['Asahikawa','아사히카와','旭川','旭川']},

            # 東北地域
            '仙台': {'city':'仙台市','prefecture':'宮城県','region':'東北','type':'city',
                'english':'Sendai',
                'alias':['Sendai','센다이','仙台','仙台']},
            '松島': {'city':'松島町','prefecture':'宮城県','region':'東北','type':'area',
                'english':'Matsushima',
                'alias':['Matsushima','마츠시마','松岛','松島']},

            # 九州・大分県
            '福岡': {'city':'福岡市','prefecture':'福岡県','region':'九州','type':'city',
                'english':'Fukuoka',
                'alias':['Fukuoka','후쿠오카','福冈','福岡']},
            '別府': {'city':'別府市','prefecture':'大分県','region':'九州','type':'city',
                'english':'Beppu',
                'alias':['Beppu','벳푸','别府','別府']},
            '湯布院': {'city':'由布市','prefecture':'大分県','region':'九州','type':'area',
                'english':'Yufuin',
                'alias':['Yufuin','유후인','由布院','由布院']},
            '熊本': {'city':'熊本市','prefecture':'熊本県','region':'九州','type':'city',
                'english':'Kumamoto',
                'alias':['Kumamoto','쿠마모토','熊本','熊本']},
            '阿蘇': {'city':'阿蘇市','prefecture':'熊本県','region':'九州','type':'area',
                'english':'Aso',
                'alias':['Aso','아소','阿苏','阿蘇']},
            '長崎': {'city':'長崎市','prefecture':'長崎県','region':'九州','type':'city',
                'english':'Nagasaki',
                'alias':['Nagasaki','나가사키','长崎','長崎']},
            '鹿児島': {'city':'鹿児島市','prefecture':'鹿児島県','region':'九州','type':'city',
                'english':'Kagoshima',
                'alias':['Kagoshima','가고시마','鹿儿岛','鹿兒島']},
            '屋久島': {'city':'屋久島町','prefecture':'鹿児島県','region':'九州','type':'area',
                'english':'Yakushima',
                'alias':['Yakushima','야쿠시마','屋久岛','屋久島']},
            '指宿': {'city':'指宿市','prefecture':'鹿児島県','region':'九州','type':'city',
                'english':'Ibusuki',
                'alias':['Ibusuki','이부스키','指宿','指宿']},
            '黒川温泉': {'city':'南小国町','prefecture':'熊本県','region':'九州','type':'area',
                'english':'Kurokawa Onsen',
                'alias':['Kurokawa Onsen','쿠로카와 온천','黑川温泉','黑川溫泉']},

            '広島': {'city':'広島市','prefecture':'広島県','region':'中国','type':'city',
                'english':'Hiroshima',
                'alias':['Hiroshima','히로시마','广岛','廣島']},
            '宮島': {'city':'廿日市市','prefecture':'広島県','region':'中国','type':'area',
                'english':'Miyajima',
                'alias':['Miyajima','미야지마','宫岛','宮島']},

            '金沢': {'city':'金沢市','prefecture':'石川県','region':'北陸','type':'city',
                'english':'Kanazawa',
                'alias':['Kanazawa','카나자와','金泽','金澤']},
            '高山': {'city':'高山市','prefecture':'岐阜県','region':'中部','type':'city',
                'english':'Takayama',
                'alias':['Takayama','타카야마','高山','高山']},
            '白川郷': {'city':'白川村','prefecture':'岐阜県','region':'中部','type':'area',
                'english':'Shirakawago',
                'alias':['Shirakawa-go','Shirakawago','시라카와고','白川乡','白川鄉']},
            
            '新倉山浅間公園': {'city':'富士吉田市','prefecture':'山梨県','region':'中部','type':'area',
                'english':'Arakurayama Sengen Park',
                'alias':['Arakurayama Sengen Park','Chureito Pagoda','新倉山浅間公園','忠霊塔','아라쿠라야마','아라쿠라 산']},

            '富士河口湖': {'city':'富士河口湖町','prefecture':'山梨県','region':'中部','type':'lake',
                'english':'Lake Kawaguchi',
                'alias':['Lake Kawaguchi','Kawaguchiko','河口湖','카와구치코','카와구치호']},

            '富士本栖湖': {'city':'富士河口湖町 / 富士宮市','prefecture':'山梨県 / 静岡県','region':'中部','type':'lake',
                'english':'Lake Motosu',
                'alias':['Lake Motosu','Motosuko','本栖湖','모토스코','모토스호']},
            # 必要な項目は以上で約60箇所です。
        }
        normalized_locations.update({
            # 沖縄県
            '那覇': {'city': '那覇市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'city', 'english': 'Naha', 'alias': ['Naha', '나하', '那霸', '那覇']},
            '沖縄': {'city': '沖縄市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'city', 'english': 'Okinawa', 'alias': ['Okinawa', '오키나와', '冲绳', '沖繩']},
            '石垣島': {'city': '石垣市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'area', 'english': 'Ishigaki Island', 'alias': ['Ishigaki', 'Ishigaki Island', '이시가키', '石垣岛', '石垣島']},
            '宮古島': {'city': '宮古島市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'area', 'english': 'Miyako Island', 'alias': ['Miyakojima', 'Miyako Island', '미야코지마', '宫古岛', '宮古島']},
            '恩納村': {'city': '恩納村', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'area', 'english': 'Onna', 'alias': ['Onna', '온나손', '恩纳村', '恩納村']}
        })
        
        # normalize_input関数（エイリアス逆引き機能）
        def normalize_input(inp):
            """ユーザー入力を正規化された日本語地名に変換"""
            inp_clean = inp.strip()
            for jp, data in normalized_locations.items():
                # 完全一致（日本語）
                if inp_clean == jp:
                    return jp
                # エイリアス一致（多言語対応）
                if 'alias' in data:
                    if inp_clean.lower() in [a.lower() for a in data.get('alias', [])]:
                        return jp
                    # 大文字小文字を区別しない部分一致
                    for alias in data.get('alias', []):
                        if inp_clean.lower() == alias.lower():
                            return jp
            return inp_clean
        
        # 入力を正規化
        normalized_input = normalize_input(cleaned_text)
        
        # 正規化された結果で検索
        if normalized_input in normalized_locations:
            return normalized_locations[normalized_input]
        
        # 完全一致検索（従来の処理）
        for key, location_data in normalized_locations.items():
            if key in cleaned_text:
                return location_data
        
        # 部分一致・柔軟検索
        for key, location_data in normalized_locations.items():
            if any(part in cleaned_text for part in key.split()) and len(key) > 1:
                return location_data
        
        # 都道府県名での検索
        prefecture_match = self._find_prefecture_match(cleaned_text)
        if prefecture_match:
            return prefecture_match
        
        return None
    
    def _get_region_from_prefecture(self, prefecture: str) -> str:
        """都道府県から地域を推定"""
        if not prefecture:
            return '九州'  # デフォルト
        
        region_mapping = {
            # 北海道・東北
            '北海道': '北海道', '青森県': '東北', '岩手県': '東北', '宮城県': '東北',
            '秋田県': '東北', '山形県': '東北', '福島県': '東北',
            
            # 関東
            '茨城県': '関東', '栃木県': '関東', '群馬県': '関東', '埼玉県': '関東',
            '千葉県': '関東', '東京都': '関東', '神奈川県': '関東',
            
            # 中部・北陸
            '新潟県': '中部', '富山県': '北陸', '石川県': '北陸', '福井県': '北陸',
            '山梨県': '中部', '長野県': '中部', '岐阜県': '中部', '静岡県': '中部', '愛知県': '中部',
            
            # 関西
            '三重県': '関西', '滋賀県': '関西', '京都府': '関西', '大阪府': '関西',
            '兵庫県': '関西', '奈良県': '関西', '和歌山県': '関西',
            
            # 中国・四国
            '鳥取県': '中国', '島根県': '中国', '岡山県': '中国', '広島県': '中国', '山口県': '中国',
            '徳島県': '四国', '香川県': '四国', '愛媛県': '四国', '高知県': '四国',
            
            # 九州・沖縄
            '福岡県': '九州', '佐賀県': '九州', '長崎県': '九州', '熊本県': '九州',
            '大分県': '九州', '宮崎県': '九州', '鹿児島県': '九州', '沖縄県': '沖縄'
        }
        
        return region_mapping.get(prefecture, '九州')  # デフォルトは九州

    def _get_fallback_location(self, company_id: str) -> Dict:
        """フォールバック所在地を取得（従来のロジック）"""
        try:
            # デモ会社用のデフォルト値
            if company_id == 'demo-company':
                return {
                    'city': '別府市',
                    'prefecture': '大分県',
                    'region': '九州',
                    'type': 'demo_default',
                    'address': '',
                    'postal_code': None
                }
            
            # company_idのパターンから推定
            location_hints = {
                'oita': {'city': '大分市', 'prefecture': '大分県', 'region': '九州'},
                'fukuoka': {'city': '福岡市', 'prefecture': '福岡県', 'region': '九州'},
                'tokyo': {'city': '東京都', 'prefecture': '東京都', 'region': '関東'},
                'osaka': {'city': '大阪市', 'prefecture': '大阪府', 'region': '関西'},
                'kyoto': {'city': '京都市', 'prefecture': '京都府', 'region': '関西'},
                'hyogo': {'city': '神戸市', 'prefecture': '兵庫県', 'region': '関西'}
            }
            
            for hint, location in location_hints.items():
                if hint in company_id.lower():
                    return {
                        'city': location['city'],
                        'prefecture': location['prefecture'],
                        'region': location['region'],
                        'type': 'id_based_fallback',
                        'address': '',
                        'postal_code': None
                    }
            
            # 最終フォールバック: デフォルト地域（大分県）を返す
            return {
                'city': '大分市',
                'prefecture': '大分県',
                'region': '九州',
                'type': 'default_fallback',
                'address': '',
                'postal_code': None
            }
            
        except Exception as e:
            print(f"[LOCATION_SERVICE] フォールバック処理エラー: {e}")
            # 最終的なエラー時フォールバック
            return {
                'city': '大分市',
                'prefecture': '大分県',
                'region': '九州',
                'type': 'error_fallback',
                'address': '',
                'postal_code': None
            }

    def _get_company_base_location(self, company_id: str) -> Optional[Dict]:
        """会社の基本所在地を取得（companiesテーブルから）"""
        try:
            from core.database import get_cursor
            
            # companiesテーブルから所在地情報を取得
            with get_cursor() as cursor:
                cursor.execute("""
                    SELECT prefecture, city, address, postal_code
                    FROM companies 
                    WHERE id = ?
                """, (company_id,))
                
                result = cursor.fetchone()
                
                if result and (result['prefecture'] or result['city']):
                    # データベースに所在地情報がある場合
                    prefecture = result['prefecture'] or ''
                    city = result['city'] or ''
                    address = result['address'] or ''
                    
                    # 地域の推定（都道府県から）
                    region = self._get_region_from_prefecture(prefecture)
                    
                    location_data = {
                        'city': city,
                        'prefecture': prefecture,
                        'region': region,
                        'type': 'database',
                        'address': address,
                        'postal_code': result['postal_code']
                    }
                    
                    print(f"[LOCATION_SERVICE] DB所在地取得成功: {company_id} -> {prefecture} {city}")
                    return location_data
                else:
                    print(f"[LOCATION_SERVICE] DB所在地情報なし: {company_id}, フォールバック処理")
            
            # データベースに所在地情報がない場合のフォールバック処理
            return self._get_fallback_location(company_id)
            
        except Exception as e:
            print(f"[LOCATION_SERVICE] 会社位置情報取得エラー: {e}")
            # エラー時もフォールバックを返す
            return self._get_fallback_location(company_id)
    
    def _is_gps_reasonable(self, gps_coords: Tuple[float, float], company_id: str) -> bool:
        """GPS座標の妥当性チェック"""
        lat, lng = gps_coords
        
        # 日本の緯度経度範囲チェック
        if not (20.0 <= lat <= 46.0 and 122.0 <= lng <= 154.0):
            return False
        
        # 会社所在地との距離チェック（大まかな範囲）
        company_location = self._get_company_base_location(company_id)
        if company_location:
            expected_coords = self._get_prefecture_center(company_location['prefecture'])
            if expected_coords:
                distance = self._calculate_distance(gps_coords, expected_coords)
                # 300km以内なら妥当とする
                return distance < 300
        
        return True
    
    def _coords_to_location(self, coords: Tuple[float, float]) -> Optional[Dict]:
        """座標から地名を推定（簡易版）"""
        lat, lng = coords
        
        # 日本全国の都道府県座標範囲
        city_ranges = {
            '北海道': {'lat_range': (41.0, 46.0), 'lng_range': (139.0, 146.0)},
            '青森県': {'lat_range': (40.0, 41.6), 'lng_range': (139.5, 141.7)},
            '岩手県': {'lat_range': (38.7, 40.4), 'lng_range': (140.5, 142.1)},
            '宮城県': {'lat_range': (37.8, 39.0), 'lng_range': (140.4, 141.7)},
            '秋田県': {'lat_range': (38.8, 40.7), 'lng_range': (139.4, 141.0)},
            '山形県': {'lat_range': (37.7, 39.3), 'lng_range': (139.2, 140.7)},
            '福島県': {'lat_range': (36.8, 38.0), 'lng_range': (139.2, 141.1)},
            '茨城県': {'lat_range': (35.7, 37.0), 'lng_range': (139.6, 140.9)},
            '栃木県': {'lat_range': (36.2, 37.0), 'lng_range': (139.1, 140.3)},
            '群馬県': {'lat_range': (36.0, 37.0), 'lng_range': (138.3, 139.9)},
            '埼玉県': {'lat_range': (35.7, 36.3), 'lng_range': (138.7, 139.9)},
            '千葉県': {'lat_range': (34.9, 36.1), 'lng_range': (139.7, 141.0)},
            '東京都': {'lat_range': (35.5, 35.9), 'lng_range': (138.9, 140.0)},
            '神奈川県': {'lat_range': (35.1, 35.6), 'lng_range': (138.9, 139.8)},
            '新潟県': {'lat_range': (36.7, 38.6), 'lng_range': (137.6, 140.0)},
            '富山県': {'lat_range': (36.3, 37.0), 'lng_range': (136.8, 137.9)},
            '石川県': {'lat_range': (36.0, 37.6), 'lng_range': (135.8, 137.4)},
            '福井県': {'lat_range': (35.3, 36.4), 'lng_range': (135.4, 136.8)},
            '山梨県': {'lat_range': (35.1, 36.0), 'lng_range': (138.2, 139.2)},
            '長野県': {'lat_range': (35.2, 37.0), 'lng_range': (137.3, 138.9)},
            '岐阜県': {'lat_range': (35.1, 36.6), 'lng_range': (136.0, 138.0)},
            '静岡県': {'lat_range': (34.6, 35.7), 'lng_range': (137.5, 139.2)},
            '愛知県': {'lat_range': (34.5, 35.4), 'lng_range': (136.7, 138.0)},
            '三重県': {'lat_range': (33.7, 35.2), 'lng_range': (135.8, 137.1)},
            '滋賀県': {'lat_range': (34.7, 35.7), 'lng_range': (135.7, 136.5)},
            '京都府': {'lat_range': (34.7, 35.8), 'lng_range': (135.0, 136.1)},
            '大阪府': {'lat_range': (34.2, 35.0), 'lng_range': (135.0, 136.0)},
            '兵庫県': {'lat_range': (34.2, 35.7), 'lng_range': (134.0, 135.5)},
            '奈良県': {'lat_range': (33.9, 34.8), 'lng_range': (135.6, 136.2)},
            '和歌山県': {'lat_range': (33.4, 34.5), 'lng_range': (134.9, 136.0)},
            '鳥取県': {'lat_range': (35.0, 35.7), 'lng_range': (133.1, 134.6)},
            '島根県': {'lat_range': (34.0, 36.0), 'lng_range': (131.7, 133.5)},
            '岡山県': {'lat_range': (34.3, 35.4), 'lng_range': (133.2, 134.7)},
            '広島県': {'lat_range': (34.0, 35.0), 'lng_range': (132.0, 133.6)},
            '山口県': {'lat_range': (33.7, 34.9), 'lng_range': (130.8, 132.4)},
            '徳島県': {'lat_range': (33.6, 34.4), 'lng_range': (133.5, 134.8)},
            '香川県': {'lat_range': (34.1, 34.5), 'lng_range': (133.4, 134.5)},
            '愛媛県': {'lat_range': (32.8, 34.4), 'lng_range': (132.3, 133.9)},
            '高知県': {'lat_range': (32.7, 34.0), 'lng_range': (132.5, 134.3)},
            '福岡県': {'lat_range': (33.0, 34.2), 'lng_range': (129.7, 131.3)},
            '佐賀県': {'lat_range': (33.0, 33.8), 'lng_range': (129.7, 130.8)},
            '長崎県': {'lat_range': (32.6, 34.7), 'lng_range': (128.8, 130.4)},
            '熊本県': {'lat_range': (32.0, 33.3), 'lng_range': (130.2, 131.3)},
            '大分県': {'lat_range': (32.7, 33.8), 'lng_range': (130.8, 132.0)},
            '宮崎県': {'lat_range': (31.3, 32.8), 'lng_range': (130.7, 131.9)},
            '鹿児島県': {'lat_range': (24.0, 32.1), 'lng_range': (128.9, 131.5)},
            '沖縄県': {'lat_range': (24.0, 26.9), 'lng_range': (123.0, 131.4)}
        }
        
        for prefecture, ranges in city_ranges.items():
            lat_range = ranges['lat_range']
            lng_range = ranges['lng_range']
            
            if (lat_range[0] <= lat <= lat_range[1] and 
                lng_range[0] <= lng <= lng_range[1]):
                return {
                    'prefecture': prefecture,
                    'region': self._get_region_from_prefecture(prefecture),
                    'type': 'gps_estimation'
                }
        
        return None
    
    def _load_prefecture_mapping(self) -> Dict:
        """都道府県マッピングを読み込み（全国対応）"""
        return {
            '北海道': {'region': '北海道', 'center': (43.0642, 141.3469)},
            '青森県': {'region': '東北', 'center': (40.8244, 140.7400)},
            '岩手県': {'region': '東北', 'center': (39.7036, 141.1527)},
            '宮城県': {'region': '東北', 'center': (38.2682, 140.8694)},
            '秋田県': {'region': '東北', 'center': (39.7186, 140.1024)},
            '山形県': {'region': '東北', 'center': (38.2404, 140.3633)},
            '福島県': {'region': '東北', 'center': (37.7503, 140.4676)},
            '茨城県': {'region': '関東', 'center': (36.3418, 140.4469)},
            '栃木県': {'region': '関東', 'center': (36.5657, 139.8836)},
            '群馬県': {'region': '関東', 'center': (36.3911, 139.0608)},
            '埼玉県': {'region': '関東', 'center': (35.8572, 139.6489)},
            '千葉県': {'region': '関東', 'center': (35.6074, 140.1065)},
            '東京都': {'region': '関東', 'center': (35.6762, 139.6503)},
            '神奈川県': {'region': '関東', 'center': (35.4478, 139.6425)},
            '新潟県': {'region': '中部', 'center': (37.9024, 139.0235)},
            '富山県': {'region': '中部', 'center': (36.6953, 137.2113)},
            '石川県': {'region': '中部', 'center': (36.5946, 136.6256)},
            '福井県': {'region': '中部', 'center': (36.0652, 136.2217)},
            '山梨県': {'region': '中部', 'center': (35.6640, 138.5684)},
            '長野県': {'region': '中部', 'center': (36.6513, 138.1809)},
            '岐阜県': {'region': '中部', 'center': (35.3912, 136.7223)},
            '静岡県': {'region': '中部', 'center': (34.9769, 138.3831)},
            '愛知県': {'region': '中部', 'center': (35.1802, 136.9066)},
            '三重県': {'region': '関西', 'center': (34.7303, 136.5086)},
            '滋賀県': {'region': '関西', 'center': (35.0045, 135.8686)},
            '京都府': {'region': '関西', 'center': (35.0116, 135.7681)},
            '大阪府': {'region': '関西', 'center': (34.6937, 135.5023)},
            '兵庫県': {'region': '関西', 'center': (34.6913, 135.1830)},
            '奈良県': {'region': '関西', 'center': (34.6851, 135.8048)},
            '和歌山県': {'region': '関西', 'center': (34.2261, 135.1675)},
            '鳥取県': {'region': '中国', 'center': (35.5038, 134.2381)},
            '島根県': {'region': '中国', 'center': (35.4722, 133.0506)},
            '岡山県': {'region': '中国', 'center': (34.6617, 133.9344)},
            '広島県': {'region': '中国', 'center': (34.3965, 132.4596)},
            '山口県': {'region': '中国', 'center': (34.1858, 131.4706)},
            '徳島県': {'region': '四国', 'center': (34.0658, 134.5594)},
            '香川県': {'region': '四国', 'center': (34.3401, 134.0431)},
            '愛媛県': {'region': '四国', 'center': (33.8416, 132.7658)},
            '高知県': {'region': '四国', 'center': (33.5597, 133.5311)},
            '福岡県': {'region': '九州', 'center': (33.6064, 130.4181)},
            '佐賀県': {'region': '九州', 'center': (33.2494, 130.2989)},
            '長崎県': {'region': '九州', 'center': (32.7503, 129.8677)},
            '熊本県': {'region': '九州', 'center': (32.7898, 130.7417)},
            '大分県': {'region': '九州', 'center': (33.2382, 131.6126)},
            '宮崎県': {'region': '九州', 'center': (31.9111, 131.4239)},
            '鹿児島県': {'region': '九州', 'center': (31.5602, 130.5581)},
            '沖縄県': {'region': '沖縄', 'center': (26.2124, 127.6792)}
        }
    
    def _find_prefecture_match(self, text: str) -> Optional[Dict]:
        """都道府県名一致検索"""
        for prefecture, info in self.prefecture_mapping.items():
            if prefecture in text or prefecture.replace('県', '').replace('府', '').replace('都', '') in text:
                return {
                    'prefecture': prefecture,
                    'region': info['region'],
                    'type': 'prefecture_match'
                }
        return None
    
    def _get_region_from_prefecture(self, prefecture: str) -> str:
        """都道府県から地方を取得"""
        return self.prefecture_mapping.get(prefecture, {}).get('region', '不明')
    
    def _parse_address(self, address: str) -> Optional[Dict]:
        """住所から位置情報を解析"""
        # 簡易的な住所解析
        for prefecture, info in self.prefecture_mapping.items():
            if prefecture in address:
                return {
                    'prefecture': prefecture,
                    'region': info['region'],
                    'type': 'address_parse'
                }
        return None
    
    def _get_prefecture_center(self, prefecture: str) -> Optional[Tuple[float, float]]:
        """都道府県の中心座標取得"""
        return self.prefecture_mapping.get(prefecture, {}).get('center')
    
    def _calculate_distance(self, coords1: Tuple[float, float], coords2: Tuple[float, float]) -> float:
        """2点間の距離計算（簡易版・km）"""
        import math
        
        lat1, lng1 = coords1
        lat2, lng2 = coords2
        
        # ハヴァーシン公式の簡易版
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlng/2)**2)
        
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # 地球の半径（km）
        
        return c * r
    
    def get_address_from_postal_code(self, postal_code: str) -> Optional[Dict]:
        """
        郵便番号から住所情報を取得（日本郵便API使用）
        
        Args:
            postal_code (str): 郵便番号（ハイフンありなしどちらでも可）
            
        Returns:
            Dict: 住所情報 {'postal_code', 'prefecture', 'city', 'address'}
        """
        import requests
        import re
        
        try:
            # 郵便番号の正規化（ハイフンを除去）
            clean_postal_code = re.sub(r'[^\d]', '', postal_code)
            
            if len(clean_postal_code) != 7:
                print(f"[POSTAL_CODE] 無効な郵便番号形式: {postal_code}")
                return None
            
            # ハイフン付きに変換（XXX-XXXX形式）
            formatted_postal_code = f"{clean_postal_code[:3]}-{clean_postal_code[3:]}"
            
            # 郵便番号検索API（無料）を使用
            api_url = f"https://zipcloud.ibsnet.co.jp/api/search"
            params = {'zipcode': clean_postal_code}
            
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') == 200 and data.get('results'):
                result = data['results'][0]  # 最初の結果を使用
                
                address_info = {
                    'postal_code': formatted_postal_code,
                    'prefecture': result.get('address1', ''),  # 都道府県
                    'city': result.get('address2', ''),       # 市区町村
                    'address': result.get('address3', '')     # 町域
                }
                
                print(f"[POSTAL_CODE] 住所取得成功: {formatted_postal_code} -> {address_info['prefecture']} {address_info['city']} {address_info['address']}")
                return address_info
            else:
                print(f"[POSTAL_CODE] 住所が見つかりません: {postal_code}")
                return None
                
        except requests.RequestException as e:
            print(f"[POSTAL_CODE] API通信エラー: {e}")
            return None
        except Exception as e:
            print(f"[POSTAL_CODE] 郵便番号検索エラー: {e}")
            return None