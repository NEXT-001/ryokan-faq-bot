import requests
import openai
from langdetect import detect
import urllib.parse
import os
import re
from dotenv import load_dotenv

# .env を読み込む
load_dotenv()

# 環境変数から API キーを取得
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

def detect_language(text):
    try:
        return detect(text)
    except:
        return "ja"

def add_links_to_tourist_spots(text):
    """回答テキスト内の観光スポット名にBing検索リンクを追加"""
    # 一般的な観光スポットのパターン
    tourist_spot_patterns = [
        # 寺社名（～寺、～神社、～大社）
        r'([一-龯ヶヵ々ー・]+(?:寺|神社|大社|稲荷|八幡宮|天満宮|宮|社))(?:（[ひらがなカタカナ一-龯ー・]+）)?',
        # 城・宮殿名（～城、～宮、～御所）
        r'([一-龯ヶヵ々ー・]+(?:城|宮|御所|館))(?:（[ひらがなカタカナ一-龯ー・]+）)?',
        # 公園・庭園名（～公園、～庭園、～園）
        r'([一-龯ヶヵ々ー・]+(?:公園|庭園|園|森林公園))(?:（[ひらがなカタカナ一-龯ー・]+）)?',
        # 山・峰名（～山、～峰、～岳）
        r'([一-龯ヶヵ々ー・]+(?:山|峰|岳|丘))(?:（[ひらがなカタカナ一-龯ー・]+）)?',
        # 橋・建造物名（～橋、～タワー、～駅）
        r'([一-龯ヶヵ々ー・]+(?:橋|タワー|駅|門|塔))(?:（[ひらがなカタカナ一-龯ー・]+）)?',
        # 地域・エリア名（～地区、～街、～町）
        r'([一-龯ヶヵ々ー・]+(?:地区|街|町|通り|小径|散歩道))(?:（[ひらがなカタカナ一-龯ー・]+）)?',
        # 美術館・博物館名（～美術館、～博物館、～館）
        r'([一-龯ヶヵ々ー・]+(?:美術館|博物館|記念館|資料館|館))(?:（[ひらがなカタカナ一-龯ー・]+）)?',
        # 温泉名（～温泉、～湯）
        r'([一-龯ヶヵ々ー・]+(?:温泉|湯))(?:（[ひらがなカタカナ一-龯ー・]+）)?',
        # 特定の有名スポット
        r'(竹林の小径|渡月橋|清水の舞台|千本鳥居|嵐山|祇園|先斗町|二年坂|三年坂|哲学の道)(?:（[ひらがなカタカナ一-龯ー・]+）)?'
    ]
    
    def create_bing_link(spot_name):
        """観光スポット名用のBing検索リンクを生成"""
        encoded_name = urllib.parse.quote(spot_name)
        return f"https://www.bing.com/search?q={encoded_name}"
    
    processed_text = text
    added_links = set()  # 重複リンク防止
    
    for pattern in tourist_spot_patterns:
        matches = re.finditer(pattern, processed_text)
        for match in matches:
            spot_name = match.group(1)
            full_match = match.group(0)
            
            # 既にリンク化済みかチェック
            if spot_name in added_links or '[' in full_match or ']' in full_match:
                continue
                
            # 3文字以上の場合のみリンク化（ノイズ除去）
            if len(spot_name) >= 3:
                bing_link = create_bing_link(full_match)
                markdown_link = f"[{full_match}]({bing_link})"
                processed_text = processed_text.replace(full_match, markdown_link, 1)
                added_links.add(spot_name)
    
    return processed_text

def generate_tourism_response_by_city(user_input, city_name, lang):
    """都市名ベースで観光情報を生成"""    
    system_prompt = {
        "ja": f"あなたは{city_name}の観光ガイドAIです。日本語で親切に答えてください。",
        "en": f"You are a sightseeing guide AI for {city_name}. Answer politely in English.",
        "ko": f"당신은 {city_name}의 관광 가이드 AI입니다. 한국어로 답변하십시오。",
        "zh": f"你是{city_name}的旅游向导AI。请用中文礼貌回答。"
    }.get(lang, f"You are a sightseeing guide AI for {city_name}. Answer politely.")

    prompt = f"""
都市・地域: {city_name}
入力された都市名: {city_name}

質問: {user_input}
質問と同じ言語で丁寧に答えてください。地域の特色やおすすめポイントを含めて回答してください。
"""

    if openai.api_key:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": system_prompt},
                          {"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=500
            )
            answer = response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API エラー: {e}")
            answer = _get_default_city_response(city_name, lang)
    else:
        answer = _get_default_city_response(city_name, lang)

    # 観光スポット名に自動リンクを追加
    answer_with_links = add_links_to_tourist_spots(answer)

    # グルメと観光地の複数リンクを生成
    links = []
    
    # ぐるなびリンク
    links.append({"name": "🍽️ 周辺グルメ・レストラン（ぐるなび）", "photo": None, "map_url": generate_gnavi_url_by_city(city_name, "ja")})
    
    # 複数の観光地情報サイトリンク
    tourism_links = generate_multiple_tourism_links(city_name, "ja")
    links.extend(tourism_links)

    return answer_with_links, links

