# 依存関係管理ガイド
# Dependency Management Guide

## 概要 / Overview

このプロジェクトでは、明確で保守しやすい依存関係管理のために2つのrequirementsファイルを使用しています。

This project uses two requirements files for clear and maintainable dependency management.

## ファイル構成 / File Structure

### 1. `requirements.txt` - 本番環境用
**用途**: 本番環境・デプロイ用の必須依存関係
**使用場面**:
- 本番環境へのデプロイ時
- Heroku、Railway、Streamlit Cloudなどのクラウドプラットフォーム
- Dockerコンテナでの実行時
- 最小限の環境でアプリケーションを実行する場合

**インストール方法**:
```bash
pip install -r requirements.txt
```

### 2. `requirements-dev.txt` - 開発環境用
**用途**: 開発・テスト・デバッグ用の追加依存関係
**含まれる内容**:
- `requirements.txt`の全ての依存関係（`-r requirements.txt`で継承）
- テストツール（pytest, pytest-cov, pytest-mock）
- コード品質ツール（black, flake8, isort, mypy）
- 開発ツール（jupyter, ipdb, pre-commit）
- データ可視化ライブラリ（matplotlib, seaborn）

**使用場面**:
- ローカル開発環境
- テストの実行
- コード品質チェック
- データ分析・プロトタイピング

**インストール方法**:
```bash
pip install -r requirements-dev.txt
```

## 使い分けガイド / Usage Guide

| 環境 / Environment | 使用ファイル / File to Use | 理由 / Reason |
|-------------------|-------------------------|---------------|
| 本番環境 / Production | `requirements.txt` | 必要最小限の依存関係でセキュリティとパフォーマンスを最適化 |
| 開発環境 / Development | `requirements-dev.txt` | 開発に必要な全てのツールを含む |
| CI/CD | `requirements-dev.txt` | テストとコード品質チェックのため |
| Docker本番 / Docker Prod | `requirements.txt` | イメージサイズを最小化 |
| Docker開発 / Docker Dev | `requirements-dev.txt` | 開発ツールを含む |

## メンテナンス方法 / Maintenance

### 新しい依存関係の追加
1. **本番環境で必要な場合**: `requirements.txt`に追加
2. **開発環境でのみ必要な場合**: `requirements-dev.txt`に追加

### バージョン更新
1. 両方のファイルで一貫したバージョン範囲を使用
2. セマンティックバージョニングに従ってバージョン範囲を指定
3. 例: `package>=1.0.0,<2.0.0`（メジャーバージョンを固定）

### 依存関係の削除
1. 使用されていないパッケージを定期的に確認
2. 削除前に影響範囲を確認
3. テストを実行して問題がないことを確認

## ベストプラクティス / Best Practices

### 1. バージョン固定
- 上限と下限を指定してバージョン範囲を制限
- 予期しない破壊的変更を防ぐ

### 2. 定期的な更新
- 月1回程度の頻度で依存関係を確認・更新
- セキュリティアップデートは優先的に適用

### 3. テスト
- 依存関係更新後は必ずテストを実行
- 本番環境と同じ条件でのテストを推奨

### 4. ドキュメント
- 新しい依存関係を追加する際は理由をコメントで記載
- 重要な依存関係の変更はCHANGELOGに記録

## トラブルシューティング / Troubleshooting

### 依存関係の競合
```bash
# 現在の依存関係を確認
pip list

# 競合を解決
pip install --upgrade package_name

# 仮想環境をクリーンアップ
pip freeze > temp_requirements.txt
pip uninstall -r temp_requirements.txt -y
pip install -r requirements-dev.txt
```

### パッケージが見つからない
1. パッケージ名のスペルを確認
2. PyPIで利用可能性を確認
3. 代替パッケージを検討

## 関連ファイル / Related Files

- `runtime.txt`: Pythonバージョンの指定（Heroku用）
- `.python-version`: pyenvでのPythonバージョン管理
- `pyproject.toml`: 将来的な依存関係管理の移行先候補

---

**最終更新**: 2025年7月16日
**更新者**: システム管理者
