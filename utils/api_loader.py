"""
APIキー管理モジュール
utils/api_loader.py
"""
import os
import streamlit as st

def load_api_key():
    """APIキーを読み込む"""
    
    # 環境変数からAPIキーを取得
    api_key = os.environ.get("OPENAI_API_KEY")
    
    if api_key:
        print("[API_LOADER] 環境変数からAPIキーを読み込みました")
        return api_key
    
    # Streamlit secretsからAPIキーを取得
    try:
        if hasattr(st, 'secrets') and 'OPENAI_API_KEY' in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
            print("[API_LOADER] Streamlit secretsからAPIキーを読み込みました")
            return api_key
    except Exception as e:
        print(f"[API_LOADER] Streamlit secrets読み込みエラー: {e}")
    
    # .envファイルからAPIキーを取得
    try:
        env_file = ".env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                if line.startswith("OPENAI_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"\'')
                    if api_key:
                        print("[API_LOADER] .envファイルからAPIキーを読み込みました")
                        return api_key
    except Exception as e:
        print(f"[API_LOADER] .env読み込みエラー: {e}")
    
    # APIキーが見つからない場合
    print("[API_LOADER] APIキーが見つかりません")
    raise ValueError("APIキーが設定されていません。以下の方法でAPIキーを設定してください：\n"
                    "1. 環境変数: OPENAI_API_KEY=your_key_here\n"
                    "2. .envファイル: OPENAI_API_KEY=your_key_here\n"
                    "3. Streamlit secrets: [secrets.toml] OPENAI_API_KEY = 'your_key_here'")

def check_api_key():
    """APIキーの存在をチェック（エラーを発生させない）"""
    try:
        api_key = load_api_key()
        return api_key is not None and len(api_key) > 0
    except:
        return False

def get_api_key():
    """APIキーを取得（キャッシュ付き）"""
    try:
        return load_api_key()
    except ValueError:
        return None