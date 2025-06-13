# 🏨 旅館FAQチャットボット

旅館に関するよくある質問に自動で回答するチャットボットアプリケーションです。Streamlitとセマンティック検索を使用して、ユーザーの質問に最も関連性の高い回答を提供します。

## 機能

- 📝 よくある質問への自動回答
- 🔍 セマンティック検索による関連性の高い回答
- 📊 利用履歴の記録と表示
- 🔐 ユーザー認証と管理機能
- 📱 レスポンシブなWebインターフェース

## インストール方法

```bash
# リポジトリのクローン
git clone https://github.com/kangju80/ryokan-faq-bot.git
cd ryokan-faq-bot

# PowerShell
myenv\Scripts\Activate.ps1

# 必要なパッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
# .envファイルを作成し、ANTHROPIC_API_KEYを設定してください
```

## 使用方法

```bash
# エンベディングの生成（初回または質問データ更新時）
python -m services.embedding_service

# アプリケーションの起動
streamlit run main.py
```

## デプロイ方法

このアプリケーションはStreamlit Cloudにデプロイできます。詳細は[公式ドキュメント](https://docs.streamlit.io/streamlit-cloud/get-started)を参照してください。

## デフォルトアカウント

初回起動時に以下のデフォルト管理者アカウントが作成されます：
- ユーザー名: `admin`
- パスワード: `admin123`

**重要:** 実運用環境では、このデフォルトパスワードを必ず変更してください。

## FAQ内容のカスタマイズ

`data/faq.csv`ファイルを編集することで、FAQの内容をカスタマイズできます。CSVファイルは以下の形式で作成してください：

```csv
question,answer
質問1,回答1
質問2,回答2
...
```

ファイル更新後は、`python -m services.embedding_service`を実行してエンベディングを再生成してください。

## ライセンス

MIT License

## 作者

Your Name


---
# 旅館FAQチャットボット テストモードの使用方法

テストモードを使用すると、Anthropic APIキーを取得せずにアプリケーションの基本機能をテストできます。テストモードでは、事前に定義されたいくつかの質問に対して回答できます。

## テストモードの有効化方法

テストモードを有効にするには、以下のいずれかの方法を使用します：

### 1. 環境変数で設定

`.env`ファイルに以下の設定を追加します：

```
TEST_MODE=true
```

または、APIキーを設定せずに空欄にすることでも自動的にテストモードになります：

```
ANTHROPIC_API_KEY=
```

### 2. 実行時に環境変数で設定

コマンドラインから実行する場合、環境変数を直接設定できます：

```bash
# Windows (Command Prompt)
set TEST_MODE=true
streamlit run main.py

# Windows (PowerShell)
$env:TEST_MODE="true"
streamlit run main.py

# macOS/Linux
TEST_MODE=true streamlit run main.py
```

### 3. 管理者UIから設定

管理者としてログインした場合、サイドバーにテストモードの切り替えチェックボックスが表示されます。これを使用して、テストモードのオン/オフを切り替えることができます。

## テストモードでのログイン

テストモードでは、以下のテスト用アカウントを使用できます：

1. 管理者アカウント：
   - ユーザー名: `admin`
   - パスワード: `admin`

2. 一般ユーザーアカウント：
   - ユーザー名: `user`
   - パスワード: `user`

## テストモードで対応可能なキーワード

テストモードでは、以下のキーワードに関連する質問に回答できます：

- チェックイン
- チェックアウト
- 駐車場
- Wi-Fi
- アレルギー
- 部屋
- 温泉
- 食事
- 子供
- 観光

例えば、「チェックインの時間は何時ですか？」と質問すると、テストモードでも適切な回答が得られます。

## 本番モードへの切り替え方法

テストが終了し、本番環境で使用する準備ができたら、以下の手順で本番モードに切り替えます：

1. `.env`ファイルで`TEST_MODE=false`に設定し、有効なAnthropicのAPIキーを追加します：

```
TEST_MODE=false
ANTHROPIC_API_KEY=sk-your-api-key-here
```

2. エンベディングを再生成します（実際のAPIを使用）：

```bash
python -m services.embedding_service
```

3. アプリケーションを再起動します：

```bash
streamlit run main.py
```

これにより、テストモードから本番モードに切り替わり、実際のAnthropicのAPIを使用した高品質な回答が得られるようになります。

## テストモードと本番モードの違い

| 機能 | テストモード | 本番モード |
|------|--------------|------------|
| APIキー | 不要 | 必須 |
| 回答生成 | キーワードベースのシンプルな回答 | 高度なセマンティック検索による精度の高い回答 |
| エンベディング | ダミーエンベディング（ハッシュベース） | 実際のAPIを使用した高品質なエンベディング |
| 対応質問 | 限定的（10種類のキーワード） | 全てのFAQデータに基づく（無制限） |
| ログイン | テスト用アカウントのみ | 実際のユーザーデータベース |

## テストモードの制限事項

テストモードには以下の制限があります：

1. 限られたキーワードにのみ反応します
2. 複雑な質問や文脈を理解する能力が制限されています
3. 類似性の判断がランダムなベクトルに基づいているため、精度が低い場合があります

これらの制限は本番モードでは解消されます。本番環境では、Anthropicの強力なAIモデルを活用して、より高度で正確な回答を提供します。

# ユーザーページ
http://localhost:8501?mode=user&company_id=demo-company

# 管理者ページ  
http://localhost:8501?mode=admin&company_id=demo-company

# 登録ページ
http://localhost:8501?mode=reg

# メール認証（自動生成）
http://localhost:8501?token=abc123...


📋 利用可能なモード

?mode=user&company_id=demo-company

FAQチャットボット画面
サイドバーなしのシンプルなインターフェース


?mode=admin&company_id=demo-company

FAQ管理者画面
ログイン機能付き
企業別の管理機能


?mode=reg

14日間無料お試し登録画面
companyパラメータは無視


?token=xxx

メール認証ページ
自動的にverifyモードに切り替わり
