"""
統一シングルトンベースクラス
core/singleton_base.py

全サービスクラスで使用するシングルトンパターンの統一実装
"""
import threading
from config.unified_config import UnifiedConfig


class SingletonMeta(type):
    """スレッドセーフなシングルトンメタクラス"""
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                # ダブルチェックロッキング
                if cls not in cls._instances:
                    instance = super(SingletonMeta, cls).__call__(*args, **kwargs)
                    cls._instances[cls] = instance
                    UnifiedConfig.log_debug(f"[SINGLETON] 新規インスタンス作成: {cls.__name__}")
                else:
                    UnifiedConfig.log_debug(f"[SINGLETON] 既存インスタンス利用: {cls.__name__}")
        else:
            UnifiedConfig.log_debug(f"[SINGLETON] 既存インスタンス利用: {cls.__name__}")
        
        return cls._instances[cls]


class SingletonService(metaclass=SingletonMeta):
    """
    シングルトンサービスベースクラス
    
    全サービスクラスはこのクラスを継承してシングルトンパターンを適用
    """
    _initialized = False
    
    def __init__(self):
        """
        初期化メソッド（サブクラスでオーバーライド）
        重複初期化を防ぐため、_initializedフラグを使用
        """
        if not self._initialized:
            self._initialized = True
            self._initialize()
            UnifiedConfig.log_service_init(self.__class__.__name__, "初期化完了")
        else:
            UnifiedConfig.log_debug(f"[SINGLETON] {self.__class__.__name__}は既に初期化済み")
    
    def _initialize(self):
        """
        実際の初期化処理（サブクラスでオーバーライド必須）
        """
        pass
    
    @classmethod
    def reset_all_instances(cls):
        """
        テスト用：全インスタンスをリセット
        """
        with SingletonMeta._lock:
            for service_class in list(SingletonMeta._instances.keys()):
                if hasattr(SingletonMeta._instances[service_class], '_initialized'):
                    SingletonMeta._instances[service_class]._initialized = False
            SingletonMeta._instances.clear()
            UnifiedConfig.log_debug("[SINGLETON] 全インスタンスリセット完了")