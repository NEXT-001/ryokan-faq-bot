import requests
import openai
from langdetect import detect
import urllib.parse
import os
import re
from dotenv import load_dotenv

# .env を読み込む
load_dotenv()

# 翻訳サービスのインポート
try:
    from services.translation_service import TranslationService
    TRANSLATION_SERVICE_AVAILABLE = True
except ImportError:
    print("[TOURISM_SERVICE] 翻訳サービスが利用できません")
    TRANSLATION_SERVICE_AVAILABLE = False

# 環境変数から API キーを取得
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
openai.api_key = os.getenv("OPENAI_API_KEY")

def detect_language(text):
    """
    言語判定（強化版へのブリッジ関数）
    """
    try:
        # 強化言語検出を優先使用
        from services.enhanced_language_detection import enhanced_detect_language
        return enhanced_detect_language(text)
    except ImportError:
        print("[TOURISM_SERVICE] 強化言語検出が利用できません、フォールバック")
        return detect_language_fallback(text)

def detect_language_fallback(text):
    """
    フォールバック用言語判定（従来版改良、繁体字中国語サポート追加）
    """
    try:
        # 短いテキストや漢字のみの場合の特別処理
        if len(text.strip()) <= 3:
            # 短すぎる場合はデフォルトで日本語とする
            return "ja"
        
        # 日本語特有の文字（ひらがな、カタカナ）をチェック
        has_hiragana = bool(re.search(r'[あ-ん]', text))
        has_katakana = bool(re.search(r'[ア-ン]', text))
        
        if has_hiragana or has_katakana:
            # ひらがなまたはカタカナが含まれていれば確実に日本語
            return "ja"
        
        # 繁体字中国語特有の文字パターンをチェック
        traditional_chinese_patterns = [
            # 繁体字特有の文字
            r'餐廳', r'資訊', r'資料', r'觀光', r'飯店', r'風景', r'歷史', r'傳統',
            r'當地', r'營業', r'時間', r'價格', r'優質', r'評價', r'推薦', r'環境',
            r'發展', r'經濟', r'國際', r'機場', r'車站', r'飯局', r'點心', r'風味',
            # 台湾・香港でよく使われる表現
            r'什麼', r'東西', r'地方', r'這邊', r'那邊', r'這裡', r'那裡',
            # 繁体字の数字・単位
            r'個', r'間', r'種', r'層', r'樓', r'號',
        ]
        
        for pattern in traditional_chinese_patterns:
            if re.search(pattern, text):
                print(f"[LANGUAGE_DETECT] 繁体字パターン検出: {pattern}")
                return "tw"  # 繁体字中国語として判定
        
        # 日本語でよく使われる漢字の組み合わせパターン
        japanese_patterns = [
            r'観光', r'旅行', r'温泉', r'神社', r'寺院', r'公園', r'美術館', r'博物館',
            r'レストラン', r'食事', r'グルメ', r'料理', r'おすすめ', r'人気',
            r'チェックイン', r'チェックアウト', r'予約', r'宿泊'
        ]
        
        for pattern in japanese_patterns:
            if re.search(pattern, text):
                return "ja"
        
        # langdetectを使用するが、結果を検証
        detected = detect(text)
        
        # 繁体字中国語の特別処理
        if detected == "zh-cn":
            # 繁体字特有文字があるかさらにチェック
            has_traditional_chars = bool(re.search(r'[餐廳資訊觀光風景歷史傳統當營業時間價格優質評價推薦環境發展經濟國際機場車站]', text))
            if has_traditional_chars:
                print(f"[LANGUAGE_DETECT] 簡体字判定だが繁体字文字を検出: tw に変更")
                return "tw"
        
        # 漢字のみで韓国語と判定された場合は日本語に修正
        has_chinese_chars = bool(re.search(r'[一-龯]', text))
        has_korean_chars = bool(re.search(r'[가-힣]', text))
        
        if detected == "ko" and has_chinese_chars and not has_korean_chars:
            # 漢字があるが韓国文字がない場合は日本語とする
            return "ja"
        
        return detected
        
    except Exception as e:
        print(f"[LANGUAGE_DETECT] 言語判定エラー: {e}")
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

    # URL生成用にuser_inputを日本語に翻訳（必要に応じて）
    japanese_user_input = _translate_keyword_to_japanese(user_input, lang)
    print(f"[TOURISM_SERVICE] URL用ユーザー入力翻訳: '{user_input}' → '{japanese_user_input}'")

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
    
    # ぐるなびリンク（多言語対応）
    gnavi_label = _get_gnavi_label(lang)
    links.append({"name": gnavi_label, "photo": None, "map_url": generate_gnavi_url_by_city(city_name, lang)})
    
    # 複数の観光地情報サイトリンク（多言語対応）
    tourism_links = generate_multiple_tourism_links(city_name, lang)
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
    """複数の観光地情報サイトのリンクを生成（多言語対応）"""
    links = []
    
    # 1. じゃらんnet
    jalan_url = generate_tourism_url_by_city(city_name, lang)
    if "jalan.net" in jalan_url:
        jalan_label = _get_jalan_label(lang)
        links.append({"name": jalan_label, "photo": None, "map_url": jalan_url})
    
    # 2. 楽天トラベル
    rakuten_url = f"https://travel.rakuten.co.jp/guide/{urllib.parse.quote(city_name)}/"
    rakuten_label = _get_rakuten_label(lang)
    links.append({"name": rakuten_label, "photo": None, "map_url": rakuten_url})
    
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

