# データベーススキーマ整理実装計画

## 概要

このドキュメントは、company_adminsテーブルを削除し、usersとcompaniesテーブルのみを使用するデータベーススキーマ整理の実装計画です。

## 実装手順

### フェーズ1: 準備とデータ移行

#### 1.1 移行スクリプトの実行
```bash
cd scripts
python database_migration.py
```

この移行スクリプトは以下を実行します：
- データベースのバックアップ作成
- company_adminsテーブルのデータをusersテーブルに移行
- usersテーブルからcompany_nameカラムを削除
- company_adminsテーブルを削除
- 移行結果の検証

### フェーズ2: コード修正

#### 2.1 core/database.py の修正

**削除する関数:**
- `save_company_admin_to_db()`
- `delete_company_admins_from_db()`

**修正する関数:**
- `get_company_admins_from_db()` - usersテーブルから取得
- `update_company_name_in_db()` - usersテーブルの更新部分を削除

#### 2.2 services/company_service.py の修正

**修正する関数:**
- `verify_company_admin()` - usersテーブルから認証
- `add_admin()` - usersテーブルに追加
- `load_company_settings()` - 管理者情報をusersテーブルから取得

#### 2.3 pages/admin_page.py の修正

**修正箇所:**
- 会社名表示をcompaniesテーブルから取得するよう修正

### フェーズ3: テストと検証

#### 3.1 機能テスト
- ログイン機能
- 会社名変更機能
- ユーザー名変更機能
- パスワード変更機能
- 管理者追加機能

#### 3.2 データ整合性テスト
- 会社とユーザーの関連性
- 外部キー制約の動作確認

## 詳細な修正内容

### 1. core/database.py の修正

#### 1.1 get_company_admins_from_db() の修正
```python
def get_company_admins_from_db(company_id):
    """会社の管理者一覧をusersテーブルから取得"""
    try:
        query = "SELECT name, email, password, created_at FROM users WHERE company_id = ?"
        results = fetch_dict(query, (company_id,))
        
        admins = {}
        for row in results:
            admins[row["name"]] = {
                "password": row["password"],
                "email": row["email"],
                "created_at": row["created_at"]
            }
        
        return admins
        
    except Exception as e:
        print(f"[DATABASE] 管理者取得エラー: {e}")
        return {}
```

#### 1.2 update_company_name_in_db() の修正
```python
def update_company_name_in_db(company_id, new_company_name):
    """会社名をcompaniesテーブルのみで更新"""
    try:
        # companiesテーブルのみを更新
        query = "UPDATE companies SET name = ? WHERE id = ?"
        rows_affected = execute_query(query, (new_company_name, company_id))
        
        if rows_affected > 0:
            print(f"[DATABASE] 会社名更新完了: {company_id} -> {new_company_name}")
            return True
        else:
            print(f"[DATABASE] 会社名更新失敗: 会社が見つかりません {company_id}")
            return False
        
    except Exception as e:
        print(f"[DATABASE] 会社名更新エラー: {e}")
        return False
```

### 2. services/company_service.py の修正

#### 2.1 verify_company_admin() の修正
```python
def verify_company_admin(company_id, username, password):
    """会社管理者の認証を行う（usersテーブル使用）"""
    try:
        # 会社の存在確認
        if not company_exists_in_db(company_id):
            return False, "企業が見つかりません"
        
        # usersテーブルから管理者情報を取得
        query = "SELECT name, password FROM users WHERE company_id = ? AND name = ?"
        result = fetch_dict_one(query, (company_id, username))
        
        if not result:
            return False, "ユーザー名が見つかりません"
        
        # パスワードの確認
        if result["password"] != hash_password(password):
            return False, "パスワードが間違っています"
        
        # 会社名を取得
        company_info = get_company_from_db(company_id)
        company_name = company_info["company_name"] if company_info else "不明な企業"
        
        # 認証成功
        return True, company_name
        
    except Exception as e:
        print(f"[COMPANY_SERVICE] 認証エラー: {e}")
        return False, "認証エラーが発生しました"
```

#### 2.2 add_admin() の修正
```python
def add_admin(company_id, username, password, email=""):
    """会社に管理者を追加する（usersテーブル使用）"""
    if not username or not password:
        return False, "ユーザー名とパスワードを入力してください"
    
    try:
        # 会社の存在確認
        if not company_exists_in_db(company_id):
            return False, "企業が見つかりません"
        
        # 既存管理者の確認
        existing_query = "SELECT id FROM users WHERE company_id = ? AND name = ?"
        existing_user = fetch_dict_one(existing_query, (company_id, username))
        
        if existing_user:
            return False, "このユーザー名は既に使用されています"
        
        # 新しい管理者をusersテーブルに追加
        created_at = datetime.now().isoformat()
        query = """
            INSERT INTO users (company_id, name, email, password, created_at, is_verified)
            VALUES (?, ?, ?, ?, ?, 1)
        """
        
        execute_query(query, (company_id, username, email, hash_password(password), created_at))
        return True, "管理者を追加しました"
            
    except Exception as e:
        print(f"[COMPANY_SERVICE] 管理者追加エラー: {e}")
        return False, "管理者の追加に失敗しました"
```

### 3. pages/admin_page.py の修正

#### 3.1 会社名表示の修正
```python
def admin_dashboard(company_id):
    """管理者ダッシュボード"""
    try:
        # スーパー管理者かどうかを確認
        is_super = is_super_admin()
        
        # 会社名を取得
        if is_super:
            company_name = "スーパー管理者"
        else:
            # companiesテーブルから会社名を取得
            from core.database import get_company_from_db
            company_info = get_company_from_db(company_id)
            company_name = company_info["company_name"] if company_info else "不明な会社"
        
        # 以下は既存のコードと同じ...
```

## リスクと対策

### リスク1: データ損失
**対策**: 移行前に必ずバックアップを作成し、各段階で検証を実施

### リスク2: 機能の一時的な停止
**対策**: 段階的な移行により、影響を最小限に抑制

### リスク3: 外部キー制約エラー
**対策**: 移行スクリプトで適切な外部キー制約を設定

## 検証項目

### 機能検証
- [ ] ログイン機能（メールアドレス認証）
- [ ] 会社名変更機能
- [ ] ユーザー名変更機能
- [ ] パスワード変更機能
- [ ] 管理者追加機能
- [ ] FAQ管理機能
- [ ] LINE設定機能

### データ整合性検証
- [ ] 会社とユーザーの関連性
- [ ] 外部キー制約の動作
- [ ] データの重複がないこと
- [ ] 必要なデータが欠損していないこと

## 実装後の利点

1. **データの一貫性**: 会社名の重複がなくなり、単一の情報源となる
2. **保守性の向上**: テーブル数の削減により、保守が容易になる
3. **パフォーマンス向上**: JOINの削減により、クエリ性能が向上
4. **拡張性**: 一つの会社に複数の管理者を持つことが可能

## 注意事項

1. 移行は本番環境で実施する前に、開発環境で十分にテストすること
2. 移行中はシステムを停止することを推奨
3. バックアップファイルは移行完了後も一定期間保持すること
4. 移行後は関連するドキュメントも更新すること

## 完了基準

- [ ] 移行スクリプトが正常に実行される
- [ ] company_adminsテーブルが削除されている
- [ ] usersテーブルからcompany_nameカラムが削除されている
- [ ] 全ての機能が正常に動作する
- [ ] データの整合性が保たれている
- [ ] テストが全て通過する
