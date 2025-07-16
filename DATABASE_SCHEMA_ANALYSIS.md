# データベーススキーマ分析と改善提案

## 現在の問題点

### 1. 三つの会社関連テーブルの重複
現在のシステムには以下の三つのテーブルが存在し、データの重複と不整合が発生しています：

- `companies` テーブル
- `company_admins` テーブル  
- `users` テーブル

### 2. データの重複
- `companies.name` と `users.company_name` が重複
- 管理者情報が `company_admins` と `users` の両方に存在

### 3. 使用方法の不整合
- 「{会社名} - 管理画面」と「ようこそ、{管理者名}さん」では `users` テーブルを使用
- 管理者情報は `company_admins` テーブルを使用
- `save_company_to_db` などでは `companies` テーブルを使用
- 「会社名を変更」では `companies` と `users` の両方を更新
- 「ユーザー名を変更」では `users` テーブルのみ更新
- 「パスワードを変更」では `users` テーブルのみ更新

## 現在のテーブル構造

### companies テーブル
```sql
CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    faq_count INTEGER DEFAULT 0,
    last_updated TEXT NOT NULL
)
```

### company_admins テーブル（削除対象）
```sql
CREATE TABLE company_admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(company_id, username),
    UNIQUE(company_id, email)
)
```

### users テーブル
```sql
CREATE TABLE users (
    id INTEGER,
    company_id TEXT NOT NULL UNIQUE,
    company_name TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_verified INTEGER DEFAULT 0,
    verify_token TEXT,
    status INTEGER DEFAULT 0,
    trial_start_date TEXT,
    trial_end_date TEXT,
    is_trial_active INTEGER DEFAULT 1,
    PRIMARY KEY(id AUTOINCREMENT)
)
```

## 推奨改善案

### 案1: 最小限の変更（推奨）

#### 1. company_admins テーブルを削除
#### 2. users テーブルから company_name カラムを削除
#### 3. companies テーブルとの外部キー制約を強化

```sql
-- 改善後の companies テーブル
CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    faq_count INTEGER DEFAULT 0,
    last_updated TEXT NOT NULL
);

-- 改善後の users テーブル
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_verified INTEGER DEFAULT 0,
    verify_token TEXT,
    status INTEGER DEFAULT 0,
    trial_start_date TEXT,
    trial_end_date TEXT,
    is_trial_active INTEGER DEFAULT 1,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);
```

#### メリット：
- データの重複を解消
- 一つの会社に複数の管理者を持てる
- 外部キー制約により整合性を保証
- 既存コードの変更が最小限

#### デメリット：
- company_id の UNIQUE 制約を削除する必要がある

### 案2: より良い正規化（代替案）

一つの会社に複数の管理者が必要な場合を考慮した設計：

```sql
-- companies テーブル（変更なし）
CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    faq_count INTEGER DEFAULT 0,
    last_updated TEXT NOT NULL
);

-- users テーブル（管理者専用に特化）
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_verified INTEGER DEFAULT 0,
    verify_token TEXT,
    status INTEGER DEFAULT 0,
    trial_start_date TEXT,
    trial_end_date TEXT,
    is_trial_active INTEGER DEFAULT 1,
    FOREIGN KEY (company_id) REFERENCES companies (id) ON DELETE CASCADE
);
```

## 移行手順

### ステップ1: データ移行の準備
1. 現在のデータをバックアップ
2. `company_admins` テーブルのデータを `users` テーブルに統合
3. データの整合性を確認

### ステップ2: テーブル構造の変更
1. `users` テーブルから `company_name` カラムを削除
2. `users` テーブルの `company_id` UNIQUE 制約を削除
3. `company_admins` テーブルを削除

### ステップ3: コードの修正
1. 会社名取得を `companies` テーブルから行うよう修正
2. 管理者認証を `users` テーブルのみ使用するよう修正
3. 関連する全ての関数を更新

## 影響を受ける関数とファイル

### core/database.py
- `save_company_admin_to_db()` - 削除
- `get_company_admins_from_db()` - `users` テーブルから取得するよう修正
- `delete_company_admins_from_db()` - 削除
- `update_company_admin_password_in_db()` - 既に `users` テーブルを使用（修正不要）
- `update_company_name_in_db()` - `users` テーブルの更新部分を削除
- `update_username_in_db()` - 修正不要

### services/company_service.py
- `verify_company_admin()` - `users` テーブルから認証するよう修正
- `add_admin()` - `users` テーブルに追加するよう修正
- `load_company_settings()` - 管理者情報を `users` テーブルから取得

### services/auth_service.py
- 既に `users` テーブルを主に使用しているため、大きな変更は不要

### pages/admin_page.py
- 会社名表示を `companies` テーブルから取得するよう修正

## 実装の優先順位

1. **高優先度**: データ移行スクリプトの作成
2. **高優先度**: `company_admins` テーブル依存の関数修正
3. **中優先度**: UI表示の修正
4. **低優先度**: 不要なコードの削除

## 注意事項

1. **データ損失の防止**: 移行前に必ずバックアップを取得
2. **段階的移行**: 一度にすべてを変更せず、段階的に実施
3. **テスト**: 各段階でテストを実施し、動作確認を行う
4. **ロールバック計画**: 問題が発生した場合の復旧手順を準備

## 結論

**推奨案**: 案1（最小限の変更）を採用し、以下の順序で実装することを推奨します：

1. データ移行スクリプトの作成・実行
2. `company_admins` テーブル依存の関数を `users` テーブル使用に変更
3. `users.company_name` カラムの削除
4. `company_admins` テーブルの削除
5. 不要なコードの削除

この方法により、データの整合性を保ちながら、システムの複雑さを軽減できます。