def _get_jalan_label(lang):
    """じゃらんリンクのラベルを言語別に取得"""
    labels = {
        "ja": "🗾 観光地情報（じゃらん）",
        "en": "🗾 Tourist Information (Jalan)",
        "ko": "🗾 관광지 정보 (쟈란)",
        "zh": "🗾 旅游景点信息 (JALAN)",
        "tw": "🗾 旅遊景點資訊 (JALAN)"
    }
    return labels.get(lang, labels["ja"])

def _get_rakuten_label(lang):
    """楽天トラベルリンクのラベルを言語別に取得"""
    labels = {
        "ja": "🌸 観光ガイド（楽天トラベル）",
        "en": "🌸 Travel Guide (Rakuten Travel)",
        "ko": "🌸 관광 가이드 (라쿠텐 트래블)",
        "zh": "🌸 旅游指南 (乐天旅行)",
        "tw": "🌸 旅遊指南 (樂天旅遊)"
    }
    return labels.get(lang, labels["ja"])

def _get_tourism_label(lang):
    """観光地リンクのラベルを言語別に取得（後方互換性用）"""
    return _get_jalan_label(lang)

def _translate_keyword_to_japanese(keyword, source_language):
    """
    キーワードを日本語に翻訳（URL用）
    
    Args:
        keyword: 翻訳対象キーワード
        source_language: 元の言語コード
        
    Returns:
        str: 日本語に翻訳されたキーワード
    """
    # 既に日本語の場合はそのまま返す
    if source_language == 'ja':
        return keyword
    
    # 翻訳サービスが利用できない場合はそのまま返す
    if not TRANSLATION_SERVICE_AVAILABLE:
        print(f"[TOURISM_SERVICE] 翻訳サービス利用不可、元のキーワードを使用: '{keyword}'")
        return keyword
    
    try:
        # 翻訳サービスのインスタンス作成
        translation_service = TranslationService()
        
        # キーワードを日本語に翻訳
        japanese_keyword = translation_service.translate_text(keyword, 'ja', source_language)
        print(f"[TOURISM_SERVICE] キーワード翻訳: '{keyword}' ({source_language}) → '{japanese_keyword}' (ja)")
        return japanese_keyword
    except Exception as e:
        print(f"[TOURISM_SERVICE] キーワード翻訳エラー: {e}")
        # エラー時は元のキーワードを返す
        return keyword
