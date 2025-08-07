"""
専門サイトリンク生成サービス
services/specialized_link_service.py
"""
import urllib.parse
from typing import Dict, List, Optional
import pandas as pd
import os

class SpecializedLinkService:
    def __init__(self):
        # 翻訳サービスのインポート
        try:
            from services.translation_service import TranslationService
            self.translation_service = TranslationService()
        except ImportError:
            print("[SPECIALIZED_LINK] 翻訳サービスが利用できません")
            self.translation_service = None
        
        # 観光情報専門サイト（信頼度順）
        self.tourism_sites = [
            {
                'name': 'じゃらんnet',
                'base_url': 'https://www.jalan.net',
                'search_pattern': '/kankou/{prefecture_code}/?keyword={query}',
                'strength': ['観光地', '温泉', '体験'],
                'languages': ['ja'],
                'priority': 1
            },
            {
                'name': 'Google Maps',
                'base_url': 'https://www.google.com',
                'search_pattern': '/maps/search/{query}+{location}',
                'strength': ['地図情報', '営業時間', 'ルート案内'],
                'languages': ['ja', 'en', 'ko', 'zh', 'tw'],
                'priority': 2
            }
        ]
        
        # グルメ専門サイト
        self.restaurant_sites = [
            {
                'name': 'ぐるなび',
                'base_url': 'https://r.gnavi.co.jp',
                'search_pattern': '/area/jp/rs/?fw={keyword}&area={area}',
                'strength': ['レストラン予約', '地域グルメ'],
                'languages': ['ja', 'en', 'ko', 'zh', 'tw'],
                'priority': 1
            },
            {
                'name': '食べログ',
                'base_url': 'https://tabelog.com',
                'search_pattern': '/rstLst/?word={query}&LstRange={area}',
                'strength': ['口コミ', '評価', 'ランキング'],
                'languages': ['ja'],
                'priority': 2
            }
        ]
        
        # 地域コードマッピング
        self.area_codes = self._load_area_codes()
        
        # じゃらん都道府県コード
        self.jalan_prefecture_codes = self._load_jalan_codes()
    
    def generate_specialized_links(
        self, 
        query: str, 
        location: Dict, 
        intent_type: str, 
        language: str = 'ja'
    ) -> List[Dict]:
        """
        専門サイトリンクを生成
        
        Args:
            query: 検索クエリ
            location: 位置情報
            intent_type: 'tourism' または 'restaurant'
            language: 言語コード
            
        Returns:
            List[Dict]: リンク情報のリスト
        """
        links = []
        
        # 韓国の都市の場合は国際対応サイトのみ
        if location.get('region') == '韓国':
            print(f"[SPECIALIZED_LINK] 韓国都市のため国際対応サイトのみを使用")
            if intent_type == 'tourism':
                sites = [site for site in self.tourism_sites 
                        if site['name'] in ['Google Maps'] 
                        and language in site['languages']]
            elif intent_type == 'restaurant':
                sites = [site for site in self.restaurant_sites 
                        if site['name'] in ['Google Maps'] 
                        and language in site['languages']]
            else:
                # 混合の場合
                tourism_sites = [site for site in self.tourism_sites 
                               if site['name'] in ['Google Maps'] 
                               and language in site['languages']]
                restaurant_sites = [site for site in self.restaurant_sites 
                                   if site['name'] in ['Google Maps'] 
                                   and language in site['languages']]
                sites = sorted(tourism_sites + restaurant_sites, key=lambda x: x['priority'])
        else:
            # 対象サイトを選択（日本国内）
            if intent_type == 'tourism':
                sites = [site for site in self.tourism_sites if language in site['languages']]
            elif intent_type == 'restaurant':
                sites = [site for site in self.restaurant_sites if language in site['languages']]
            else:
                # 混合の場合は両方
                tourism_sites = [site for site in self.tourism_sites if language in site['languages']]
                restaurant_sites = [site for site in self.restaurant_sites if language in site['languages']]
                sites = sorted(tourism_sites + restaurant_sites, key=lambda x: x['priority'])
        
        # 上位5サイトのリンクを生成
        for site in sites[:5]:
            try:
                url = self._build_search_url(site, query, location, language)
                if url:
                    links.append({
                        'name': self._get_localized_site_name(site['name'], language),
                        'url': url,
                        'description': f"{', '.join(site['strength'])}情報",
                        'site_type': site['name'],
                        'priority': site['priority']
                    })
            except Exception as e:
                print(f"リンク生成エラー ({site['name']}): {e}")
                continue
        
        return links
    
    def _build_search_url(self, site: Dict, query: str, location: Dict, language: str) -> Optional[str]:
        """検索URLを構築"""
        print(f"[SPECIALIZED_LINK] URL構築開始 - site: {site['name']}, location: {location}")
        try:
            base_url = site['base_url']
            pattern = site['search_pattern']
            
            # 外国語のクエリを日本語に翻訳（URL用）
            japanese_query = self._translate_query_to_japanese(query, language)
            print(f"[SPECIALIZED_LINK] URL用クエリ翻訳: '{query}' → '{japanese_query}'")
            
            # 翻訳されたクエリをURLエンコード
            encoded_query = urllib.parse.quote(japanese_query)
            
            # 位置情報から地域コードを取得
            area_code = self._get_area_code(location, site['name'])
            print(f"[SPECIALIZED_LINK] area_code: {area_code} for {site['name']}")
            
            # 韓国の都市の場合は日本の観光サイトをスキップ
            if location.get('region') == '韓国' and site['name'] in ['じゃらんnet', 'ぐるなび', '食べログ', 'TripAdvisor', 'るるぶ']:
                print(f"[SPECIALIZED_LINK] 韓国の都市のため{site['name']}をスキップ")
                return None
            
            # パターンに応じてURL生成
            if site['name'] == 'じゃらんnet':
                return self._build_jalan_url(encoded_query, location)
            elif site['name'] == 'Google Maps':
                return self._build_google_maps_url(encoded_query, location)
            elif site['name'] == 'ぐるなび':
                return self._build_gurunavi_url(encoded_query, location)
            elif site['name'] == '食べログ':
                return self._build_tabelog_url(encoded_query, location)
            else:
                # 汎用パターン
                url = base_url + pattern.format(
                    query=encoded_query,
                    keyword=encoded_query,
                    area=area_code or 'japan',
                    area_code=area_code or '01',
                    location=location.get('city', 'japan'),
                    prefecture_code=area_code or '01',
                    location_id='japan'
                )
                return url
                
        except Exception as e:
            print(f"URL構築エラー: {e}")
            return None
    
    def _build_jalan_url(self, query: str, location: Dict) -> str:
        """じゃらんURL構築"""
        prefecture = location.get('prefecture', '')
        jalan_code = self.jalan_prefecture_codes.get(prefecture, '440000')  # デフォルト: 大分県
        
        return f"https://www.jalan.net/kankou/{jalan_code}/?screenId=OUW1021&keyword={query}"
    
    def _build_gurunavi_url(self, query: str, location: Dict) -> str:
        """ぐるなびURL構築"""
        city = location.get('city', '')
        if city:
            city_encoded = urllib.parse.quote(city)
            return f"https://r.gnavi.co.jp/area/jp/rs/?fwp={city_encoded}"
            # return f"https://r.gnavi.co.jp/area/jp/rs/?fwp={city_encoded}&fw={query}"
        else:
            return f"https://r.gnavi.co.jp/search/?fw={query}"
    
    def _build_google_maps_url(self, query: str, location: Dict) -> str:
        """Google Maps URL構築（多言語対応）"""
        city = location.get('city', '')
        prefecture = location.get('prefecture', '')
        region = location.get('region', '')
        
        print(f"[SPECIALIZED_LINK] Google Maps URL構築: city={city}, prefecture={prefecture}, region={region}")
        
        # 韓国の都市の場合
        if region == '韓国':
            if city == 'ソウル市':
                location_str = "Seoul, South Korea"
            elif city == '釜山市':
                location_str = "Busan, South Korea"
            else:
                location_str = f"{city}, South Korea"
        else:
            # 日本の都市の場合
            if city and prefecture:
                location_str = f"{city},{prefecture}"
            elif city:
                location_str = city
            elif prefecture:
                location_str = prefecture
            else:
                location_str = "日本"
        
        # Google Mapsの検索URL
        encoded_location = urllib.parse.quote(location_str)
        print(f"[SPECIALIZED_LINK] Google Maps URL: {query}+{location_str}")
        return f"https://www.google.com/maps/search/{query}+{encoded_location}"
    
    def _build_tabelog_url(self, query: str, location: Dict) -> str:
        """食べログURL構築"""
        prefecture = location.get('prefecture', '')
        city = location.get('city', '')
        
        # 都道府県コードマッピング（食べログ用）
        tabelog_codes = {
            # 北海道・東北
            '北海道': 'hokkaido',
            '青森県': 'aomori',
            '岩手県': 'iwate',
            '宮城県': 'miyagi',
            '秋田県': 'akita',
            '山形県': 'yamagata',
            '福島県': 'fukushima',
            
            # 関東
            '茨城県': 'ibaraki',
            '栃木県': 'tochigi',
            '群馬県': 'gunma',
            '埼玉県': 'saitama',
            '千葉県': 'chiba',
            '東京都': 'tokyo',
            '神奈川県': 'kanagawa',
            
            # 中部・北陸
            '新潟県': 'niigata',
            '富山県': 'toyama',
            '石川県': 'ishikawa',
            '福井県': 'fukui',
            '山梨県': 'yamanashi',
            '長野県': 'nagano',
            '岐阜県': 'gifu',  # 白川郷対応
            '静岡県': 'shizuoka',
            '愛知県': 'aichi',
            
            # 関西
            '三重県': 'mie',
            '滋賀県': 'shiga',
            '京都府': 'kyoto',
            '大阪府': 'osaka',
            '兵庫県': 'hyogo',
            '奈良県': 'nara',
            '和歌山県': 'wakayama',
            
            # 中国・四国
            '鳥取県': 'tottori',
            '島根県': 'shimane',
            '岡山県': 'okayama',
            '広島県': 'hiroshima',
            '山口県': 'yamaguchi',
            '徳島県': 'tokushima',
            '香川県': 'kagawa',
            '愛媛県': 'ehime',
            '高知県': 'kochi',
            
            # 九州・沖縄
            '福岡県': 'fukuoka',
            '佐賀県': 'saga',
            '長崎県': 'nagasaki',
            '熊本県': 'kumamoto',
            '大分県': 'oita',
            '宮崎県': 'miyazaki',
            '鹿児島県': 'kagoshima',
            '沖縄県': 'okinawa'
        }
        
        area_code = tabelog_codes.get(prefecture, 'japan')
        return f"https://tabelog.com/{area_code}/rstLst/"
        # return f"https://tabelog.com/{area_code}/rstLst/?word={query}"
    
    def _get_area_code(self, location: Dict, site_name: str) -> Optional[str]:
        """サイト固有の地域コードを取得"""
        prefecture = location.get('prefecture', '')
        
        if site_name in ['じゃらんnet']:
            return self.jalan_prefecture_codes.get(prefecture)
        elif site_name in ['ぐるなび']:
            return self._get_gurunavi_area_code(location)
        else:
            return self.area_codes.get(prefecture)
    
    def _get_gurunavi_area_code(self, location: Dict) -> Optional[str]:
        """ぐるなび用地域コード"""
        prefecture = location.get('prefecture', '')
        gurunavi_codes = {
            '大分県': 'oita',
            '福岡県': 'fukuoka',
            '兵庫県': 'hyogo', 
            '大阪府': 'osaka',
            '京都府': 'kyoto',
            '東京都': 'tokyo'
        }
        return gurunavi_codes.get(prefecture)
    
    def _get_localized_site_name(self, site_name: str, language: str) -> str:
        """言語に応じたサイト名を取得（繁体字サポート追加）"""
        if language == 'en':
            name_mapping = {
                'じゃらんnet': '🗾 Jalan Tourism Guide',
                'ぐるなび': '🍽️ Gurunavi Restaurant Guide',
                '食べログ': '⭐ Tabelog Restaurant Reviews',
                'Google Maps': '🗺️ Google Maps'
            }
            return name_mapping.get(site_name, f"🔍 {site_name}")
        elif language == 'ko':
            name_mapping = {
                'じゃらんnet': '🗾 관광정보 (자란)',
                'ぐるなび': '🍽️ 그루메정보 (구루나비)',
                '食べログ': '⭐ 레스토랑 리뷰 (타베로그)',
                'Google Maps': '🗺️ 지도정보 (Google Maps)'
            }
            return name_mapping.get(site_name, f"🔍 {site_name}에서 자세히 보기")
        elif language in ['zh', 'zh-cn']:
            # 簡体字中国語
            name_mapping = {
                'じゃらんnet': '🗾 旅游信息（Jalan）',
                'ぐるなび': '🍽️ 餐厅信息（Gurunavi）',
                '食べログ': '⭐ 餐厅评价（Tabelog）',
                'Google Maps': '🗺️ 地图信息（Google Maps）'
            }
            return name_mapping.get(site_name, f"🔍 {site_name}详细信息")
        elif language in ['tw', 'zh-tw']:
            # 繁体字中国語
            name_mapping = {
                'じゃらんnet': '🗾 觀光資訊（Jalan）',
                'ぐるなび': '🍽️ 餐廳資訊（Gurunavi）',
                '食べログ': '⭐ 餐廳評價（Tabelog）',
                'Google Maps': '🗺️ 地圖資訊（Google Maps）'
            }
            return name_mapping.get(site_name, f"🔍 {site_name}詳細資訊")
        else:
            # 日本語（デフォルト）
            name_mapping = {
                'じゃらんnet': '🗾 観光情報（じゃらん）',
                'ぐるなび': '🍽️ グルメ情報（ぐるなび）',
                '食べログ': '⭐ レストラン口コミ（食べログ）',
                'Google Maps': '🗺️ 地図情報（Google Maps）'
            }
            return name_mapping.get(site_name, f"🔍 {site_name}で詳細を見る")
    
    def _load_area_codes(self) -> Dict:
        """地域コードマッピングを読み込み"""
        return {
            '大分県': '44',
            '兵庫県': '28',
            '大阪府': '27', 
            '京都府': '26',
            '東京都': '13',
            '神奈川県': '14',
            '栃木県': '09',  # 日光
            '福岡県': '40',
            '熊本県': '43',
            # 韓国の都市（代替処理用）
            '韓国': '13'  # 東京をフォールバック
        }
    
    def _load_jalan_codes(self) -> Dict:
        """じゃらん都道府県コードを読み込み（全都道府県対応）"""
        return {
            # 北海道・東北
            '北海道': '010000',
            '青森県': '020000',
            '岩手県': '030000',
            '宮城県': '040000',
            '秋田県': '050000',
            '山形県': '060000',
            '福島県': '070000',
            
            # 関東
            '茨城県': '080000',
            '栃木県': '090000',
            '群馬県': '100000',
            '埼玉県': '110000',
            '千葉県': '120000',
            '東京都': '130000',
            '神奈川県': '140000',
            
            # 中部・北陸
            '新潟県': '150000',
            '富山県': '160000',
            '石川県': '170000',
            '福井県': '180000',
            '山梨県': '190000',
            '長野県': '200000',
            '岐阜県': '210000',  # 白川郷対応
            '静岡県': '220000',
            '愛知県': '230000',
            
            # 関西
            '三重県': '240000',
            '滋賀県': '250000',
            '京都府': '260000',
            '大阪府': '270000',
            '兵庫県': '280000',
            '奈良県': '290000',
            '和歌山県': '300000',
            
            # 中国・四国
            '鳥取県': '310000',
            '島根県': '320000',
            '岡山県': '330000',
            '広島県': '340000',
            '山口県': '350000',
            '徳島県': '360000',
            '香川県': '370000',
            '愛媛県': '380000',
            '高知県': '390000',
            
            # 九州・沖縄
            '福岡県': '400000',
            '佐賀県': '410000',
            '長崎県': '420000',
            '熊本県': '430000',
            '大分県': '440000',
            '宮崎県': '450000',
            '鹿児島県': '460000',
            '沖縄県': '470000',
            
            # 国際対応（代替処理）
            '韓国': '130000'  # 東京をフォールバック
        }
    
    def _translate_query_to_japanese(self, query: str, language: str) -> str:
        """
        外国語のクエリを日本語に翻訳（URL用）
        
        Args:
            query: 翻訳対象クエリ
            language: 元の言語コード
            
        Returns:
            str: 日本語に翻訳されたクエリ
        """
        # 既に日本語の場合はそのまま返す
        if language == 'ja':
            return query
        
        # 翻訳サービスが利用できない場合はそのまま返す
        if not self.translation_service:
            print(f"[SPECIALIZED_LINK] 翻訳サービス利用不可、元のクエリを使用: '{query}'")
            return query
        
        try:
            # キーワードを日本語に翻訳
            japanese_query = self.translation_service.translate_text(query, 'ja', language)
            print(f"[SPECIALIZED_LINK] クエリ翻訳: '{query}' ({language}) → '{japanese_query}' (ja)")
            return japanese_query
        except Exception as e:
            print(f"[SPECIALIZED_LINK] クエリ翻訳エラー: {e}")
            # エラー時は元のクエリを返す
            return query