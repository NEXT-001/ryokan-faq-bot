# settings.py
# 
# ⚠️ 非推奨: このファイルは config/unified_config.py に統合されました
# 新しいコードでは config.unified_config.UnifiedConfig を使用してください
# 
# このファイルは後方互換性のためにのみ残されています
#

import os
import streamlit as st
from dotenv import load_dotenv
import anthropic
import json

# 新しい統一設定をインポート
from config.unified_config import UnifiedConfig

# .envファイルを読み込む
load_dotenv()

def is_test_mode():
    """
    アプリケーションがテストモードで実行されているかどうかを確認する
    .env ファイルまたは環境変数から判断
    """
    # 明示的に設定されたテストモード値を取得
    test_mode = os.getenv("TEST_MODE", "false").lower()
    
    # 文字列の比較を修正（大文字小文字を無視し、"true"という文字列かどうか）
    is_test = test_mode == "true"
    
    return is_test

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

def get_data_path(company_id=None):
    """
    会社IDに基づいたデータディレクトリのパスを取得する
    
    Args:
        company_id (str, optional): 会社ID。指定されない場合は共通データディレクトリを返す
        
    Returns:
        str: データディレクトリのパス
    """
    # 基本データディレクトリ
    base_path = "data"
    
    # データディレクトリが存在しない場合は作成
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    # 会社別データディレクトリ
    if company_id:
        company_path = os.path.join(base_path, "companies", company_id)
        
        # 会社別ディレクトリが存在しない場合は作成
        if not os.path.exists(company_path):
            os.makedirs(company_path)
            
        return company_path
    
    # 共通データディレクトリ
    return base_path
