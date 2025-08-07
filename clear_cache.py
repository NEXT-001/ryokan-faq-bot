#!/usr/bin/env python3
"""
キャッシュクリアスクリプト
clear_cache.py

翻訳キャッシュと言語検出キャッシュをクリアします
"""
import sys
import os
from dotenv import load_dotenv

# パスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# .envファイルを読み込み
load_dotenv()

def clear_translation_cache():
    """翻訳サービスのキャッシュをクリア"""
    try:
        from services.translation_service import TranslationService
        
        # 新しいインスタンスを作成（キャッシュリセット）
        translation_service = TranslationService()
        
        # クリア前の状態確認
        if hasattr(translation_service, '_translation_cache'):
            cache_size_before = len(translation_service._translation_cache)
            print(f"[CACHE_CLEAR] クリア前翻訳キャッシュサイズ: {cache_size_before}件")
            
            # キャッシュを手動でクリア
            translation_service._translation_cache.clear()
            
            # クリア後確認
            cache_size_after = len(translation_service._translation_cache)
            print(f"[CACHE_CLEAR] 翻訳キャッシュクリア完了: {cache_size_before}件削除")
            print(f"[CACHE_CLEAR] クリア後翻訳キャッシュサイズ: {cache_size_after}件")
            return cache_size_before
        else:
            print("[CACHE_CLEAR] 翻訳キャッシュが見つかりません")
            return 0
            
    except Exception as e:
        print(f"[CACHE_CLEAR] 翻訳キャッシュクリアエラー: {e}")
        return 0

def clear_language_detection_cache():
    """言語検出キャッシュをクリア"""
    try:
        from services.enhanced_language_detection import EnhancedLanguageDetection
        
        # 新しいインスタンスを作成（キャッシュリセット）
        detector = EnhancedLanguageDetection()
        
        # クリア前の状態確認
        if hasattr(detector, '_cache'):
            cache_size_before = len(detector._cache)
            hits_before = detector._cache_hits if hasattr(detector, '_cache_hits') else 0
            misses_before = detector._cache_misses if hasattr(detector, '_cache_misses') else 0
            
            print(f"[CACHE_CLEAR] クリア前言語検出キャッシュサイズ: {cache_size_before}件")
            print(f"[CACHE_CLEAR] クリア前ヒット数: {hits_before}, ミス数: {misses_before}")
            
            # キャッシュを手動でクリア
            detector._cache.clear()
            
            # 統計情報もリセット
            detector._cache_hits = 0
            detector._cache_misses = 0
            
            # クリア後確認
            cache_size_after = len(detector._cache)
            print(f"[CACHE_CLEAR] 言語検出キャッシュクリア完了: {cache_size_before}件削除")
            print(f"[CACHE_CLEAR] クリア後キャッシュサイズ: {cache_size_after}件")
            print("[CACHE_CLEAR] キャッシュ統計情報リセット完了")
            return cache_size_before
        else:
            print("[CACHE_CLEAR] 言語検出キャッシュが見つかりません")
            return 0
            
    except Exception as e:
        print(f"[CACHE_CLEAR] 言語検出キャッシュクリアエラー: {e}")
        return 0

def clear_streamlit_cache():
    """Streamlitキャッシュをクリア"""
    try:
        import streamlit as st
        
        # Streamlitキャッシュクリア
        if hasattr(st, 'cache_data'):
            st.cache_data.clear()
            print("[CACHE_CLEAR] Streamlit cache_data クリア完了")
            
        if hasattr(st, 'cache_resource'):
            st.cache_resource.clear()
            print("[CACHE_CLEAR] Streamlit cache_resource クリア完了")
            
        print("[CACHE_CLEAR] Streamlitキャッシュクリア完了")
        
    except Exception as e:
        print(f"[CACHE_CLEAR] Streamlitキャッシュクリアエラー: {e}")

def verify_cache_clear():
    """キャッシュクリアの効果を確認"""
    print("\n" + "=" * 50)
    print("🔍 キャッシュクリア効果確認")
    print("=" * 50)
    
    try:
        # 翻訳キャッシュ確認
        from services.translation_service import TranslationService
        translation_service = TranslationService()
        
        if hasattr(translation_service, '_translation_cache'):
            current_translation_size = len(translation_service._translation_cache)
            print(f"[VERIFY] 現在の翻訳キャッシュサイズ: {current_translation_size}件")
        
        # 言語検出キャッシュ確認
        from services.enhanced_language_detection import EnhancedLanguageDetection
        detector = EnhancedLanguageDetection()
        
        if hasattr(detector, '_cache'):
            current_lang_size = len(detector._cache)
            hits = detector._cache_hits if hasattr(detector, '_cache_hits') else 0
            misses = detector._cache_misses if hasattr(detector, '_cache_misses') else 0
            print(f"[VERIFY] 現在の言語検出キャッシュサイズ: {current_lang_size}件")
            print(f"[VERIFY] 現在のヒット数: {hits}, ミス数: {misses}")
        
        print("\n✅ キャッシュ状態確認完了")
        
    except Exception as e:
        print(f"[VERIFY] キャッシュ確認エラー: {e}")

def main():
    """メインキャッシュクリア処理"""
    print("=" * 50)
    print("🧹 キャッシュクリア開始")
    print("=" * 50)
    
    # 1. 翻訳キャッシュクリア
    print("\n1. 翻訳キャッシュクリア")
    translation_deleted = clear_translation_cache()
    
    # 2. 言語検出キャッシュクリア
    print("\n2. 言語検出キャッシュクリア")
    language_deleted = clear_language_detection_cache()
    
    # 3. Streamlitキャッシュクリア
    print("\n3. Streamlitキャッシュクリア")
    clear_streamlit_cache()
    
    # 4. クリア効果確認
    verify_cache_clear()
    
    print("\n" + "=" * 50)
    print("✅ 全キャッシュクリア完了")
    print(f"📊 削除サマリー: 翻訳 {translation_deleted}件, 言語検出 {language_deleted}件")
    print("=" * 50)
    print("\n💡 アプリケーションを再起動してください:")
    print("   streamlit run app.py")
    
    # テスト推奨手順
    print("\n🧪 推奨テスト手順:")
    print("   1. 外国語（韓国語など）で検索")
    print("   2. 翻訳が適用されるか確認")
    print("   3. 続けて同じ言語で別の質問")
    print("   4. 言語継続性が保たれるか確認")

if __name__ == "__main__":
    main()