"""
FAQチャットボットシステム - メインエントリーポイント
app.py
"""
import sys
import os

# パスを追加してモジュールをインポート可能にする
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from core.app_router import route_application


if __name__ == "__main__":
    # アプリケーションのルーティングを開始
    route_application()