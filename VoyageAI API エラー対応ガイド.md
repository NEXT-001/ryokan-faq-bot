# VoyageAI API エラー対応ガイド

## 発生したエラー

以下のエラーメッセージが表示されています：

```
VoyageAI APIクライアント初期化成功
VoyageAIエンベディング取得エラー: You have not yet added your payment method in the billing page and will have reduced rate limits of 3 RPM and 10K TPM. To unlock our standard rate limits, please add a payment method in the billing page for the appropriate organization in the user dashboard (https://dashboard.voyageai.com/). Even with payment methods entered, the free tokens (200M tokens for Voyage series 3) will still apply. After adding a payment method, you should see your rate limits increase after several minutes. See our pricing docs (https://docs.voyageai.com/docs/pricing) for the free tokens for your model.
```

## エラーの原因

このエラーは、VoyageAI APIのレート制限（Rate Limit）に関する警告です。支払い方法を登録していないため、APIの使用に制限がかかっています：

- 現在の制限：3 RPM（分あたり3リクエスト）、10K TPM（分あたり10,000トークン）
- これらの制限は、APIの通常の利用には不十分な場合があります

## 対応策

### 1. VoyageAIダッシュボードで支払い方法を追加する（推奨）

最も簡単な解決策は、VoyageAIダッシュボードで支払い方法を追加することです：

1. [VoyageAI Dashboard](https://dashboard.voyageai.com/)にアクセス
2. アカウントにログイン
3. 課金ページ（Billing）に移動
4. 支払い方法を追加

**注意**: 支払い方法を追加しても、無料枠（Voyage series 3の場合は200Mトークン）が適用されます。また、支払い方法を追加してからレート制限が緩和されるまで数分かかる場合があります。

### 2. システムをテストモードで実行する（一時的な対策）

支払い方法を追加できない場合や、開発/テスト段階では、システムをテストモードで実行することで、VoyageAI APIを使用せずにシステムをテストできます：

1. `.env`ファイルで`TEST_MODE=true`を設定
2. または管理画面で「テストモード」を有効化

テストモードでは、APIを呼び出す代わりに擬似的なエンベディングが生成されます。これにより、実際のAPIを使用せずにシステムの機能をテストできます。

### 3. コードの修正（エラー耐性の向上）

エンベディングサービスを修正し、レート制限エラーに対するリトライ機能と、より適切なフォールバック処理を実装しました：

- 各API呼び出しに最大3回のリトライ（設定可能）
- エラー時には一定時間待機してからリトライ（デフォルトは20秒）
- すべてのリトライが失敗した場合は自動的にテストモードに切り替え

## 設定パラメータ

`.env`ファイルで以下の設定を変更できます：

```ini
# テストモード設定
TEST_MODE=true

# API呼び出し制限対策設定
MAX_RETRIES=3   # リトライ最大回数
RETRY_DELAY=20  # リトライ間隔（秒）
```

## 本番環境での推奨設定

本番環境では以下の設定を推奨します：

1. VoyageAIアカウントに支払い方法を追加する
2. `.env`ファイルで`TEST_MODE=false`を設定
3. 十分なリトライ回数（`MAX_RETRIES=3`以上）を設定

## デモ/テスト環境での推奨設定

デモやテスト環境では以下の設定を推奨します：

1. `.env`ファイルで`TEST_MODE=true`を設定
2. これにより、APIを使用せずにシステムの機能を確認できます