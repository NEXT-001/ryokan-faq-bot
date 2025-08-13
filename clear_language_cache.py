"""
言語検出キャッシュクリアスクリプト
clear_language_cache.py
"""
import sys
import os

# プロジェクトルートディレクトリをPythonパスに追加
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from services.enhanced_language_detection import EnhancedLanguageDetection

def clear_language_cache():
    """言語検出キャッシュをクリア"""
    try:
        detector = EnhancedLanguageDetection()
        
        # 統計情報を表示
        stats = detector.get_cache_stats()
        print(f"[CACHE] クリア前の統計:")
        print(f"  - キャッシュサイズ: {stats['cache_size']}")
        print(f"  - ヒット回数: {stats['cache_hits']}")
        print(f"  - ミス回数: {stats['cache_misses']}")
        print(f"  - ヒット率: {stats['hit_rate_percent']}%")
        
        # キャッシュクリア
        cleared_count = detector.clear_cache()
        print(f"[CACHE] 言語検出キャッシュをクリアしました: {cleared_count}件")
        
        # テスト
        test_cases = [
            "allergies?",
            "チェックイン時間は何時ですか？",
            "What time is check-in?",
            "체크인은 몇 시부터인가요?",
            "check-in时间是几点？"
        ]
        
        print(f"\n[TEST] 言語検出テスト:")
        for text in test_cases:
            result = detector.detect_language_multilayer(text)
            print(f"  '{text}' → {result['language']} (信頼度: {result['confidence']:.2f}, 方法: {result['method']})")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] キャッシュクリアエラー: {e}")
        return False

if __name__ == "__main__":
    clear_language_cache()