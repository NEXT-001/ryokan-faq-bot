"""
管理者用キャッシュ管理機能
admin_cache_management.py

Streamlitアプリでキャッシュを管理するためのユーティリティ
"""
import streamlit as st

def show_cache_management_ui():
    """管理者用キャッシュ管理UIを表示"""
    
    st.subheader("🧹 キャッシュ管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**翻訳キャッシュ**")
        if st.button("翻訳キャッシュクリア", key="clear_translation_cache"):
            try:
                from services.translation_service import TranslationService
                service = TranslationService()
                deleted_count = service.clear_cache()
                st.success(f"翻訳キャッシュをクリアしました ({deleted_count}件削除)")
            except Exception as e:
                st.error(f"エラー: {e}")
        
        # 翻訳キャッシュ統計
        try:
            from services.translation_service import TranslationService
            service = TranslationService()
            stats = service.get_cache_stats()
            st.info(f"現在のキャッシュサイズ: {stats['cache_size']}/{stats['cache_limit']}")
        except:
            st.info("キャッシュ統計を取得できません")
    
    with col2:
        st.write("**言語検出キャッシュ**")
        if st.button("言語検出キャッシュクリア", key="clear_language_cache"):
            try:
                from services.enhanced_language_detection import EnhancedLanguageDetection
                detector = EnhancedLanguageDetection()
                deleted_count = detector.clear_cache()
                st.success(f"言語検出キャッシュをクリアしました ({deleted_count}件削除)")
            except Exception as e:
                st.error(f"エラー: {e}")
        
        # 言語検出キャッシュ統計
        try:
            from services.enhanced_language_detection import EnhancedLanguageDetection
            detector = EnhancedLanguageDetection()
            stats = detector.get_cache_stats()
            st.info(f"""
            キャッシュサイズ: {stats['cache_size']}/{stats['cache_limit']}
            ヒット率: {stats['hit_rate_percent']}%
            ヒット数: {stats['cache_hits']}
            ミス数: {stats['cache_misses']}
            """)
        except:
            st.info("キャッシュ統計を取得できません")
    
    # 全キャッシュクリア
    st.write("---")
    if st.button("🚨 全キャッシュクリア", key="clear_all_cache"):
        try:
            # Streamlitキャッシュクリア
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()
            if hasattr(st, 'cache_resource'):
                st.cache_resource.clear()
            
            # カスタムキャッシュクリア
            from services.translation_service import TranslationService
            from services.enhanced_language_detection import EnhancedLanguageDetection
            
            translation_service = TranslationService()
            detector = EnhancedLanguageDetection()
            
            t_deleted = translation_service.clear_cache()
            l_deleted = detector.clear_cache()
            
            st.success(f"全キャッシュクリア完了！ (翻訳: {t_deleted}件, 言語検出: {l_deleted}件)")
            st.info("🔄 ページを再読み込みしてください")
            
        except Exception as e:
            st.error(f"エラー: {e}")

# 使用例（管理ページに追加する場合）
def add_to_admin_page():
    """管理ページにキャッシュ管理機能を追加する例"""
    
    # 管理者権限チェック（必要に応じて）
    # if not is_admin_user():
    #     return
    
    with st.expander("🧹 キャッシュ管理", expanded=False):
        show_cache_management_ui()