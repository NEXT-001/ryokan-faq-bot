"""
データ整合性チェッカー
utils/data_consistency_checker.py

PostgreSQLデータベースとファイルシステムの整合性をチェック・修正
"""
import os
import shutil
from datetime import datetime
from typing import Dict, List, Tuple
from core.database import fetch_all, execute_query, fetch_one
from config.unified_config import UnifiedConfig


class DataConsistencyChecker:
    """データ整合性チェッククラス"""
    
    def __init__(self):
        self.issues = []
        self.fixes_applied = []
        
    def check_all_consistency(self, auto_fix: bool = False) -> Dict:
        """
        全データの整合性チェック
        
        Args:
            auto_fix (bool): 自動修正を行うかどうか
            
        Returns:
            Dict: チェック結果とアクション
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "database_vs_filesystem": self._check_database_filesystem_consistency(auto_fix),
            "orphaned_files": self._check_orphaned_files(auto_fix),
            "missing_directories": self._check_missing_directories(auto_fix),
            "user_company_mapping": self._check_user_company_mapping(auto_fix),
            "issues_found": len(self.issues),
            "fixes_applied": len(self.fixes_applied),
            "summary": self._generate_summary()
        }
        
        return results
    
    def _check_database_filesystem_consistency(self, auto_fix: bool) -> Dict:
        """データベース整合性チェック（フォルダ管理は廃止済み）"""
        try:
            # データベースから全企業を取得
            db_companies = fetch_all("SELECT id, name FROM companies")
            db_company_ids = {company['id'] for company in db_companies}
            
            # フォルダ管理は廃止済み - データベースのみでチェック
            return {
                "status": "success",
                "db_companies": len(db_company_ids),
                "fs_companies": 0,  # フォルダ管理廃止
                "db_only": [],
                "fs_only": [],
                "issues": [],
                "fixes": [],
                "note": "フォルダ管理は廃止されました。データベース管理のみです。"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _check_orphaned_files(self, auto_fix: bool) -> Dict:
        """孤立ファイルのチェック（フォルダ管理は廃止済み）"""
        # フォルダ管理は廃止済み - 一般的なデータディレクトリのみチェック
        orphaned_files = []
        fixes = []
        
        try:
            # データディレクトリ内の一般的なクリーンアップのみ
            data_dir = UnifiedConfig.DATA_DIR
            if not os.path.exists(data_dir):
                return {"status": "success", "orphaned_files": [], "fixes": []}
            
            # 一時ファイルや不要ファイルのみチェック
            for file_name in os.listdir(data_dir):
                file_path = os.path.join(data_dir, file_name)
                if os.path.isfile(file_path) and self._is_temp_file(file_path):
                    orphaned_files.append(file_path)
                    
                    if auto_fix and self._remove_orphaned_file(file_path):
                        fix = f"一時ファイルを削除: {file_path}"
                        fixes.append(fix)
                        self.fixes_applied.append(fix)
            
            return {
                "status": "success",
                "orphaned_files": orphaned_files,
                "fixes": fixes,
                "note": "企業フォルダ管理は廃止されました。"
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _check_missing_directories(self, auto_fix: bool) -> Dict:
        """必要なディレクトリの存在チェック（企業フォルダは除外）"""
        missing_dirs = []
        fixes = []
        
        # 必要なディレクトリ（COMPANIES_DIRは除外）
        required_dirs = [
            UnifiedConfig.DATA_DIR,
            UnifiedConfig.UPLOAD_DIR,
            UnifiedConfig.LOGS_DIR,
            UnifiedConfig.BACKUP_DIR
        ]
        
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                missing_dirs.append(dir_path)
                
                if auto_fix:
                    try:
                        os.makedirs(dir_path, exist_ok=True)
                        fix = f"ディレクトリを作成: {dir_path}"
                        fixes.append(fix)
                        self.fixes_applied.append(fix)
                    except Exception as e:
                        self.issues.append(f"ディレクトリ作成失敗: {dir_path} - {e}")
        
        return {
            "status": "success",
            "missing_directories": missing_dirs,
            "fixes": fixes,
            "note": "企業フォルダディレクトリは廃止されました。"
        }
    
    def _check_user_company_mapping(self, auto_fix: bool) -> Dict:
        """ユーザーと企業の関連性チェック"""
        try:
            # 存在しない企業を参照しているユーザーを検索
            query = """
                SELECT u.id, u.name, u.email, u.company_id 
                FROM users u 
                LEFT JOIN companies c ON u.company_id = c.id 
                WHERE c.id IS NULL
            """
            
            orphaned_users = fetch_all(query)
            issues = []
            fixes = []
            
            for user in orphaned_users:
                issue = f"ユーザー {user['email']} が存在しない企業 {user['company_id']} を参照しています"
                issues.append(issue)
                self.issues.append(issue)
                
                if auto_fix:
                    # デモ企業に移動するか、ユーザーを削除するかの選択
                    # ここでは安全のためデモ企業に移動
                    update_query = "UPDATE users SET company_id = %s WHERE id = %s"
                    execute_query(update_query, ('demo-company', user['id']))
                    
                    fix = f"ユーザー {user['email']} をデモ企業に移動しました"
                    fixes.append(fix)
                    self.fixes_applied.append(fix)
            
            return {
                "status": "success",
                "orphaned_users": len(orphaned_users),
                "issues": issues,
                "fixes": fixes
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _is_temp_file(self, file_path: str) -> bool:
        """一時ファイルかどうかをチェック"""
        file_name = os.path.basename(file_path)
        
        # 一時ファイルパターン
        temp_patterns = [
            '.tmp',
            '.temp',
            '~',
            '.bak',
            '.swp',
            '.lock'
        ]
        
        # 一時ファイルの判定
        for pattern in temp_patterns:
            if file_name.endswith(pattern):
                return True
        
        # 隠しファイルで一時的なもの
        if file_name.startswith('.') and file_name.startswith('.#'):
            return True
        
        return False
    
    def _remove_orphaned_directory(self, dir_path: str) -> bool:
        """孤立ディレクトリを安全に削除"""
        try:
            if os.path.exists(dir_path):
                # バックアップディレクトリに移動
                backup_dir = UnifiedConfig.BACKUP_DIR
                os.makedirs(backup_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(backup_dir, f"orphaned_{os.path.basename(dir_path)}_{timestamp}")
                
                shutil.move(dir_path, backup_path)
                UnifiedConfig.log_info(f"孤立ディレクトリをバックアップに移動: {dir_path} -> {backup_path}")
                return True
        except Exception as e:
            UnifiedConfig.log_error(f"ディレクトリ削除エラー: {e}")
            return False
        
        return False
    
    def _remove_orphaned_file(self, file_path: str) -> bool:
        """孤立ファイルを安全に削除"""
        try:
            if os.path.exists(file_path):
                # バックアップディレクトリに移動
                backup_dir = UnifiedConfig.BACKUP_DIR
                os.makedirs(backup_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = os.path.basename(file_path)
                backup_path = os.path.join(backup_dir, f"orphaned_{file_name}_{timestamp}")
                
                shutil.move(file_path, backup_path)
                UnifiedConfig.log_info(f"孤立ファイルをバックアップに移動: {file_path} -> {backup_path}")
                return True
        except Exception as e:
            UnifiedConfig.log_error(f"ファイル削除エラー: {e}")
            return False
        
        return False
    
    def _generate_summary(self) -> str:
        """整合性チェックの概要を生成"""
        if not self.issues:
            return "✅ データ整合性に問題は見つかりませんでした"
        
        summary = f"⚠️ {len(self.issues)}件の問題が見つかりました"
        
        if self.fixes_applied:
            summary += f"\n🔧 {len(self.fixes_applied)}件の問題を自動修正しました"
        
        return summary


def run_consistency_check(auto_fix: bool = False) -> Dict:
    """データ整合性チェックを実行"""
    checker = DataConsistencyChecker()
    return checker.check_all_consistency(auto_fix)


def run_consistency_check_report() -> str:
    """整合性チェックレポートを生成"""
    results = run_consistency_check(auto_fix=False)
    
    report = f"""
# データ整合性チェックレポート
作成日時: {results['timestamp']}

## 概要
{results['summary']}

## データベース vs ファイルシステム
- データベース企業数: {results['database_vs_filesystem'].get('db_companies', 0)}
- ファイルシステム企業数: {results['database_vs_filesystem'].get('fs_companies', 0)}
- DB専用企業: {results['database_vs_filesystem'].get('db_only', [])}
- ファイルシステム専用企業: {results['database_vs_filesystem'].get('fs_only', [])}

## 孤立ファイル
- 検出数: {len(results['orphaned_files'].get('orphaned_files', []))}

## ユーザー企業関連
- 孤立ユーザー数: {results['user_company_mapping'].get('orphaned_users', 0)}

## 発見された問題
総問題数: {results['issues_found']}
"""
    
    return report