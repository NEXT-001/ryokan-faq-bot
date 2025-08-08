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
        import re
        
        # 入力テキストをクリーニング
        cleaned_text = location_text.strip()
        
        # 郵便番号チェック（3桁-4桁 or 7桁数字）
        # ハイフンありなし両方に対応
        postal_pattern = re.match(r'^\d{3}-?\d{4}$', cleaned_text)
        if postal_pattern:
            postal_result = self.get_address_from_postal_code(cleaned_text)
            if postal_result:
                return {
                    'city': postal_result['city'],
                    'prefecture': postal_result['prefecture'], 
                    'region': self._get_region_from_prefecture(postal_result['prefecture']),
                    'type': 'postal_code',
                    'address': postal_result.get('address', ''),
                    'postal_code': postal_result['postal_code']
                }
                
        # 7桁数字のみの場合も郵便番号として処理
        if re.match(r'^\d{7}$', cleaned_text):
            formatted_postal = f"{cleaned_text[:3]}-{cleaned_text[3:]}"
            postal_result = self.get_address_from_postal_code(formatted_postal)
            if postal_result:
                return {
                    'city': postal_result['city'],
                    'prefecture': postal_result['prefecture'], 
                    'region': self._get_region_from_prefecture(postal_result['prefecture']),
                    'type': 'postal_code',
                    'address': postal_result.get('address', ''),
                    'postal_code': postal_result['postal_code']
                }
        
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
            '黒川温泉': {'city':'南小国町','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Kurokawa Onsen',
                'alias':['Kurokawa Onsen','쿠로카와 온천','黑川温泉','黑川溫泉']},
            
            # 九州の主要温泉地を追加
            '嬉野温泉': {'city':'嬉野市','prefecture':'佐賀県','region':'九州','type':'onsen',
                'english':'Ureshino Onsen',
                'alias':['Ureshino Onsen','우레시노 온천','嬉野温泉','嬉野溫泉']},
            '別府温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Beppu Onsen',
                'alias':['Beppu Onsen','벳푸 온천','别府温泉','別府溫泉']},
            '雲仙温泉': {'city':'雲仙市','prefecture':'長崎県','region':'九州','type':'onsen',
                'english':'Unzen Onsen',
                'alias':['Unzen Onsen','운젠 온천','云仙温泉','雲仙溫泉']},
            '霧島温泉': {'city':'霧島市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Kirishima Onsen',
                'alias':['Kirishima Onsen','기리시마 온천','雾岛温泉','霧島溫泉']},
            '山鹿温泉': {'city':'山鹿市','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Yamaga Onsen',
                'alias':['Yamaga Onsen','야마가 온천','山鹿温泉','山鹿溫泉']},
            '平山温泉': {'city':'山鹿市','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Hirayama Onsen',
                'alias':['Hirayama Onsen','히라야마 온천','平山温泉','平山溫泉']},
            '内牧温泉': {'city':'阿蘇市','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Uchinomaki Onsen',
                'alias':['Uchinomaki Onsen','우치노마키 온천','内牧温泉','內牧溫泉']},
            '南阿蘇温泉': {'city':'南阿蘇村','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Minami-Aso Onsen',
                'alias':['Minami-Aso Onsen','미나미아소 온천','南阿苏温泉','南阿蘇溫泉']},
            '武雄温泉': {'city':'武雄市','prefecture':'佐賀県','region':'九州','type':'onsen',
                'english':'Takeo Onsen',
                'alias':['Takeo Onsen','다케오 온천','武雄温泉','武雄溫泉']},
            '川内高城温泉': {'city':'薩摩川内市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Sendai Takajo Onsen',
                'alias':['Sendai Takajo Onsen','센다이 다카조 온천','川内高城温泉','川內高城溫泉']},
            '妙見温泉': {'city':'霧島市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Myoken Onsen',
                'alias':['Myoken Onsen','묘켄 온천','妙见温泉','妙見溫泉']},
            '筋湯温泉': {'city':'九重町','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Sujiyu Onsen',
                'alias':['Sujiyu Onsen','스지유 온천','筋汤温泉','筋湯溫泉']},
            '宝泉寺温泉': {'city':'九重町','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Hosenji Onsen',
                'alias':['Hosenji Onsen','호센지 온천','宝泉寺温泉','寶泉寺溫泉']},
            '壁湯温泉': {'city':'九重町','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Kabeyu Onsen',
                'alias':['Kabeyu Onsen','가베유 온천','壁汤温泉','壁湯溫泉']},
            '川底温泉': {'city':'九重町','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Kawazoko Onsen',
                'alias':['Kawazoko Onsen','가와조코 온천','川底温泉','川底溫泉']},
            '湯坪温泉': {'city':'九重町','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Yutsubo Onsen',
                'alias':['Yutsubo Onsen','유츠보 온천','汤坪温泉','湯坪溫泉']},
            '長湯温泉': {'city':'竹田市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Nagayu Onsen',
                'alias':['Nagayu Onsen','나가유 온천','长汤温泉','長湯溫泉']},
            '久住高原温泉': {'city':'竹田市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Kuju Kogen Onsen',
                'alias':['Kuju Kogen Onsen','구주 고원 온천','久住高原温泉','久住高原溫泉']},
            '天ヶ瀬温泉': {'city':'日田市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Amagase Onsen',
                'alias':['Amagase Onsen','아마가세 온천','天濑温泉','天瀨溫泉']},
            '杖立温泉': {'city':'小国町','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Tsuetate Onsen',
                'alias':['Tsuetate Onsen','츠에타테 온천','杖立温泉','杖立溫泉']},
            '植木温泉': {'city':'熊本市','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Ueki Onsen',
                'alias':['Ueki Onsen','우에키 온천','植木温泉','植木溫泉']},
            '玉名温泉': {'city':'玉名市','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Tamana Onsen',
                'alias':['Tamana Onsen','다마나 온천','玉名温泉','玉名溫泉']},
            '菊池温泉': {'city':'菊池市','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Kikuchi Onsen',
                'alias':['Kikuchi Onsen','기쿠치 온천','菊池温泉','菊池溫泉']},
            '人吉温泉': {'city':'人吉市','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Hitoyoshi Onsen',
                'alias':['Hitoyoshi Onsen','히토요시 온천','人吉温泉','人吉溫泉']},
            '湯の児温泉': {'city':'水俣市','prefecture':'熊本県','region':'九州','type':'onsen',
                'english':'Yunoko Onsen',
                'alias':['Yunoko Onsen','유노코 온천','汤之儿温泉','湯之兒溫泉']},
            '小浜温泉': {'city':'雲仙市','prefecture':'長崎県','region':'九州','type':'onsen',
                'english':'Obama Onsen',
                'alias':['Obama Onsen','오바마 온천','小浜温泉','小濱溫泉']},
            '島原温泉': {'city':'島原市','prefecture':'長崎県','region':'九州','type':'onsen',
                'english':'Shimabara Onsen',
                'alias':['Shimabara Onsen','시마바라 온천','岛原温泉','島原溫泉']},
            '平戸温泉': {'city':'平戸市','prefecture':'長崎県','region':'九州','type':'onsen',
                'english':'Hirado Onsen',
                'alias':['Hirado Onsen','히라도 온천','平户温泉','平戶溫泉']},
            '原鶴温泉': {'city':'朝倉市','prefecture':'福岡県','region':'九州','type':'onsen',
                'english':'Harazuru Onsen',
                'alias':['Harazuru Onsen','하라즈루 온천','原鹤温泉','原鶴溫泉']},
            '筑後川温泉': {'city':'うきは市','prefecture':'福岡県','region':'九州','type':'onsen',
                'english':'Chikugogawa Onsen',
                'alias':['Chikugogawa Onsen','치쿠고가와 온천','筑后川温泉','筑後川溫泉']},
            '船小屋温泉': {'city':'筑後市','prefecture':'福岡県','region':'九州','type':'onsen',
                'english':'Funagoya Onsen',
                'alias':['Funagoya Onsen','후나고야 온천','船小屋温泉','船小屋溫泉']},
            '二日市温泉': {'city':'筑紫野市','prefecture':'福岡県','region':'九州','type':'onsen',
                'english':'Futsukaichi Onsen',
                'alias':['Futsukaichi Onsen','후츠카이치 온천','二日市温泉','二日市溫泉']},
            '脇田温泉': {'city':'宮若市','prefecture':'福岡県','region':'九州','type':'onsen',
                'english':'Wakita Onsen',
                'alias':['Wakita Onsen','와키타 온천','脇田温泉','脇田溫泉']},
            '吉井温泉': {'city':'うきは市','prefecture':'福岡県','region':'九州','type':'onsen',
                'english':'Yoshii Onsen',
                'alias':['Yoshii Onsen','요시이 온천','吉井温泉','吉井溫泉']},
            '日田温泉': {'city':'日田市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Hita Onsen',
                'alias':['Hita Onsen','히타 온천','日田温泉','日田溫泉']},
            '鉄輪温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Kannawa Onsen',
                'alias':['Kannawa Onsen','간나와 온천','铁轮温泉','鐵輪溫泉']},
            '観海寺温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Kankaiji Onsen',
                'alias':['Kankaiji Onsen','간카이지 온천','观海寺温泉','觀海寺溫泉']},
            '明礬温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Myoban Onsen',
                'alias':['Myoban Onsen','묘반 온천','明矾温泉','明礬溫泉']},
            '亀川温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Kamegawa Onsen',
                'alias':['Kamegawa Onsen','가메가와 온천','龟川温泉','龜川溫泉']},
            '堀田温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Horita Onsen',
                'alias':['Horita Onsen','호리타 온천','堀田温泉','堀田溫泉']},
            '浜脇温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Hamawaki Onsen',
                'alias':['Hamawaki Onsen','하마와키 온천','滨脇温泉','濱脇溫泉']},
            '柴石温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Shibaseki Onsen',
                'alias':['Shibaseki Onsen','시바세키 온천','柴石温泉','柴石溫泉']},
            '城島高原温泉': {'city':'別府市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Kijima Kogen Onsen',
                'alias':['Kijima Kogen Onsen','기지마 고원 온천','城岛高原温泉','城島高原溫泉']},
            '湯の花温泉': {'city':'由布市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Yunohana Onsen',
                'alias':['Yunohana Onsen','유노하나 온천','汤之花温泉','湯之花溫泉']},
            '塚原温泉': {'city':'由布市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Tsukahara Onsen',
                'alias':['Tsukahara Onsen','츠카하라 온천','冢原温泉','塚原溫泉']},
            '湯平温泉': {'city':'由布市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Yunohira Onsen',
                'alias':['Yunohira Onsen','유노히라 온천','汤平温泉','湯平溫泉']},
            '庄内温泉': {'city':'由布市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Shonai Onsen',
                'alias':['Shonai Onsen','쇼나이 온천','庄内温泉','庄內溫泉']},
            '臼杵温泉': {'city':'臼杵市','prefecture':'大分県','region':'九州','type':'onsen',
                'english':'Usuki Onsen',
                'alias':['Usuki Onsen','우스키 온천','臼杵温泉','臼杵溫泉']},
            '温泉津温泉': {'city':'大田市','prefecture':'島根県','region':'中国','type':'onsen',
                'english':'Yunotsu Onsen',
                'alias':['Yunotsu Onsen','유노츠 온천','温泉津温泉','溫泉津溫泉']},
            'えびの高原温泉': {'city':'えびの市','prefecture':'宮崎県','region':'九州','type':'onsen',
                'english':'Ebino Kogen Onsen',
                'alias':['Ebino Kogen Onsen','에비노 고원 온천','虾野高原温泉','蝦野高原溫泉']},
            '青島温泉': {'city':'宮崎市','prefecture':'宮崎県','region':'九州','type':'onsen',
                'english':'Aoshima Onsen',
                'alias':['Aoshima Onsen','아오시마 온천','青岛温泉','青島溫泉']},
            '北郷温泉': {'city':'日南市','prefecture':'宮崎県','region':'九州','type':'onsen',
                'english':'Kitago Onsen',
                'alias':['Kitago Onsen','기타고 온천','北乡温泉','北鄉溫泉']},
            '京町温泉': {'city':'えびの市','prefecture':'宮崎県','region':'九州','type':'onsen',
                'english':'Kyomachi Onsen',
                'alias':['Kyomachi Onsen','교마치 온천','京町温泉','京町溫泉']},
            '市比野温泉': {'city':'薩摩川内市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Ichihino Onsen',
                'alias':['Ichihino Onsen','이치히노 온천','市比野温泉','市比野溫泉']},
            '新川渓谷温泉': {'city':'薩摩川内市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Shinkawa Keikoku Onsen',
                'alias':['Shinkawa Keikoku Onsen','신카와 케이코쿠 온천','新川溪谷温泉','新川溪谷溫泉']},
            '紫尾温泉': {'city':'薩摩川内市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Shio Onsen',
                'alias':['Shio Onsen','시오 온천','紫尾温泉','紫尾溫泉']},
            '日当山温泉': {'city':'霧島市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Hintoyama Onsen',
                'alias':['Hintoyama Onsen','힌토야마 온천','日当山温泉','日當山溫泉']},
            '安楽温泉': {'city':'霧島市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Anraku Onsen',
                'alias':['Anraku Onsen','안라쿠 온천','安乐温泉','安樂溫泉']},
            '新湯温泉': {'city':'霧島市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Shinyu Onsen',
                'alias':['Shinyu Onsen','신유 온천','新汤温泉','新湯溫泉']},
            '湯之元温泉': {'city':'日置市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Yunomoto Onsen',
                'alias':['Yunomoto Onsen','유노모토 온천','汤之元温泉','湯之元溫泉']},
            '東郷温泉': {'city':'日置市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Togo Onsen',
                'alias':['Togo Onsen','도고 온천','东乡温泉','東鄉溫泉']},
            '吹上温泉': {'city':'日置市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Fukiage Onsen',
                'alias':['Fukiage Onsen','후키아게 온천','吹上温泉','吹上溫泉']},
            '砂むし温泉': {'city':'指宿市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Sunamushi Onsen',
                'alias':['Sunamushi Onsen','스나무시 온천','砂蒸温泉','砂蒸溫泉']},
            '山川温泉': {'city':'指宿市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Yamagawa Onsen',
                'alias':['Yamagawa Onsen','야마가와 온천','山川温泉','山川溫泉']},
            '鰻温泉': {'city':'指宿市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Unagi Onsen',
                'alias':['Unagi Onsen','우나기 온천','鳗温泉','鰻溫泉']},
            '池田湖温泉': {'city':'指宿市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Ikedako Onsen',
                'alias':['Ikedako Onsen','이케다코 온천','池田湖温泉','池田湖溫泉']},
            '有村温泉': {'city':'鹿児島市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Arimura Onsen',
                'alias':['Arimura Onsen','아리무라 온천','有村温泉','有村溫泉']},
            '古里温泉': {'city':'鹿児島市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Furusato Onsen',
                'alias':['Furusato Onsen','후루사토 온천','古里温泉','古里溫泉']},
            '垂水温泉': {'city':'垂水市','prefecture':'鹿児島県','region':'九州','type':'onsen',
                'english':'Tarumizu Onsen',
                'alias':['Tarumizu Onsen','다루미즈 온천','垂水温泉','垂水溫泉']},

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
        
        # 全国主要都市（人口10万人以上＋有名観光地）を追加
        major_cities = {
            # 北海道（札幌以外の主要都市・観光地）
            '旭川': {'city': '旭川市', 'prefecture': '北海道', 'region': '北海道', 'type': 'city', 'english': 'Asahikawa', 'alias': ['Asahikawa', '아사히카와', '旭川', '旭川']},
            '帯広': {'city': '帯広市', 'prefecture': '北海道', 'region': '北海道', 'type': 'city', 'english': 'Obihiro', 'alias': ['Obihiro', '오비히로', '带广', '帶廣']},
            '釧路': {'city': '釧路市', 'prefecture': '北海道', 'region': '北海道', 'type': 'city', 'english': 'Kushiro', 'alias': ['Kushiro', '구시로', '钏路', '釧路']},
            '北見': {'city': '北見市', 'prefecture': '北海道', 'region': '北海道', 'type': 'city', 'english': 'Kitami', 'alias': ['Kitami', '기타미', '北见', '北見']},
            '美瑛': {'city': '美瑛町', 'prefecture': '北海道', 'region': '北海道', 'type': 'area', 'english': 'Biei', 'alias': ['Biei', '비에이', '美瑛', '美瑛']},
            '洞爺湖': {'city': '洞爺湖町', 'prefecture': '北海道', 'region': '北海道', 'type': 'area', 'english': 'Lake Toya', 'alias': ['Lake Toya', 'Toyako', '도야코', '洞爷湖', '洞爺湖']},
            
            # 東北地方
            '青森': {'city': '青森市', 'prefecture': '青森県', 'region': '東北', 'type': 'city', 'english': 'Aomori', 'alias': ['Aomori', '아오모리', '青森', '青森']},
            '弘前': {'city': '弘前市', 'prefecture': '青森県', 'region': '東北', 'type': 'city', 'english': 'Hirosaki', 'alias': ['Hirosaki', '히로사키', '弘前', '弘前']},
            '八戸': {'city': '八戸市', 'prefecture': '青森県', 'region': '東北', 'type': 'city', 'english': 'Hachinohe', 'alias': ['Hachinohe', '하치노헤', '八户', '八戸']},
            '盛岡': {'city': '盛岡市', 'prefecture': '岩手県', 'region': '東北', 'type': 'city', 'english': 'Morioka', 'alias': ['Morioka', '모리오카', '盛冈', '盛岡']},
            '一関': {'city': '一関市', 'prefecture': '岩手県', 'region': '東北', 'type': 'city', 'english': 'Ichinoseki', 'alias': ['Ichinoseki', '이치노세키', '一关', '一關']},
            '奥州': {'city': '奥州市', 'prefecture': '岩手県', 'region': '東北', 'type': 'city', 'english': 'Oshu', 'alias': ['Oshu', '오슈', '奥州', '奧州']},
            '秋田': {'city': '秋田市', 'prefecture': '秋田県', 'region': '東北', 'type': 'city', 'english': 'Akita', 'alias': ['Akita', '아키타', '秋田', '秋田']},
            '横手': {'city': '横手市', 'prefecture': '秋田県', 'region': '東北', 'type': 'city', 'english': 'Yokote', 'alias': ['Yokote', '요코테', '横手', '橫手']},
            '山形': {'city': '山形市', 'prefecture': '山形県', 'region': '東北', 'type': 'city', 'english': 'Yamagata', 'alias': ['Yamagata', '야마가타', '山形', '山形']},
            '鶴岡': {'city': '鶴岡市', 'prefecture': '山形県', 'region': '東北', 'type': 'city', 'english': 'Tsuruoka', 'alias': ['Tsuruoka', '쓰루오카', '鶴岡', '鶴岡']},
            '酒田': {'city': '酒田市', 'prefecture': '山形県', 'region': '東北', 'type': 'city', 'english': 'Sakata', 'alias': ['Sakata', '사카타', '酒田', '酒田']},
            '福島': {'city': '福島市', 'prefecture': '福島県', 'region': '東北', 'type': 'city', 'english': 'Fukushima', 'alias': ['Fukushima', '후쿠시마', '福岛', '福島']},
            'いわき': {'city': 'いわき市', 'prefecture': '福島県', 'region': '東北', 'type': 'city', 'english': 'Iwaki', 'alias': ['Iwaki', '이와키', '磐城', 'いわき']},
            '郡山': {'city': '郡山市', 'prefecture': '福島県', 'region': '東北', 'type': 'city', 'english': 'Koriyama', 'alias': ['Koriyama', '고리야마', '郡山', '郡山']},
            '会津若松': {'city': '会津若松市', 'prefecture': '福島県', 'region': '東北', 'type': 'city', 'english': 'Aizuwakamatsu', 'alias': ['Aizuwakamatsu', '아이즈와카마츠', '会津若松', '會津若松']},
            
            # 関東地方（既存以外）
            '水戸': {'city': '水戸市', 'prefecture': '茨城県', 'region': '関東', 'type': 'city', 'english': 'Mito', 'alias': ['Mito', '미토', '水户', '水戸']},
            'つくば': {'city': 'つくば市', 'prefecture': '茨城県', 'region': '関東', 'type': 'city', 'english': 'Tsukuba', 'alias': ['Tsukuba', '쓰쿠바', '筑波', 'つくば']},
            '日立': {'city': '日立市', 'prefecture': '茨城県', 'region': '関東', 'type': 'city', 'english': 'Hitachi', 'alias': ['Hitachi', '히타치', '日立', '日立']},
            'ひたちなか': {'city': 'ひたちなか市', 'prefecture': '茨城県', 'region': '関東', 'type': 'city', 'english': 'Hitachinaka', 'alias': ['Hitachinaka', '히타치나카', '常陆那珂', 'ひたちなか']},
            '宇都宮': {'city': '宇都宮市', 'prefecture': '栃木県', 'region': '関東', 'type': 'city', 'english': 'Utsunomiya', 'alias': ['Utsunomiya', '우츠노미야', '宇都宫', '宇都宮']},
            '足利': {'city': '足利市', 'prefecture': '栃木県', 'region': '関東', 'type': 'city', 'english': 'Ashikaga', 'alias': ['Ashikaga', '아시카가', '足利', '足利']},
            '那須': {'city': '那須町', 'prefecture': '栃木県', 'region': '関東', 'type': 'area', 'english': 'Nasu', 'alias': ['Nasu', '나스', '那须', '那須']},
            '前橋': {'city': '前橋市', 'prefecture': '群馬県', 'region': '関東', 'type': 'city', 'english': 'Maebashi', 'alias': ['Maebashi', '마에바시', '前桥', '前橋']},
            '高崎': {'city': '高崎市', 'prefecture': '群馬県', 'region': '関東', 'type': 'city', 'english': 'Takasaki', 'alias': ['Takasaki', '다카사키', '高崎', '高崎']},
            '草津': {'city': '草津町', 'prefecture': '群馬県', 'region': '関東', 'type': 'area', 'english': 'Kusatsu', 'alias': ['Kusatsu', '구사츠', '草津', '草津']},
            'さいたま': {'city': 'さいたま市', 'prefecture': '埼玉県', 'region': '関東', 'type': 'city', 'english': 'Saitama', 'alias': ['Saitama', '사이타마', '埼玉', 'さいたま']},
            '川越': {'city': '川越市', 'prefecture': '埼玉県', 'region': '関東', 'type': 'city', 'english': 'Kawagoe', 'alias': ['Kawagoe', '가와고에', '川越', '川越']},
            '秩父': {'city': '秩父市', 'prefecture': '埼玉県', 'region': '関東', 'type': 'city', 'english': 'Chichibu', 'alias': ['Chichibu', '치치부', '秩父', '秩父']},
            '千葉': {'city': '千葉市', 'prefecture': '千葉県', 'region': '関東', 'type': 'city', 'english': 'Chiba', 'alias': ['Chiba', '치바', '千叶', '千葉']},
            '船橋': {'city': '船橋市', 'prefecture': '千葉県', 'region': '関東', 'type': 'city', 'english': 'Funabashi', 'alias': ['Funabashi', '후나바시', '船桥', '船橋']},
            '柏': {'city': '柏市', 'prefecture': '千葉県', 'region': '関東', 'type': 'city', 'english': 'Kashiwa', 'alias': ['Kashiwa', '가시와', '柏', '柏']},
            '成田': {'city': '成田市', 'prefecture': '千葉県', 'region': '関東', 'type': 'city', 'english': 'Narita', 'alias': ['Narita', '나리타', '成田', '成田']},
            
            # 中部地方
            '新潟': {'city': '新潟市', 'prefecture': '新潟県', 'region': '中部', 'type': 'city', 'english': 'Niigata', 'alias': ['Niigata', '니가타', '新潟', '新潟']},
            '長岡': {'city': '長岡市', 'prefecture': '新潟県', 'region': '中部', 'type': 'city', 'english': 'Nagaoka', 'alias': ['Nagaoka', '나가오카', '长冈', '長岡']},
            '上越': {'city': '上越市', 'prefecture': '新潟県', 'region': '中部', 'type': 'city', 'english': 'Joetsu', 'alias': ['Joetsu', '조에츠', '上越', '上越']},
            '富山': {'city': '富山市', 'prefecture': '富山県', 'region': '中部', 'type': 'city', 'english': 'Toyama', 'alias': ['Toyama', '도야마', '富山', '富山']},
            '高岡': {'city': '高岡市', 'prefecture': '富山県', 'region': '中部', 'type': 'city', 'english': 'Takaoka', 'alias': ['Takaoka', '다카오카', '高冈', '高岡']},
            '福井': {'city': '福井市', 'prefecture': '福井県', 'region': '中部', 'type': 'city', 'english': 'Fukui', 'alias': ['Fukui', '후쿠이', '福井', '福井']},
            '甲府': {'city': '甲府市', 'prefecture': '山梨県', 'region': '中部', 'type': 'city', 'english': 'Kofu', 'alias': ['Kofu', '고후', '甲府', '甲府']},
            '長野': {'city': '長野市', 'prefecture': '長野県', 'region': '中部', 'type': 'city', 'english': 'Nagano', 'alias': ['Nagano', '나가노', '长野', '長野']},
            '軽井沢': {'city': '軽井沢町', 'prefecture': '長野県', 'region': '中部', 'type': 'area', 'english': 'Karuizawa', 'alias': ['Karuizawa', '가루이자와', '轻井泽', '輕井澤']},
            '上高地': {'city': '松本市', 'prefecture': '長野県', 'region': '中部', 'type': 'area', 'english': 'Kamikochi', 'alias': ['Kamikochi', '가미고치', '上高地', '上高地']},
            '岐阜': {'city': '岐阜市', 'prefecture': '岐阜県', 'region': '中部', 'type': 'city', 'english': 'Gifu', 'alias': ['Gifu', '기후', '岐阜', '岐阜']},
            '静岡': {'city': '静岡市', 'prefecture': '静岡県', 'region': '中部', 'type': 'city', 'english': 'Shizuoka', 'alias': ['Shizuoka', '시즈오카', '静冈', '靜岡']},
            '浜松': {'city': '浜松市', 'prefecture': '静岡県', 'region': '中部', 'type': 'city', 'english': 'Hamamatsu', 'alias': ['Hamamatsu', '하마마츠', '滨松', '濱松']},
            '熱海': {'city': '熱海市', 'prefecture': '静岡県', 'region': '中部', 'type': 'city', 'english': 'Atami', 'alias': ['Atami', '아타미', '热海', '熱海']},
            '伊東': {'city': '伊東市', 'prefecture': '静岡県', 'region': '中部', 'type': 'city', 'english': 'Ito', 'alias': ['Ito', '이토', '伊东', '伊東']},
            '豊橋': {'city': '豊橋市', 'prefecture': '愛知県', 'region': '中部', 'type': 'city', 'english': 'Toyohashi', 'alias': ['Toyohashi', '도요하시', '丰桥', '豐橋']},
            '岡崎': {'city': '岡崎市', 'prefecture': '愛知県', 'region': '中部', 'type': 'city', 'english': 'Okazaki', 'alias': ['Okazaki', '오카자키', '冈崎', '岡崎']},
            '一宮': {'city': '一宮市', 'prefecture': '愛知県', 'region': '中部', 'type': 'city', 'english': 'Ichinomiya', 'alias': ['Ichinomiya', '이치노미야', '一宫', '一宮']},
            '春日井': {'city': '春日井市', 'prefecture': '愛知県', 'region': '中部', 'type': 'city', 'english': 'Kasugai', 'alias': ['Kasugai', '가스가이', '春日井', '春日井']},
            '津': {'city': '津市', 'prefecture': '三重県', 'region': '関西', 'type': 'city', 'english': 'Tsu', 'alias': ['Tsu', '쓰', '津', '津']},
            '四日市': {'city': '四日市市', 'prefecture': '三重県', 'region': '関西', 'type': 'city', 'english': 'Yokkaichi', 'alias': ['Yokkaichi', '욧카이치', '四日市', '四日市']},
            '伊勢': {'city': '伊勢市', 'prefecture': '三重県', 'region': '関西', 'type': 'city', 'english': 'Ise', 'alias': ['Ise', '이세', '伊势', '伊勢']},
            
            # 関西地方（既存以外）
            '大津': {'city': '大津市', 'prefecture': '滋賀県', 'region': '関西', 'type': 'city', 'english': 'Otsu', 'alias': ['Otsu', '오츠', '大津', '大津']},
            '草津': {'city': '草津市', 'prefecture': '滋賀県', 'region': '関西', 'type': 'city', 'english': 'Kusatsu', 'alias': ['Kusatsu', '구사츠', '草津', '草津']},
            '彦根': {'city': '彦根市', 'prefecture': '滋賀県', 'region': '関西', 'type': 'city', 'english': 'Hikone', 'alias': ['Hikone', '히코네', '彦根', '彦根']},
            '堺': {'city': '堺市', 'prefecture': '大阪府', 'region': '関西', 'type': 'city', 'english': 'Sakai', 'alias': ['Sakai', '사카이', '堺', '堺']},
            '東大阪': {'city': '東大阪市', 'prefecture': '大阪府', 'region': '関西', 'type': 'city', 'english': 'Higashiosaka', 'alias': ['Higashiosaka', '히가시오사카', '东大阪', '東大阪']},
            '枚方': {'city': '枚方市', 'prefecture': '大阪府', 'region': '関西', 'type': 'city', 'english': 'Hirakata', 'alias': ['Hirakata', '히라카타', '枚方', '枚方']},
            '豊中': {'city': '豊中市', 'prefecture': '大阪府', 'region': '関西', 'type': 'city', 'english': 'Toyonaka', 'alias': ['Toyonaka', '도요나카', '丰中', '豐中']},
            '姫路': {'city': '姫路市', 'prefecture': '兵庫県', 'region': '関西', 'type': 'city', 'english': 'Himeji', 'alias': ['Himeji', '히메지', '姬路', '姬路']},
            '西宮': {'city': '西宮市', 'prefecture': '兵庫県', 'region': '関西', 'type': 'city', 'english': 'Nishinomiya', 'alias': ['Nishinomiya', '니시노미야', '西宫', '西宮']},
            '尼崎': {'city': '尼崎市', 'prefecture': '兵庫県', 'region': '関西', 'type': 'city', 'english': 'Amagasaki', 'alias': ['Amagasaki', '아마가사키', '尼崎', '尼崎']},
            '明石': {'city': '明石市', 'prefecture': '兵庫県', 'region': '関西', 'type': 'city', 'english': 'Akashi', 'alias': ['Akashi', '아카시', '明石', '明石']},
            '有馬': {'city': '神戸市', 'prefecture': '兵庫県', 'region': '関西', 'type': 'area', 'english': 'Arima', 'alias': ['Arima', '아리마', '有马', '有馬']},
            '城崎': {'city': '豊岡市', 'prefecture': '兵庫県', 'region': '関西', 'type': 'area', 'english': 'Kinosaki', 'alias': ['Kinosaki', '기노사키', '城崎', '城崎']},
            '和歌山': {'city': '和歌山市', 'prefecture': '和歌山県', 'region': '関西', 'type': 'city', 'english': 'Wakayama', 'alias': ['Wakayama', '와카야마', '和歌山', '和歌山']},
            '高野山': {'city': '高野町', 'prefecture': '和歌山県', 'region': '関西', 'type': 'area', 'english': 'Koyasan', 'alias': ['Koyasan', '고야산', '高野山', '高野山']},
            '白浜': {'city': '白浜町', 'prefecture': '和歌山県', 'region': '関西', 'type': 'area', 'english': 'Shirahama', 'alias': ['Shirahama', '시라하마', '白滨', '白濱']},
            
            # 中国・四国地方
            '鳥取': {'city': '鳥取市', 'prefecture': '鳥取県', 'region': '中国', 'type': 'city', 'english': 'Tottori', 'alias': ['Tottori', '돗토리', '鸟取', '鳥取']},
            '米子': {'city': '米子市', 'prefecture': '鳥取県', 'region': '中国', 'type': 'city', 'english': 'Yonago', 'alias': ['Yonago', '요나고', '米子', '米子']},
            '松江': {'city': '松江市', 'prefecture': '島根県', 'region': '中国', 'type': 'city', 'english': 'Matsue', 'alias': ['Matsue', '마츠에', '松江', '松江']},
            '出雲': {'city': '出雲市', 'prefecture': '島根県', 'region': '中国', 'type': 'city', 'english': 'Izumo', 'alias': ['Izumo', '이즈모', '出云', '出雲']},
            '岡山': {'city': '岡山市', 'prefecture': '岡山県', 'region': '中国', 'type': 'city', 'english': 'Okayama', 'alias': ['Okayama', '오카야마', '冈山', '岡山']},
            '倉敷': {'city': '倉敷市', 'prefecture': '岡山県', 'region': '中国', 'type': 'city', 'english': 'Kurashiki', 'alias': ['Kurashiki', '구라시키', '仓敷', '倉敷']},
            '津山': {'city': '津山市', 'prefecture': '岡山県', 'region': '中国', 'type': 'city', 'english': 'Tsuyama', 'alias': ['Tsuyama', '쓰야마', '津山', '津山']},
            '福山': {'city': '福山市', 'prefecture': '広島県', 'region': '中国', 'type': 'city', 'english': 'Fukuyama', 'alias': ['Fukuyama', '후쿠야마', '福山', '福山']},
            '呉': {'city': '呉市', 'prefecture': '広島県', 'region': '中国', 'type': 'city', 'english': 'Kure', 'alias': ['Kure', '구레', '吴', '吳']},
            '尾道': {'city': '尾道市', 'prefecture': '広島県', 'region': '中国', 'type': 'city', 'english': 'Onomichi', 'alias': ['Onomichi', '오노미치', '尾道', '尾道']},
            '下関': {'city': '下関市', 'prefecture': '山口県', 'region': '中国', 'type': 'city', 'english': 'Shimonoseki', 'alias': ['Shimonoseki', '시모노세키', '下关', '下關']},
            '宇部': {'city': '宇部市', 'prefecture': '山口県', 'region': '中国', 'type': 'city', 'english': 'Ube', 'alias': ['Ube', '우베', '宇部', '宇部']},
            '山口': {'city': '山口市', 'prefecture': '山口県', 'region': '中国', 'type': 'city', 'english': 'Yamaguchi', 'alias': ['Yamaguchi', '야마구치', '山口', '山口']},
            '徳島': {'city': '徳島市', 'prefecture': '徳島県', 'region': '四国', 'type': 'city', 'english': 'Tokushima', 'alias': ['Tokushima', '도쿠시마', '德岛', '德島']},
            '鳴門': {'city': '鳴門市', 'prefecture': '徳島県', 'region': '四国', 'type': 'city', 'english': 'Naruto', 'alias': ['Naruto', '나루토', '鸣门', '鳴門']},
            '高松': {'city': '高松市', 'prefecture': '香川県', 'region': '四国', 'type': 'city', 'english': 'Takamatsu', 'alias': ['Takamatsu', '다카마츠', '高松', '高松']},
            '丸亀': {'city': '丸亀市', 'prefecture': '香川県', 'region': '四国', 'type': 'city', 'english': 'Marugame', 'alias': ['Marugame', '마루가메', '丸龟', '丸龜']},
            '松山': {'city': '松山市', 'prefecture': '愛媛県', 'region': '四国', 'type': 'city', 'english': 'Matsuyama', 'alias': ['Matsuyama', '마츠야마', '松山', '松山']},
            '今治': {'city': '今治市', 'prefecture': '愛媛県', 'region': '四国', 'type': 'city', 'english': 'Imabari', 'alias': ['Imabari', '이마바리', '今治', '今治']},
            '新居浜': {'city': '新居浜市', 'prefecture': '愛媛県', 'region': '四国', 'type': 'city', 'english': 'Niihama', 'alias': ['Niihama', '니이하마', '新居滨', '新居濱']},
            '道後': {'city': '松山市', 'prefecture': '愛媛県', 'region': '四国', 'type': 'area', 'english': 'Dogo', 'alias': ['Dogo', '도고', '道后', '道後']},
            '高知': {'city': '高知市', 'prefecture': '高知県', 'region': '四国', 'type': 'city', 'english': 'Kochi', 'alias': ['Kochi', '고치', '高知', '高知']},
            '四万十': {'city': '四万十市', 'prefecture': '高知県', 'region': '四国', 'type': 'city', 'english': 'Shimanto', 'alias': ['Shimanto', '시만토', '四万十', '四萬十']},
            
            # 九州地方（既存以外の主要都市）
            '北九州': {'city': '北九州市', 'prefecture': '福岡県', 'region': '九州', 'type': 'city', 'english': 'Kitakyushu', 'alias': ['Kitakyushu', '기타큐슈', '北九州', '北九州']},
            '久留米': {'city': '久留米市', 'prefecture': '福岡県', 'region': '九州', 'type': 'city', 'english': 'Kurume', 'alias': ['Kurume', '구루메', '久留米', '久留米']},
            '飯塚': {'city': '飯塚市', 'prefecture': '福岡県', 'region': '九州', 'type': 'city', 'english': 'Iizuka', 'alias': ['Iizuka', '이이즈카', '饭塚', '飯塚']},
            '大牟田': {'city': '大牟田市', 'prefecture': '福岡県', 'region': '九州', 'type': 'city', 'english': 'Omuta', 'alias': ['Omuta', '오무타', '大牟田', '大牟田']},
            '太宰府': {'city': '太宰府市', 'prefecture': '福岡県', 'region': '九州', 'type': 'city', 'english': 'Dazaifu', 'alias': ['Dazaifu', '다자이후', '太宰府', '太宰府']},
            '唐津': {'city': '唐津市', 'prefecture': '佐賀県', 'region': '九州', 'type': 'city', 'english': 'Karatsu', 'alias': ['Karatsu', '가라츠', '唐津', '唐津']},
            '佐賀': {'city': '佐賀市', 'prefecture': '佐賀県', 'region': '九州', 'type': 'city', 'english': 'Saga', 'alias': ['Saga', '사가', '佐贺', '佐賀']},
            '佐世保': {'city': '佐世保市', 'prefecture': '長崎県', 'region': '九州', 'type': 'city', 'english': 'Sasebo', 'alias': ['Sasebo', '사세보', '佐世保', '佐世保']},
            '諫早': {'city': '諫早市', 'prefecture': '長崎県', 'region': '九州', 'type': 'city', 'english': 'Isahaya', 'alias': ['Isahaya', '이사하야', '谏早', '諫早']},
            '島原': {'city': '島原市', 'prefecture': '長崎県', 'region': '九州', 'type': 'city', 'english': 'Shimabara', 'alias': ['Shimabara', '시마바라', '岛原', '島原']},
            '雲仙': {'city': '雲仙市', 'prefecture': '長崎県', 'region': '九州', 'type': 'area', 'english': 'Unzen', 'alias': ['Unzen', '운젠', '云仙', '雲仙']},
            '八代': {'city': '八代市', 'prefecture': '熊本県', 'region': '九州', 'type': 'city', 'english': 'Yatsushiro', 'alias': ['Yatsushiro', '야츠시로', '八代', '八代']},
            '人吉': {'city': '人吉市', 'prefecture': '熊本県', 'region': '九州', 'type': 'city', 'english': 'Hitoyoshi', 'alias': ['Hitoyoshi', '히토요시', '人吉', '人吉']},
            '天草': {'city': '天草市', 'prefecture': '熊本県', 'region': '九州', 'type': 'city', 'english': 'Amakusa', 'alias': ['Amakusa', '아마쿠사', '天草', '天草']},
            '大分': {'city': '大分市', 'prefecture': '大分県', 'region': '九州', 'type': 'city', 'english': 'Oita', 'alias': ['Oita', '오이타', '大分', '大分']},
            '中津': {'city': '中津市', 'prefecture': '大分県', 'region': '九州', 'type': 'city', 'english': 'Nakatsu', 'alias': ['Nakatsu', '나카츠', '中津', '中津']},
            '日田': {'city': '日田市', 'prefecture': '大分県', 'region': '九州', 'type': 'city', 'english': 'Hita', 'alias': ['Hita', '히타', '日田', '日田']},
            '佐伯': {'city': '佐伯市', 'prefecture': '大分県', 'region': '九州', 'type': 'city', 'english': 'Saiki', 'alias': ['Saiki', '사이키', '佐伯', '佐伯']},
            '臼杵': {'city': '臼杵市', 'prefecture': '大分県', 'region': '九州', 'type': 'city', 'english': 'Usuki', 'alias': ['Usuki', '우스키', '臼杵', '臼杵']},
            '津久見': {'city': '津久見市', 'prefecture': '大分県', 'region': '九州', 'type': 'city', 'english': 'Tsukumi', 'alias': ['Tsukumi', '츠쿠미', '津久见', '津久見']},
            '宇佐': {'city': '宇佐市', 'prefecture': '大分県', 'region': '九州', 'type': 'city', 'english': 'Usa', 'alias': ['Usa', '우사', '宇佐', '宇佐']},
            '宮崎': {'city': '宮崎市', 'prefecture': '宮崎県', 'region': '九州', 'type': 'city', 'english': 'Miyazaki', 'alias': ['Miyazaki', '미야자키', '宫崎', '宮崎']},
            '都城': {'city': '都城市', 'prefecture': '宮崎県', 'region': '九州', 'type': 'city', 'english': 'Miyakonojo', 'alias': ['Miyakonojo', '미야코노조', '都城', '都城']},
            '延岡': {'city': '延岡市', 'prefecture': '宮崎県', 'region': '九州', 'type': 'city', 'english': 'Nobeoka', 'alias': ['Nobeoka', '노베오카', '延冈', '延岡']},
            '日南': {'city': '日南市', 'prefecture': '宮崎県', 'region': '九州', 'type': 'city', 'english': 'Nichinan', 'alias': ['Nichinan', '니치난', '日南', '日南']},
            '高千穂': {'city': '高千穂町', 'prefecture': '宮崎県', 'region': '九州', 'type': 'area', 'english': 'Takachiho', 'alias': ['Takachiho', '다카치호', '高千穂', '高千穗']},
            '霧島': {'city': '霧島市', 'prefecture': '鹿児島県', 'region': '九州', 'type': 'city', 'english': 'Kirishima', 'alias': ['Kirishima', '기리시마', '雾岛', '霧島']},
            '薩摩川内': {'city': '薩摩川内市', 'prefecture': '鹿児島県', 'region': '九州', 'type': 'city', 'english': 'Satsumasendai', 'alias': ['Satsumasendai', '사쓰마센다이', '萨摩川内', '薩摩川內']},
            '姶良': {'city': '姶良市', 'prefecture': '鹿児島県', 'region': '九州', 'type': 'city', 'english': 'Aira', 'alias': ['Aira', '아이라', '姶良', '姶良']},
            
            # 沖縄県
            '那覇': {'city': '那覇市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'city', 'english': 'Naha', 'alias': ['Naha', '나하', '那霸', '那覇']},
            '沖縄': {'city': '沖縄市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'city', 'english': 'Okinawa', 'alias': ['Okinawa', '오키나와', '冲绳', '沖繩']},
            '浦添': {'city': '浦添市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'city', 'english': 'Urasoe', 'alias': ['Urasoe', '우라소에', '浦添', '浦添']},
            '宜野湾': {'city': '宜野湾市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'city', 'english': 'Ginowan', 'alias': ['Ginowan', '기노완', '宜野湾', '宜野灣']},
            '石垣島': {'city': '石垣市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'area', 'english': 'Ishigaki Island', 'alias': ['Ishigaki', 'Ishigaki Island', '이시가키', '石垣岛', '石垣島']},
            '宮古島': {'city': '宮古島市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'area', 'english': 'Miyako Island', 'alias': ['Miyakojima', 'Miyako Island', '미야코지마', '宫古岛', '宮古島']},
            '恩納村': {'city': '恩納村', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'area', 'english': 'Onna', 'alias': ['Onna', '온나손', '恩纳村', '恩納村']},
            '名護': {'city': '名護市', 'prefecture': '沖縄県', 'region': '沖縄', 'type': 'city', 'english': 'Nago', 'alias': ['Nago', '나고', '名护', '名護']}
        }
        
        normalized_locations.update(major_cities)
        
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
        """都道府県名一致検索（県庁所在地を自動設定）"""
        # 県庁所在地マッピング
        prefecture_capitals = {
            '北海道': '札幌市', '青森県': '青森市', '岩手県': '盛岡市', '宮城県': '仙台市',
            '秋田県': '秋田市', '山形県': '山形市', '福島県': '福島市', '茨城県': '水戸市',
            '栃木県': '宇都宮市', '群馬県': '前橋市', '埼玉県': 'さいたま市', '千葉県': '千葉市',
            '東京都': '東京都', '神奈川県': '横浜市', '新潟県': '新潟市', '富山県': '富山市',
            '石川県': '金沢市', '福井県': '福井市', '山梨県': '甲府市', '長野県': '長野市',
            '岐阜県': '岐阜市', '静岡県': '静岡市', '愛知県': '名古屋市', '三重県': '津市',
            '滋賀県': '大津市', '京都府': '京都市', '大阪府': '大阪市', '兵庫県': '神戸市',
            '奈良県': '奈良市', '和歌山県': '和歌山市', '鳥取県': '鳥取市', '島根県': '松江市',
            '岡山県': '岡山市', '広島県': '広島市', '山口県': '山口市', '徳島県': '徳島市',
            '香川県': '高松市', '愛媛県': '松山市', '高知県': '高知市', '福岡県': '福岡市',
            '佐賀県': '佐賀市', '長崎県': '長崎市', '熊本県': '熊本市', '大分県': '大分市',
            '宮崎県': '宮崎市', '鹿児島県': '鹿児島市', '沖縄県': '那覇市'
        }
        
        for prefecture, info in self.prefecture_mapping.items():
            prefecture_short = prefecture.replace('県', '').replace('府', '').replace('都', '')
            
            # 完全一致または都道府県名が含まれる場合
            if prefecture in text or prefecture_short in text:
                # 「○○市」形式の入力の場合、市名を保持
                if '市' in text and not any(x in text for x in ['県', '府', '都']):
                    # 市名のみの入力（例：「鳥取市」）
                    city_name = text
                else:
                    # 県名から県庁所在地を取得
                    city_name = prefecture_capitals.get(prefecture, '')
                
                return {
                    'city': city_name,
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