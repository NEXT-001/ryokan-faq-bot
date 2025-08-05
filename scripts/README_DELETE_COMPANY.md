# 会社データ削除スクリプト

テスト時にメールアドレスを再利用するために、会社データを完全に削除するスクリプトです。

## 📋 削除されるデータ

| テーブル名 | 説明 | 削除条件 |
|-----------|------|----------|
| `faq_embeddings` | FAQエンベディング | `faq_id IN (SELECT id FROM faq_data WHERE company_id = ?)` |
| `faq_data` | FAQ情報 | `company_id = ?` |
| `users` | ユーザー情報 | `company_id = ?` |
| `company_admins` | 管理者情報 | `company_id = ?` |
| `line_settings` | LINE設定 | `company_id = ?` |
| `search_history` | 検索履歴 | `company_id = ?` |
| `faq_history` | FAQ履歴 | `company_id = ?` |
| `companies` | 会社情報 | `id = ?` |
| ファイルシステム | CSVファイル等 | `data/companies/{company_id}/` |

## 🛠️ 使用方法

### 1. 会社一覧確認
```bash
python scripts/test_company_list.py
```

### 2. インタラクティブ削除（推奨）
```bash
python scripts/interactive_company_delete.py
```
- 会社一覧を表示
- 番号で選択
- 安全確認付き

### 3. 直接削除
```bash
python scripts/delete_company_data.py <company_id>
```

例：
```bash
python scripts/delete_company_data.py demo-company
python scripts/delete_company_data.py company_fc7b87b7
```

## ⚠️ 注意事項

1. **バックアップ**: 削除前に重要なデータはバックアップしてください
2. **不可逆**: 削除は不可逆的です。元に戻せません
3. **外部キー制約**: 正しい順序で削除するため、外部キー制約に対応しています
4. **ファイル削除**: データベースだけでなく、ファイルシステムのデータも削除されます

## 🔍 削除前チェック項目

- [ ] 削除対象の会社IDが正しいか確認
- [ ] 必要なデータのバックアップ済み
- [ ] テスト環境での実行か確認
- [ ] 関係者への連絡済み（本番環境の場合）

## 📧 メールアドレス再利用

削除完了後、該当する会社で使用していたメールアドレス（`users.email`）を新しいテスト登録で再利用できます。

## 🚨 トラブルシューティング

### エラー: "foreign key constraint failed"
- 削除順序に問題があります
- スクリプトが正しい順序で削除するよう設計されています

### エラー: "database is locked"
- アプリケーションが実行中の可能性があります
- Streamlitアプリを停止してから実行してください

### ファイル削除エラー
- ファイルが使用中の可能性があります
- 権限を確認してください

## 📊 削除結果例

```
🗑️  削除開始: demo-company
  1/8 faq_embeddings削除中...
  2/8 faq_data削除中...
  3/8 users削除中...
  4/8 company_admins削除中...
  5/8 line_settings削除中...
  6/8 search_history削除中...
  7/8 faq_history削除中...
  8/8 companies削除中...

✅ データベース削除完了:
  faq_embeddings: 42件削除
  faq_data: 42件削除
  users: 1件削除
  line_settings: 1件削除
  search_history: 321件削除
  companies: 1件削除

📁 ファイルシステム削除中: data/companies/demo-company/
  削除ファイル: faq.csv, faq_with_embeddings.pkl, history.csv
✅ ファイル削除完了

🎉 削除完了! 会社ID 'demo-company' の全データが削除されました
📧 関連するメールアドレスがテストで再利用可能になりました
```