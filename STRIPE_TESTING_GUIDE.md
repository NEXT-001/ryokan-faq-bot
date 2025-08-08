# Stripe決済システム テスト完全ガイド

## 📋 目次
1. [概要](#概要)
2. [事前準備](#事前準備)
3. [テスト環境設定](#テスト環境設定)
4. [決済フローテスト](#決済フローテスト)
5. [テストカード情報](#テストカード情報)
6. [自動テスト実行](#自動テスト実行)
7. [手動テスト手順](#手動テスト手順)
8. [トラブルシューティング](#トラブルシューティング)
9. [本番環境への移行](#本番環境への移行)

---

## 概要

このガイドでは、FAQチャットボットシステムに組み込まれたStripe決済機能のテスト方法を説明します。

### 🎯 テスト対象機能
- **サブスクリプション管理**: 月額プラン（無料・標準・PRO）
- **決済方法管理**: クレジットカードの追加・削除
- **請求管理**: 請求履歴・請求書表示
- **プラン変更**: アップグレード・ダウングレード
- **キャンセル処理**: サブスクリプション解約

---

## 事前準備

### 1. Stripe SDKのインストール
```bash
pip install stripe
```

### 2. 必要なアカウント
- **Stripeテストアカウント**: [stripe.com](https://stripe.com) でアカウント作成
- **APIキーの取得**: ダッシュボードから「テスト用」のAPIキーを取得

### 3. 環境変数の設定
`.env`ファイルに以下を追加：
```env
# Stripeテスト環境設定
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxx
```

⚠️ **重要**: `sk_test_` と `pk_test_` で始まるキーを使用してください（本番用キーは使用禁止）

---

## テスト環境設定

### 1. Stripeダッシュボードの確認
1. [Stripe Dashboard](https://dashboard.stripe.com/test) にログイン
2. **テストモード**になっていることを確認（左上のトグル）
3. 「API」セクションでテスト用APIキーを確認

### 2. Webhook設定（オプション）
```
Webhook URL: https://your-domain.com/stripe/webhook
イベント: 
- payment_intent.succeeded
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.payment_succeeded
- invoice.payment_failed
```

### 3. 環境変数の確認
```bash
python -c "
import os
print('🔍 Stripe設定確認:')
secret = os.getenv('STRIPE_SECRET_KEY', '')
public = os.getenv('STRIPE_PUBLISHABLE_KEY', '')
print(f'Secret Key: {\"✅ テスト\" if secret.startswith(\"sk_test_\") else \"❌ 無効\"}')
print(f'Public Key: {\"✅ テスト\" if public.startswith(\"pk_test_\") else \"❌ 無効\"}')
"
```

---

## 決済フローテスト

### 基本的な決済フロー
```
1. 顧客登録 → 2. 決済方法追加 → 3. プラン選択 → 4. サブスクリプション作成 → 5. 請求処理
```

### 各ステップの詳細テスト

#### 1. 顧客登録テスト
```python
# テストコード例
from services.payment_service import PaymentService

service = PaymentService()
company_info = {
    "company_id": "test-company-001",
    "name": "テスト会社株式会社",
    "email": "test@example.com"
}

customer = service.create_customer(company_info)
print(f"顧客ID: {customer.id}")
```

#### 2. 決済方法追加テスト
```python
# テスト用カード情報
test_card = {
    "number": "4242424242424242",  # Visa (成功)
    "exp_month": 12,
    "exp_year": 2025,
    "cvc": "123",
    "cardholder_name": "Test User"
}

payment_method = service.create_payment_method(test_card)
service.attach_payment_method(payment_method.id, customer.id)
```

#### 3. サブスクリプション作成テスト
```python
# 価格の作成
price = service.create_price("標準", 1980)

# サブスクリプション作成
subscription = service.create_subscription(customer.id, price.id)
print(f"サブスクリプション: {subscription.id}")
print(f"ステータス: {subscription.status}")
```

---

## テストカード情報

### ✅ 成功するテストカード
| カード番号 | ブランド | 用途 |
|------------|----------|------|
| 4242424242424242 | Visa | 基本的な成功テスト |
| 4000056655665556 | Visa (debit) | デビットカードテスト |
| 5555555555554444 | Mastercard | Mastercard成功テスト |
| 2223003122003222 | Mastercard | Mastercard 2-series |
| 4000002500003155 | Visa | 3D Secure認証が必要 |

### ❌ 失敗するテストカード
| カード番号 | エラータイプ | 用途 |
|------------|-------------|------|
| 4000000000000002 | card_declined | カード拒否テスト |
| 4000000000000069 | expired_card | 期限切れカードテスト |
| 4000000000000127 | incorrect_cvc | CVC不正テスト |
| 4000000000000119 | processing_error | 処理エラーテスト |

### 💳 特殊なテストケース
```javascript
// 特定の金額でのテスト
{
  "amount": 1000,  // 10.00円 - 成功
  "amount": 2000,  // 20.00円 - card_declined
  "amount": 3000,  // 30.00円 - insufficient_funds
}
```

---

## 自動テスト実行

### 1. テストスイートの実行
```bash
python tests/stripe_payment_test.py
```

### 2. テスト結果の確認
テスト実行後、以下のファイルが生成されます：
- `data/logs/stripe_test_results_YYYYMMDD_HHMMSS.json`
- `data/logs/stripe_test_results_YYYYMMDD_HHMMSS_report.md`

### 3. カバレッジテスト
```bash
# すべての決済機能をテスト
python -c "
from tests.stripe_payment_test import StripePaymentTester
tester = StripePaymentTester()
results = tester.run_all_tests()
print(f'成功率: {results[\"summary\"][\"success_rate\"]:.1f}%')
"
```

---

## 手動テスト手順

### 1. 管理画面での決済設定テスト

#### ステップ1: 管理画面にアクセス
```
URL: http://localhost:8501/?mode=admin&company=demo-company
ログイン: admin / admin123
```

#### ステップ2: 決済管理画面に移動
1. サイドバーから「💳 決済管理」を選択
2. 現在のプラン情報を確認

#### ステップ3: 決済方法の追加
1. 「新しい決済方法を追加」ボタンをクリック
2. テストカード情報を入力：
   ```
   カード番号: 4242 4242 4242 4242
   有効期限: 12/25
   CVC: 123
   名義人: Test User
   ```
3. 「決済方法を追加」ボタンをクリック

#### ステップ4: プラン変更テスト
1. 「標準プラン」または「PROプラン」の「変更」ボタンをクリック
2. 確認画面で「確定」をクリック
3. 決済処理の完了を確認

### 2. エラーケースのテスト

#### 拒否されるカードのテスト
```
カード番号: 4000 0000 0000 0002
期待結果: 「カード情報が正しくありません」エラー
```

#### 期限切れカードのテスト
```
カード番号: 4000 0000 0000 0069
期待結果: 「カードの有効期限が切れています」エラー
```

### 3. Stripeダッシュボードでの確認

#### 確認項目
1. **顧客**: 新しい顧客が作成されているか
2. **決済方法**: カードが正しく登録されているか
3. **サブスクリプション**: アクティブなサブスクリプションが作成されているか
4. **請求書**: 請求書が正しく生成されているか

---

## トラブルシューティング

### ❌ よくある問題と解決方法

#### 1. "Stripe SDKが利用できません"
**原因**: Stripe SDKがインストールされていない
**解決方法**:
```bash
pip install stripe
```

#### 2. "STRIPE_SECRET_KEYが設定されていません"
**原因**: 環境変数が設定されていない
**解決方法**:
```bash
echo 'STRIPE_SECRET_KEY=sk_test_your_key_here' >> .env
echo 'STRIPE_PUBLISHABLE_KEY=pk_test_your_key_here' >> .env
```

#### 3. "API呼び出しエラー"
**原因**: APIキーが無効、またはネットワーク接続の問題
**解決方法**:
1. APIキーが正しいことを確認
2. インターネット接続を確認
3. Stripeのサービス状態を確認: [status.stripe.com](https://status.stripe.com)

#### 4. "カード情報が正しくありません"
**原因**: テストカード以外を使用、またはフォーマットエラー
**解決方法**:
1. 推奨テストカード（4242424242424242）を使用
2. カード番号にスペースが含まれていないことを確認

#### 5. "決済方法の作成に失敗しました"
**原因**: Stripe APIの制限、またはカード情報の不備
**解決方法**:
1. APIレート制限を確認
2. カード情報の形式を確認
3. Stripeダッシュボードでエラーログを確認

### 🔧 デバッグ方法

#### ログレベルの変更
```python
import logging
logging.getLogger('stripe').setLevel(logging.DEBUG)
```

#### APIレスポンスの詳細確認
```python
import stripe
stripe.log = 'debug'  # 詳細なAPIログを出力
```

---

## 本番環境への移行

### 1. 本番APIキーへの変更
```env
# 本番環境設定（注意：テスト完了後のみ）
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxx
```

### 2. 本番前チェックリスト
- [ ] すべてのテストが成功することを確認
- [ ] エラーハンドリングが適切に動作することを確認  
- [ ] Webhook設定が正しいことを確認
- [ ] 決済フローの端から端までのテストを実施
- [ ] セキュリティ要件を満たしていることを確認

### 3. 本番監視項目
- 決済成功率
- エラー発生率
- サブスクリプション継続率
- 請求書発行状況
- 顧客からの問い合わせ

---

## 📊 テスト結果の評価基準

### ✅ 成功基準
- **機能テスト**: 全機能が期待通りに動作する
- **エラーハンドリング**: 適切なエラーメッセージが表示される
- **パフォーマンス**: 決済処理が3秒以内に完了する
- **セキュリティ**: 機密情報が適切に保護される

### ⚠️ 注意事項
- **テスト環境のみ使用**: 本番APIキーは絶対に使用しない
- **データの管理**: テストデータは定期的に削除する
- **ログの確認**: エラーログを定期的に確認する
- **更新の確認**: Stripe SDKを定期的に更新する

---

## 🔗 関連リソース

- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Testing Guide](https://stripe.com/docs/testing)
- [Stripe Dashboard](https://dashboard.stripe.com/test)
- [Stripe Status Page](https://status.stripe.com)

---

## 📞 サポート

テストで問題が発生した場合：

1. **エラーログの確認**: `data/logs/` ディレクトリのログファイル
2. **Stripeダッシュボード**: エラーの詳細を確認
3. **このガイドの確認**: トラブルシューティングセクション
4. **Stripeサポート**: [support.stripe.com](https://support.stripe.com)

---

**最終更新**: 2025年8月8日  
**バージョン**: 1.0.0