def _get_default_city_response(city_name, lang):
    """デフォルトの都市情報レスポンス"""
    responses = {
        "ja": f"{city_name}の観光・グルメ情報をお探しですね。以下のリンクから詳細情報をご確認いただけます。",
        "en": f"Looking for tourism and gourmet information about {city_name}. Please check the links below for detailed information.",
        "ko": f"{city_name}의 관광・맛집 정보를 찾고 계시는군요. 아래 링크에서 자세한 정보를 확인하실 수 있습니다.",
        "zh": f"正在寻找{city_name}的旅游・美食信息。请通过以下链接查看详细信息。"
    }
    return responses.get(lang, responses["ja"])

def generate_gnavi_url_by_city(city_name, lang):
    """都市名ベースでぐるなび検索URLを生成"""
    # ぐるなびの検索URL形式（駅を削除）
    return f"https://r.gnavi.co.jp/area/jp/rs/?fwp={urllib.parse.quote(city_name)}"

def load_municipality_data():
    """自治体データCSVを読み込み"""
    import pandas as pd
    import os
    from config.unified_config import UnifiedConfig
    
    csv_path = os.path.join(UnifiedConfig.get_data_path(), "japan_municipalities.csv")
    try:
        df = pd.read_csv(csv_path)
        return df
    except Exception as e:
        print(f"自治体データCSVの読み込みエラー: {e}")
        return None

def get_jalan_code_from_city(city_name):
    """都市名からじゃらんコードを取得"""
    df = load_municipality_data()
    if df is None:
        return None
    
    # 市名での完全一致検索
    exact_match = df[df['city_name'] == city_name]
    if not exact_match.empty:
        return exact_match.iloc[0]['jalan_code']
    
    # 部分一致検索（市、県、区などを含む）
    partial_match = df[df['city_name'].str.contains(city_name, na=False)]
    if not partial_match.empty:
        return partial_match.iloc[0]['jalan_code']
    
    # 県名での検索
    prefecture_match = df[df['prefecture_name'].str.contains(city_name.replace('県', '').replace('府', '').replace('都', ''), na=False)]
    if not prefecture_match.empty:
        return prefecture_match.iloc[0]['jalan_code']
    
    return None

def generate_tourism_url_by_city(city_name, lang):
    """都市名ベースで観光地情報URLを生成（複数サイト対応）"""
    # CSVデータから県コードを取得
    jalan_code = get_jalan_code_from_city(city_name)
    
    if jalan_code:
        return f"https://www.jalan.net/kankou/{jalan_code}/?screenId=OUW1021"
    else:
        # 観光地名の特別マッピング（有名観光地）
        tourism_mapping = {
            "湯布院": "https://www.rurubu.com/season/autumn/kouyou/detail.aspx?SozaiNo=440001",
            "由布院": "https://www.rurubu.com/season/autumn/kouyou/detail.aspx?SozaiNo=440001", 
            "箱根": "https://www.hakone.or.jp/",
            "熱海": "https://www.ataminews.gr.jp/",
            "草津": "https://www.kusatsu-onsen.ne.jp/",
            "有馬": "https://www.arima-onsen.com/",
            "下呂": "https://www.gero-spa.or.jp/",
            "城崎": "https://www.kinosaki-spa.gr.jp/",
            "道後": "https://dogo.jp/",
            "別所": "https://www.bessho-spa.jp/"
        }
        
        # 観光地名での直接マッチング
        for spot, url in tourism_mapping.items():
            if spot in city_name:
                return url
        
        # 楽天トラベルをフォールバック
        return f"https://travel.rakuten.co.jp/guide/{urllib.parse.quote(city_name)}/"

def generate_multiple_tourism_links(city_name, lang):
    """複数の観光地情報サイトのリンクを生成"""
    links = []
    
    # 1. じゃらんnet
    jalan_url = generate_tourism_url_by_city(city_name, lang)
    if "jalan.net" in jalan_url:
        links.append({"name": "🗾 観光地情報（じゃらん）", "photo": None, "map_url": jalan_url})
    
    # 2. 楽天トラベル
    rakuten_url = f"https://travel.rakuten.co.jp/guide/{urllib.parse.quote(city_name)}/"
    links.append({"name": "🌸 観光ガイド（楽天トラベル）", "photo": None, "map_url": rakuten_url})
    
    # 3. るるぶ&more
    rurubu_url = f"https://rurubu.jp/andmore/search?keyword={urllib.parse.quote(city_name)}"
    links.append({"name": "📖 観光情報（るるぶ）", "photo": None, "map_url": rurubu_url})
    
    # 4. トリップアドバイザー
    tripadvisor_url = f"https://www.tripadvisor.jp/Search?q={urllib.parse.quote(city_name)}"
    links.append({"name": "✈️ 観光スポット（トリップアドバイザー）", "photo": None, "map_url": tripadvisor_url})
    
    return links

def _get_gnavi_label(lang):
    """ぐるなびリンクのラベルを言語別に取得"""
    labels = {
        "ja": "🍽️ 周辺グルメ・レストラン（ぐるなび）",
        "en": "🍽️ Nearby Restaurants (Gurunavi)",
        "ko": "🍽️ 주변 맛집・레스토랑 (구루나비)",
        "zh": "🍽️ 周边美食・餐厅 (GURUNAVI)"
    }
    return labels.get(lang, labels["ja"])

def _get_tourism_label(lang):
    """観光地リンクのラベルを言語別に取得"""
    labels = {
        "ja": "🗾 周辺観光地・スポット（じゃらん）",
        "en": "🗾 Nearby Tourist Spots (Jalan)",
        "ko": "🗾 주변 관광지・스팟 (쟈란)",
        "zh": "🗾 周边旅游景点 (JALAN)"
    }
    return labels.get(lang, labels["ja"])
