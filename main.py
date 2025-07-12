"""
FAQチャットボットシステム - 新しいメインエントリーポイント
main.py (レガシー互換用)

このファイルは後方互換性のために存在します。
新しいアプリケーションのエントリーポイントはapp.pyを使用してください。
"""
import sys
import os

# パスを追加してモジュールをインポート可能にする
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 新しいアプリケーションルーターを使用
from core.app_router import route_application


if __name__ == "__main__":
    # レガシー互換性のための警告
    import streamlit as st
    
    # 最初の実行時のみ警告を表示
    if 'legacy_warning_shown' not in st.session_state:
        st.info("💡 このプロジェクトはリファクタリングされました。今後は `streamlit run app.py` を使用することを推奨します。")
        st.session_state.legacy_warning_shown = True
    
    # アプリケーションのルーティングを開始
    route_application()