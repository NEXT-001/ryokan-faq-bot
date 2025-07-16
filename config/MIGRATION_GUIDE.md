# 設定管理統合 - 移行ガイド

## 概要

設定管理の重複問題を解決するため、以下のファイルの機能を `config/unified_config.py` に統合しました：

- `config/settings.py`
- `config/app_config.py`
- `utils/constants.py` の設定関連部分

## 変更内容

### 新しい統一設定クラス

`config/unified_config.py` に `UnifiedConfig` クラスを作成し、すべての設定管理機能を統合しました。

```python
from config.unified_config import UnifiedConfig

# 使用例
if UnifiedConfig.is_test_mode():
    print("テストモードで実行中")

data_path = UnifiedConfig.get_data_path("demo-company")
client = UnifiedConfig.load_anthropic_client()
```

### 主要な機能

#### 設定値の取得
- `UnifiedConfig.is_test_mode()` - テストモード判定
- `UnifiedConfig.has_api_keys()` - APIキー設定確認
- `UnifiedConfig.get_data_path(company_id)` - データパス取得

#### ページ設定
- `UnifiedConfig.get_url_params()` - URLパラメータ取得
- `UnifiedConfig.configure_page(mode)` - ページ設定

#### APIクライアント
- `UnifiedConfig.load_anthropic_client()` - Anthropicクライアント作成

#### バリデーション
- `UnifiedConfig.validate_company_id(company_id)` - 会社ID検証
- `UnifiedConfig.validate_email(email)` - メールアドレス検証

## 移行済みファイル

### `core/app_router.py`
- `from config.app_config import get_url_params, configure_page, AppConfig` 
  → `from config.unified_config import UnifiedConfig`
- `get_url_params()` → `UnifiedConfig.get_url_params()`
- `configure_page(mode)` → `UnifiedConfig.configure_page(mode)`
- `AppConfig.is_test_mode()` → `UnifiedConfig.is_test_mode()`

### `admin_faq_management.py`
- `from config.settings import get_data_path`
  → `from config.unified_config import UnifiedConfig`
- `get_data_path()` → `UnifiedConfig.get_data_path()`

## 後方互換性

既存のファイルは非推奨としてマークされていますが、後方互換性のために残されています：

- `config/settings.py` - 非推奨警告付きで残存
- `config/app_config.py` - 非推奨警告付きで残存
- `utils/constants.py` - 純粋な定数のみに整理

## 今後の作業

### 推奨される追加移行

1. **他のファイルの更新**
   - `services/` 配下のファイルで古い設定インポートを使用している箇所
   - `pages/` 配下のファイルで古い設定インポートを使用している箇所
   - `utils/` 配下のファイルで古い設定インポートを使用している箇所

2. **完全移行後のクリーンアップ**
   - 古い設定ファイルの削除（十分なテスト後）
   - `utils/constants.py` の設定関連関数の削除

### 移行手順

1. 対象ファイルで古いインポートを特定
2. `from config.unified_config import UnifiedConfig` に変更
3. 関数呼び出しを `UnifiedConfig.メソッド名()` 形式に変更
4. テストして動作確認

## 利点

- **重複の排除**: 同じ機能が複数ファイルに散らばっていた問題を解決
- **一元管理**: すべての設定が一箇所で管理される
- **保守性向上**: 設定変更時の影響範囲が明確
- **型安全性**: クラスメソッドによる明確なインターフェース

## 注意事項

- 新しいコードでは必ず `UnifiedConfig` を使用してください
- 古い設定ファイルは段階的に廃止予定です
- 移行時は十分なテストを行ってください
