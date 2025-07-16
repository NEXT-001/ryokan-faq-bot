# データベース設計問題の修正

## 問題の概要

`admin_faq_management.py` でデータベースとCSVファイルの両方を同期していたため、データの一貫性を保つのが困難でした。

## 修正内容

### 1. データベースファーストアプローチの採用

**修正前:**
- データベースとCSVファイルの両方を同期
- `save_faq_data()` 関数でCSVファイルも更新
- データの一貫性問題が発生

**修正後:**
- データベースを単一の真実の源（Single Source of Truth）として使用
- CSVファイルの同期を削除
- データの一貫性を保証

### 2. CRUD操作の最適化

#### FAQ追加 (`add_faq`)
**修正前:**
```python
# DataFrameを使用した非効率な方法
df = load_faq_data(company_id)
new_row = pd.DataFrame({"question": [question], "answer": [answer]})
df = pd.concat([df, new_row], ignore_index=True)
save_faq_data(df, company_id)  # 全データを再保存
```

**修正後:**
```python
# 直接データベースに挿入
insert_query = """
    INSERT INTO faq_data (company_id, question, answer, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?)
"""
execute_query(insert_query, (company_id, question, answer, current_time, current_time))
```

#### FAQ更新 (`update_faq`)
**修正前:**
```python
# DataFrameを使用した非効率な方法
df = load_faq_data(company_id)
df.at[index, "question"] = question
df.at[index, "answer"] = answer
save_faq_data(df, company_id)  # 全データを再保存
```

**修正後:**
```python
# 特定のレコードのみを更新
query = "SELECT id FROM faq_data WHERE company_id = ? ORDER BY created_at LIMIT 1 OFFSET ?"
result = fetch_dict_one(query, (company_id, index))
faq_id = result['id']

update_query = """
    UPDATE faq_data 
    SET question = ?, answer = ?, updated_at = ?
    WHERE id = ?
"""
execute_query(update_query, (question, answer, current_time, faq_id))
```

#### FAQ削除 (`delete_faq`)
**修正前:**
```python
# DataFrameを使用した非効率な方法
df = load_faq_data(company_id)
df = df.drop(index)
save_faq_data(df, company_id)  # 全データを再保存
```

**修正後:**
```python
# 特定のレコードのみを削除
query = "SELECT id FROM faq_data WHERE company_id = ? ORDER BY created_at LIMIT 1 OFFSET ?"
result = fetch_dict_one(query, (company_id, index))
faq_id = result['id']

delete_query = "DELETE FROM faq_data WHERE id = ?"
execute_query(delete_query, (faq_id,))
```

#### CSVインポート (`import_faq_from_csv`)
**修正前:**
```python
# DataFrameを使用した非効率な方法
current_df = load_faq_data(company_id)
combined_df = pd.concat([current_df, new_entries], ignore_index=True)
save_faq_data(combined_df, company_id)  # 全データを再保存
```

**修正後:**
```python
# 直接データベースに新しいエントリを追加
existing_questions_query = "SELECT question FROM faq_data WHERE company_id = ?"
existing_questions = fetch_dict(existing_questions_query, (company_id,))
existing_question_set = {row['question'] for row in existing_questions}

# 重複チェック後、新しいエントリのみを追加
for question, answer in new_entries:
    execute_query(insert_query, (company_id, question, answer, current_time, current_time))
```

### 3. CSVファイルの役割変更

**修正前:**
- CSVファイルとデータベースの両方がデータソース
- 同期が必要で一貫性の問題

**修正後:**
- CSVファイルはエクスポート/インポート用のみ
- データベースが唯一のデータソース
- データの一貫性を保証

### 4. パフォーマンスの改善

**修正前の問題:**
- 小さな変更でも全データを再保存
- DataFrameの読み込み/保存のオーバーヘッド
- CSVファイルとの同期処理

**修正後の改善:**
- 必要な部分のみを更新
- データベースの効率的なクエリ使用
- 不要な同期処理を削除

### 5. エラーハンドリングの改善

**修正前:**
- DataFrame操作でのエラーが複雑
- 同期失敗時の不整合

**修正後:**
- データベーストランザクションによる整合性保証
- 明確なエラーメッセージ
- 単一障害点の削除

## 利点

1. **データ整合性**: データベースが単一の真実の源
2. **パフォーマンス**: 必要な部分のみを更新
3. **保守性**: シンプルなデータフロー
4. **スケーラビリティ**: データベースの効率的な使用
5. **信頼性**: トランザクション保証とエラーハンドリング

## 後方互換性

- CSVエクスポート/インポート機能は維持
- 既存のデータベーススキーマと互換
- 既存のエンベディング生成プロセスと互換

## 今後の改善点

1. バッチ処理の最適化
2. データベースインデックスの追加
3. キャッシュ機能の実装
4. 監査ログの追加
