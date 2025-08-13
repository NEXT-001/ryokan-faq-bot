# 検索履歴クリーンアップツール

## 概要

検索履歴が膨大になることを防ぐため、指定した期間より古いデータを削除するスクリプトです。

## ファイル構成

- `cleanup_search_history.py` - メインの削除スクリプト
- `setup_history_cleanup_cron.sh` - 定期実行設定用スクリプト
- `README_HISTORY_CLEANUP.md` - このドキュメント

## 基本的な使用方法

### 1. 現在の統計確認

```bash
python scripts/cleanup_search_history.py --stats-only
```

### 2. 削除対象のプレビュー

```bash
# 30日より古いデータの削除対象を確認
python scripts/cleanup_search_history.py --days 30 --preview-only

# 特定企業の削除対象を確認
python scripts/cleanup_search_history.py --days 30 --company demo-company --preview-only
```

### 3. 実際の削除実行

```bash
# 30日より古いデータを削除（確認あり）
python scripts/cleanup_search_history.py --days 30

# バックアップ付きで削除
python scripts/cleanup_search_history.py --days 30 --backup backup_20250813.csv

# 確認なしで削除
python scripts/cleanup_search_history.py --days 30 --force
```

## オプション詳細

| オプション | 短縮形 | 説明 | デフォルト |
|-----------|--------|------|------------|
| `--days` | `-d` | 削除対象の日数 | 30 |
| `--company` | `-c` | 対象企業ID | 全企業 |
| `--backup` | `-b` | バックアップファイルパス | なし |
| `--force` | `-f` | 確認なしで実行 | False |
| `--stats-only` | - | 統計のみ表示 | False |
| `--preview-only` | - | プレビューのみ表示 | False |

## 使用例

### 基本的な削除

```bash
# 30日より古い履歴を削除
python scripts/cleanup_search_history.py --days 30

# 90日より古い履歴を削除
python scripts/cleanup_search_history.py --days 90
```

### 企業別削除

```bash
# 特定企業の60日より古い履歴を削除
python scripts/cleanup_search_history.py --days 60 --company demo-company
```

### バックアップ付き削除

```bash
# バックアップを作成してから削除
python scripts/cleanup_search_history.py --days 30 --backup /path/to/backup_20250813.csv
```

### 自動化（確認なし）

```bash
# 確認なしで自動削除
python scripts/cleanup_search_history.py --days 30 --force
```

## 定期実行の設定

### crontabによる自動実行

```bash
# 設定スクリプトを実行
bash scripts/setup_history_cleanup_cron.sh
```

### 推奨設定例

```bash
# 毎週日曜日午前2時に30日より古い履歴を削除
0 2 * * 0 cd /path/to/project && python scripts/cleanup_search_history.py --days 30 --force

# 毎日午前3時に90日より古い履歴を削除
0 3 * * * cd /path/to/project && python scripts/cleanup_search_history.py --days 90 --force

# 毎月1日に180日より古い履歴を削除（バックアップ付き）
0 1 1 * * cd /path/to/project && python scripts/cleanup_search_history.py --days 180 --backup /backup/history_$(date +%Y%m).csv --force
```

## データ保持ポリシーの推奨設定

### 小規模運用（数社〜10社程度）
- **削除間隔**: 90日
- **実行頻度**: 週1回
- **バックアップ**: 推奨

```bash
python scripts/cleanup_search_history.py --days 90 --backup weekly_backup.csv --force
```

### 中規模運用（10社〜50社程度）
- **削除間隔**: 60日
- **実行頻度**: 週2回
- **バックアップ**: 必須

```bash
python scripts/cleanup_search_history.py --days 60 --backup backup_$(date +%Y%m%d).csv --force
```

### 大規模運用（50社以上）
- **削除間隔**: 30日
- **実行頻度**: 毎日
- **バックアップ**: 重要データのみ

```bash
python scripts/cleanup_search_history.py --days 30 --force
```

## バックアップファイル形式

バックアップファイルはCSV形式で以下の列を含みます：

- `company_id` - 企業ID
- `user_info` - ユーザー情報（部屋番号など）
- `question` - 質問内容
- `answer` - 回答内容
- `input_tokens` - 入力トークン数
- `output_tokens` - 出力トークン数
- `created_at` - 作成日時

## 注意事項

### セキュリティ
- バックアップファイルには機密情報が含まれる可能性があります
- バックアップファイルの保存場所とアクセス権限に注意してください

### パフォーマンス
- 大量のデータを削除する際は、データベースのロックに注意してください
- 本番環境では業務時間外での実行を推奨します

### データ復旧
- 一度削除されたデータは復旧できません
- 重要なデータは必ずバックアップを取ってから削除してください

## トラブルシューティング

### よくある問題

#### 1. 権限エラー
```bash
# 実行権限を付与
chmod +x scripts/cleanup_search_history.py
```

#### 2. データベース接続エラー
```bash
# 環境変数の確認
python -c "import os; print('DB_TYPE:', os.getenv('DB_TYPE', 'sqlite'))"
```

#### 3. バックアップディレクトリが存在しない
```bash
# ディレクトリを作成
mkdir -p /path/to/backup/directory
```

### ログの確認

```bash
# 実行ログを確認
tail -f logs/history_cleanup.log
```

## 関連コマンド

### 統計情報の確認
```bash
# 全体統計
python scripts/cleanup_search_history.py --stats-only

# 企業別統計
python scripts/cleanup_search_history.py --company demo-company --stats-only
```

### 削除対象の詳細確認
```bash
# 30日より古いデータの詳細
python scripts/cleanup_search_history.py --days 30 --preview-only

# 特定企業の削除対象
python scripts/cleanup_search_history.py --days 30 --company demo-company --preview-only
```