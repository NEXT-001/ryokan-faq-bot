import pandas as pd
import numpy as np
import os
import anthropic
from config.settings import load_api_key, is_test_mode

def create_embeddings():
    """
    FAQデータにエンベディングを追加して保存する
    """
    # テストモードの場合
    if is_test_mode():
        print("テストモードでエンベディングを生成します")
        
        # データディレクトリの確認
        if not os.path.exists("data"):
            os.makedirs("data")
        
        # CSVファイルの確認
        if not os.path.exists("data/faq.csv"):
            # サンプルデータを作成
            sample_data = {
                "question": [
                    "チェックインの時間は何時ですか？",
                    "駐車場はありますか？",
                    "Wi-Fiは利用できますか？",
                    "食事のアレルギー対応はできますか？",
                    "部屋のタイプはどのようなものがありますか？",
                    "温泉の効能は何ですか？",
                    "食事はどのような内容ですか？",
                    "チェックアウトの時間は何時ですか？",
                    "子供連れでも大丈夫ですか？",
                    "周辺の観光スポットはありますか？"
                ],
                "answer": [
                    "チェックインは15:00〜19:00です。事前にご連絡いただければ、遅いチェックインにも対応可能です。",
                    "はい、無料の駐車場を提供しています。大型車の場合は事前にご連絡ください。",
                    "全客室でWi-Fiを無料でご利用いただけます。接続情報はチェックイン時にお渡しします。",
                    "はい、アレルギーがある場合は予約時にお知らせください。可能な限り対応いたします。",
                    "和室と洋室の両方をご用意しています。和室は8畳・10畳・12畳、洋室はシングル・ツイン・ダブルがございます。",
                    "当館の温泉は神経痛、筋肉痛、関節痛、五十肩、運動麻痺、関節のこわばり、うちみ、くじき、慢性消化器病、痔疾、冷え性、病後回復期、疲労回復、健康増進に効果があります。",
                    "地元の新鮮な食材を使った会席料理をご提供しています。朝食は和食または洋食からお選びいただけます。",
                    "チェックアウトは10:00となっております。レイトチェックアウトをご希望の場合は、フロントにご相談ください。",
                    "はい、お子様連れのお客様も大歓迎です。お子様用の浴衣やスリッパ、食事用の椅子もご用意しております。",
                    "当館から車で15分以内に、〇〇神社、△△美術館、□□公園などがございます。詳しい情報はフロントでご案内しております。"
                ]
            }
            pd.DataFrame(sample_data).to_csv("data/faq.csv", index=False)
            print("サンプルFAQデータを作成しました。")
        
        # CSVからデータを読み込む
        df = pd.read_csv("data/faq.csv")
        print(f"{len(df)}個のFAQエントリを読み込みました。")
        
        # テストモードでのダミーエンベディング生成
        import hashlib
        embeddings = []
        
        for question in df["question"]:
            # テキストのハッシュ値を使って擬似的に一貫性のあるベクトルを生成
            hash_obj = hashlib.md5(question.encode())
            hash_val = int(hash_obj.hexdigest(), 16)
            np.random.seed(hash_val)
            embeddings.append(np.random.rand(1536).tolist())  # 1536次元のランダムなベクトル
            print(f"テスト用エンベディング生成: '{question[:30]}...'")
        
        # エンベディングをデータフレームに追加
        df["embedding"] = embeddings
        
        # PKLファイルとして保存
        df.to_pickle("data/faq_with_embeddings.pkl")
        print("テスト用FAQデータとエンベディングを保存しました。")
        return
    
    # 本番モード
    # APIキーのロード
    client = load_api_key()
    
    # クライアントがNoneの場合（APIキーがない場合）
    if client is None:
        print("APIキーの読み込みに失敗しました。テストモードに切り替えます。")
        os.environ["TEST_MODE"] = "true"
        create_embeddings()  # テストモードで再帰的に呼び出し
        return
    
    # データディレクトリの確認
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # CSVファイルの確認
    if not os.path.exists("data/faq.csv"):
        # サンプルデータを作成
        sample_data = {
            "question": [
                "チェックインの時間は何時ですか？",
                "駐車場はありますか？",
                "Wi-Fiは利用できますか？",
                "食事のアレルギー対応はできますか？"
            ],
            "answer": [
                "チェックインは15:00〜19:00です。事前にご連絡いただければ、遅いチェックインにも対応可能です。",
                "はい、無料の駐車場を提供しています。大型車の場合は事前にご連絡ください。",
                "全客室でWi-Fiを無料でご利用いただけます。接続情報はチェックイン時にお渡しします。",
                "はい、アレルギーがある場合は予約時にお知らせください。可能な限り対応いたします。"
            ]
        }
        pd.DataFrame(sample_data).to_csv("data/faq.csv", index=False)
        print("サンプルFAQデータを作成しました。")
    
    # CSVからデータを読み込む
    df = pd.read_csv("data/faq.csv")
    print(f"{len(df)}個のFAQエントリを読み込みました。")
    
    # エンベディングの生成
    embeddings = []
    
    for question in df["question"]:
        try:
            response = client.embeddings.create(
                model="claude-3-haiku-20240307",
                input=question
            )
            embeddings.append(response.embedding)
            print(f"エンベディング生成: '{question[:30]}...'")
        except Exception as e:
            print(f"エンベディング生成エラー: {e}")
            # エラーが発生した場合はダミーのエンベディングを追加
            embeddings.append([0] * 1536)
    
    # エンベディングをデータフレームに追加
    df["embedding"] = embeddings
    
    # PKLファイルとして保存
    df.to_pickle("data/faq_with_embeddings.pkl")
    print("FAQデータとエンベディングを保存しました。")

if __name__ == "__main__":
    create_embeddings()