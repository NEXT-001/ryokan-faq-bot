"""
高度なログ管理システム
utils/advanced_logging.py

ファイルローテーション、ログフィルタリング、構造化ログ出力をサポート
"""
import os
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from config.unified_config import UnifiedConfig


class LogLevel(Enum):
    """ログレベル定義"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AdvancedLogger:
    """高度なログ管理クラス"""
    
    _instance = None
    _logger = None
    _file_handler = None
    _console_handler = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """ログシステムの初期化"""
        # ログディレクトリの作成
        log_dir = UnifiedConfig.LOGS_DIR
        os.makedirs(log_dir, exist_ok=True)
        
        # ログファイルパス
        log_file = os.path.join(log_dir, "application.log")
        error_log_file = os.path.join(log_dir, "errors.log")
        
        # メインロガーの設定
        self._logger = logging.getLogger("ryokan_faq_bot")
        self._logger.setLevel(self._get_log_level())
        
        # 既存のハンドラーをクリア
        self._logger.handlers.clear()
        
        # ファイルハンドラー（ローテーション付き）
        self._file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        
        # エラー専用ファイルハンドラー
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        # フォーマッターの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # JSON形式のフォーマッター（構造化ログ用）
        json_formatter = JsonFormatter()
        
        self._file_handler.setFormatter(json_formatter)
        error_handler.setFormatter(json_formatter)
        
        # コンソールハンドラー（開発時用）
        if UnifiedConfig.DEBUG_MODE:
            self._console_handler = logging.StreamHandler()
            self._console_handler.setFormatter(formatter)
            self._logger.addHandler(self._console_handler)
        
        # ハンドラーを追加
        self._logger.addHandler(self._file_handler)
        self._logger.addHandler(error_handler)
        
        # 初期化完了ログ
        self._logger.info("Advanced logging system initialized", extra={
            "component": "logging",
            "log_level": UnifiedConfig.LOG_LEVEL,
            "debug_mode": UnifiedConfig.DEBUG_MODE
        })
    
    def _get_log_level(self) -> int:
        """設定からログレベルを取得"""
        level_mapping = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_mapping.get(UnifiedConfig.LOG_LEVEL, logging.INFO)
    
    def debug(self, message: str, **kwargs):
        """デバッグログ"""
        if UnifiedConfig.should_log_debug():
            self._logger.debug(message, extra=self._create_extra(**kwargs))
    
    def info(self, message: str, **kwargs):
        """情報ログ"""
        self._logger.info(message, extra=self._create_extra(**kwargs))
    
    def warning(self, message: str, **kwargs):
        """警告ログ"""
        self._logger.warning(message, extra=self._create_extra(**kwargs))
    
    def error(self, message: str, exception: Exception = None, **kwargs):
        """エラーログ"""
        extra = self._create_extra(**kwargs)
        if exception:
            extra['exception_type'] = type(exception).__name__
            extra['exception_message'] = str(exception)
        self._logger.error(message, extra=extra)
    
    def critical(self, message: str, **kwargs):
        """クリティカルログ"""
        self._logger.critical(message, extra=self._create_extra(**kwargs))
    
    def _create_extra(self, **kwargs) -> Dict[str, Any]:
        """ログの追加情報を作成"""
        extra = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self._get_session_id(),
            'component': kwargs.get('component', 'application'),
            'user_id': kwargs.get('user_id'),
            'company_id': kwargs.get('company_id'),
            'request_id': kwargs.get('request_id'),
        }
        
        # カスタム属性を追加
        for key, value in kwargs.items():
            if key not in extra:
                extra[key] = value
        
        return {k: v for k, v in extra.items() if v is not None}
    
    def _get_session_id(self) -> Optional[str]:
        """セッションIDを取得（Streamlitセッション）"""
        try:
            import streamlit as st
            return getattr(st.session_state, 'session_id', None)
        except:
            return None
    
    def log_user_action(self, action: str, user_id: str = None, company_id: str = None, **details):
        """ユーザーアクションログ"""
        self.info(f"User action: {action}", 
                 component="user_action", 
                 user_id=user_id, 
                 company_id=company_id, 
                 action=action,
                 **details)
    
    def log_api_call(self, api_name: str, status: str, duration: float = None, **details):
        """API呼び出しログ"""
        self.info(f"API call: {api_name} - {status}",
                 component="api",
                 api_name=api_name,
                 status=status,
                 duration=duration,
                 **details)
    
    def log_database_operation(self, operation: str, table: str, status: str, **details):
        """データベース操作ログ"""
        self.info(f"Database {operation}: {table} - {status}",
                 component="database",
                 operation=operation,
                 table=table,
                 status=status,
                 **details)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """ログ統計情報を取得"""
        log_file = os.path.join(UnifiedConfig.LOGS_DIR, "application.log")
        error_log_file = os.path.join(UnifiedConfig.LOGS_DIR, "errors.log")
        
        stats = {
            "log_directory": UnifiedConfig.LOGS_DIR,
            "main_log_file": log_file,
            "error_log_file": error_log_file,
            "current_log_level": UnifiedConfig.LOG_LEVEL,
            "debug_mode": UnifiedConfig.DEBUG_MODE,
            "files": {}
        }
        
        # ファイルサイズ情報
        for name, path in [("main", log_file), ("error", error_log_file)]:
            if os.path.exists(path):
                stats["files"][name] = {
                    "size_bytes": os.path.getsize(path),
                    "size_mb": round(os.path.getsize(path) / (1024*1024), 2),
                    "last_modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
                }
        
        return stats


class JsonFormatter(logging.Formatter):
    """JSON形式のログフォーマッター"""
    
    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをJSON形式にフォーマット"""
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        
        # 追加属性を含める
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                          'relativeCreated', 'thread', 'threadName', 'processName', 
                          'process', 'message', 'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        # 例外情報の処理
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False, default=str)


# グローバルログインスタンス
logger = AdvancedLogger()

# 後方互換性のためのエイリアス
log_debug = logger.debug
log_info = logger.info
log_warning = logger.warning
log_error = logger.error
log_critical = logger.critical
log_user_action = logger.log_user_action
log_api_call = logger.log_api_call
log_database_operation = logger.log_database_operation
get_log_stats = logger.get_log_stats