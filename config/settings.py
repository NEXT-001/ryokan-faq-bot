import os
import streamlit as st
from dotenv import load_dotenv
import anthropic

def is_test_mode():
    """
    アプリケーションがテストモードで実行されているかどうかを確認する
    .env ファイルまたは環境変数から判断
    """
    # 明示的に設定されたテストモード値を取得
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    return test_mode

def load_api_key():
    """
    .envファイルまたはStreamlit SecretsからAPIキーを読み込む
    Anthropicクライアントを返す
    """
    # テストモードかどうかを確認
    test_mode = is_test_mode()
    
    if test_mode:
        print("テストモードで実行中 - APIキーは不要です")
        return None
    
    # Streamlit Secretsを安全に確認
    api_key = None
    try:
        if hasattr(st, 'secrets') and isinstance(st.secrets, dict) and 'ANTHROPIC_API_KEY' in st.secrets:
            api_key = st.secrets['ANTHROPIC_API_KEY']
    except Exception as e:
        print(f"Streamlit Secretsの読み込みエラー: {e}")
    
    # Secretsからキーが取得できなかった場合は.envファイルを確認
    if not api_key:
        # ローカル環境では.envファイルから読み込み
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # APIキーが存在するか確認
    if not api_key:
        # APIキーがない場合はテストモードに切り替え
        print("APIキーが設定されていないため、自動的にテストモードを有効化しました")
        os.environ["TEST_MODE"] = "true"
        return None
    
    # Anthropicクライアントを作成して返す
    try:
        client = anthropic.Anthropic(api_key=api_key)
        return client
    except Exception as e:
        print(f"Anthropicクライアント作成エラー: {e}")
        os.environ["TEST_MODE"] = "true"
        return None