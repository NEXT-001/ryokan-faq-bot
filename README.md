# Ryokan FAQ Bot - セットアップガイド

## 概要

Ryokan FAQ Botは、日本の旅館・ホテル業界向けに特化したマルチテナント対応のFAQチャットボットシステムです。複数の宿泊施設が独自のFAQデータを管理し、お客様がウェブインターフェースから質問できるシステムです。各施設は独自の管理者アカウントを持ち、FAQ管理や利用履歴の確認、決済管理が可能です。

### 主な特徴

- **マルチテナント対応**: 各宿泊施設が独自のFAQデータを管理
- **AI搭載回答システム**: Anthropic Claude + VoyageAI による意味理解ベースの回答
- **セキュアな管理**: 施設ごとの管理者アカウントによる独立したデータ管理
- **簡単なデータ管理**: CSVインポート/エクスポート対応
- **決済管理**: 支払い履歴と請求管理機能
- **LINE連携**: LINE Bot統合によるマルチチャネル対応
- **メール認証**: 安全なユーザー登録とアカウント管理
- **自動テストモード**: APIキー不要での開発・テスト環境

## システム要件

- Python 3.8以上
- 以下のPythonパッケージ:
  - streamlit
  - pandas
  - numpy
  - scikit-learn
  - python-dotenv
  - anthropic (オプション)
  - voyageai (オプション、エンベディング生成用)

## インストール手順

1. リポジトリをクローンまたはダウンロードする
2. 必要なパッケージをインストールする:
   
   **本番環境・デプロイ用**:
   ```bash
   pip install -r requirements.txt
   ```
   
   **開発環境用（テスト・デバッグツール含む）**:
   ```bash
   pip install -r requirements-dev.txt
   ```
   
   > 📋 **依存関係の詳細**: [DEPENDENCY_MANAGEMENT.md](DEPENDENCY_MANAGEMENT.md) を参照してください

3. フォルダ構造の初期化:
   ```bash
   mkdir -p data/companies/demo-company
   ```

## 設定方法

### 基本設定

`.env` ファイルを作成し、以下の設定を行います:

```
TEST_MODE=true
VOYAGE_API_KEY=your_api_key_here  # オプション
ANTHROPIC_API_KEY=your_api_key_here  # オプション
```

- `TEST_MODE`: `true` に設定すると、実際のAPIを使わずにテストデータで動作します
- `VOYAGE_API_KEY`: VoyageAI APIのキー (エンベディング生成用、オプション)
- `ANTHROPIC_API_KEY`: Anthropic APIのキー (拡張機能用、オプション)

### テストモードについて

テストモードでは、エンベディングAPIを呼び出さずに擬似的なエンベディングを生成します。実運用環境ではVoyageAI APIキーの設定を推奨しますが、小規模な利用ではテストモードでも十分機能します。

## 実行方法

### 1. 埋め込みベクトル生成（初回または FAQ 更新時）
```bash
python -m services.embedding_service
```

### 2. アプリケーション起動
```bash
# 推奨方法
streamlit run app.py

# レガシー対応（従来の方法）
streamlit run main.py
```

ブラウザが自動的に開き、アプリケーションにアクセスできます。通常は `http://localhost:8501` でアクセス可能です。

## 初期アカウント

システムは以下のアカウントを使用できます:

- **スーパー管理者**（テストモードのみ）:
  - 企業ID: `admin`
  - ユーザー名: `admin`
  - パスワード: `admin`

- **デモ宿泊施設管理者**:
  - 企業ID: `demo-company`
  - ユーザー名: `admin`
  - パスワード: `admin123`

## 使用方法

### 顧客向けインターフェース

1. トップページで企業を選択
2. 質問を入力し、回答を受け取る
3. 会話履歴は一時的に保存され、セッション間で保持されない

### 管理者インターフェース

1. **ログイン**: メールアドレスとパスワードでログイン
2. **FAQ管理**: 質問と回答の追加、編集、削除
3. **FAQ履歴**: お客様の質問と回答の履歴確認
4. **LINE通知設定**: LINE Bot連携の設定
5. **管理者設定**: 施設管理者アカウントの追加/削除
6. **FAQプレビュー**: FAQ表示のテスト
7. **決済管理**: 支払い履歴と請求管理

### スーパー管理者インターフェース

1. **企業管理**: 新規宿泊施設と管理者の登録
2. **FAQデモ**: 各施設のFAQをテスト

## フォルダ構造

```
ryokan-faq-bot/
├── app.py                  # メインアプリケーション (推奨)
├── main.py                 # レガシー互換エントリーポイント
├── config/
│   ├── app_config.py       # アプリケーション設定
│   └── settings.py         # システム設定
├── core/
│   ├── app_router.py       # URL ルーティング
│   └── database.py         # データベース管理
├── pages/
│   ├── user_page.py        # お客様向けページ
│   ├── admin_page.py       # 管理者ページ
│   ├── registration_page.py # 新規登録ページ
│   └── verify_page.py      # メール認証ページ
├── services/
│   ├── chat_service.py     # チャット回答サービス
│   ├── company_service.py  # 施設管理サービス
│   ├── embedding_service.py # ベクトル埋め込み生成
│   ├── history_service.py  # 履歴管理
│   ├── login_service.py    # ログイン認証
│   ├── email_service.py    # メール送信
│   ├── line_service.py     # LINE Bot連携
│   └── payment_service.py  # 決済管理
├── utils/
│   ├── auth_utils.py       # 認証ユーティリティ
│   ├── company_utils.py    # 施設ユーティリティ
│   └── db_utils.py         # データベースユーティリティ
├── data/
│   ├── faq_database.db     # SQLite データベース
│   └── companies/          # 施設別データフォルダ
│       └── demo-company/   # デモ施設のデータ
│           ├── faq.csv     # FAQデータ
│           ├── faq_with_embeddings.pkl
│           └── history.csv # 利用履歴
└── requirements.txt        # 依存関係
```

## トラブルシューティング

### APIキーの問題

- VoyageAI または Anthropic APIキーが設定されていない場合、システムは自動的にテストモードに切り替わります
- テストモードでは簡易的なエンベディングとキーワードベース回答を使用するため、AI機能の精度が低下します
- 本格運用時は両方のAPIキーの設定を推奨します

### データファイルの問題

- データフォルダが存在しない場合は自動的に作成されます
- 施設データが見つからない場合はデフォルトデータが生成されます
- SQLite データベースは初回起動時に自動作成されます

### 認証・ログインの問題

- メール認証が機能しない場合は .env ファイルのメール設定を確認してください
- パスワードハッシュ化に関するエラーが発生した場合は依存関係を再インストールしてください

### その他の問題

- システムのログを確認して問題を特定してください
- テストモードで問題が解決するか確認してください
- ブラウザのキャッシュをクリアしてページを再読み込みしてください
