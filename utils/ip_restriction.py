"""
IPアドレス制限機能
utils/ip_restriction.py

不審なIPアドレスからのアクセスを制限する機能
"""
import streamlit as st
import requests
import time
from streamlit import runtime
from streamlit.runtime.scriptrunner import get_script_run_ctx

# IPアドレス→国コードのキャッシュ（メモリ節約のため最大100件）
_ip_cache = {}
_cache_max_size = 100
_cache_expiry = 3600  # 1時間で期限切れ


def get_client_ip():
    """
    クライアントのIPアドレスを取得
    
    Returns:
        str: クライアントのIPアドレス、取得できない場合はNone
    """
    try:
        # Method 1: Streamlit runtime API
        ctx = get_script_run_ctx()
        if ctx is None:
            return None
        
        session_info = runtime.get_instance().get_client(ctx.session_id)
        if session_info is None:
            return None
            
        return session_info.request.remote_ip
    except:
        # Method 2: Fallback - 外部サービス（開発・テスト用）
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            if response.status_code == 200:
                return response.json().get('ip')
        except:
            pass
    
    return None


def get_country_from_ip(ip_address):
    """
    IPアドレスから国情報を取得（キャッシュ付き）
    
    Args:
        ip_address (str): IPアドレス
        
    Returns:
        str: 国コード（ISO 2文字）、取得できない場合はNone
    """
    if not ip_address or ip_address in ['127.0.0.1', 'localhost']:
        return 'JP'  # ローカル環境では日本とみなす
    
    # キャッシュをチェック
    current_time = time.time()
    if ip_address in _ip_cache:
        cached_data = _ip_cache[ip_address]
        if current_time - cached_data['timestamp'] < _cache_expiry:
            return cached_data['country_code']
    
    try:
        # 無料のIP地理情報API（ip-api.com）
        response = requests.get(f'http://ip-api.com/json/{ip_address}?fields=countryCode', timeout=5)
        if response.status_code == 200:
            data = response.json()
            country_code = data.get('countryCode')
            
            # キャッシュに保存（サイズ制限あり）
            if len(_ip_cache) >= _cache_max_size:
                # 最も古いエントリを削除
                oldest_key = min(_ip_cache.keys(), key=lambda k: _ip_cache[k]['timestamp'])
                del _ip_cache[oldest_key]
            
            _ip_cache[ip_address] = {
                'country_code': country_code,
                'timestamp': current_time
            }
            
            return country_code
    except:
        pass
    
    return None


def is_blocked_country(country_code):
    """
    ブロック対象国かどうかを判定
    
    Args:
        country_code (str): 国コード
        
    Returns:
        bool: ブロック対象の場合True
    """
    # ブロック対象国リスト（必要に応じて設定変更可能）
    blocked_countries = {
        'CN',  # 中国
        'RU',  # ロシア
        'KP',  # 北朝鮮
        'IR',  # イラン
        # 必要に応じて追加
    }
    
    return country_code in blocked_countries


def check_ip_restriction():
    """
    IPアドレス制限をチェック
    
    Returns:
        tuple: (許可されているか, メッセージ, 国コード)
    """
    # IPアドレス取得
    client_ip = get_client_ip()
    
    if not client_ip:
        # IPアドレスが取得できない場合は許可（開発環境等）
        return True, "IPアドレスを取得できませんでした（開発環境）", None
    
    # 国情報取得
    country_code = get_country_from_ip(client_ip)
    
    if not country_code:
        # 国情報が取得できない場合は許可
        return True, f"国情報を取得できませんでした（IP: {client_ip}）", None
    
    # ブロック対象国チェック
    if is_blocked_country(country_code):
        return False, f"申し訳ございませんが、{country_code}からのアクセスは制限されています。", country_code
    
    # 許可
    return True, f"アクセス許可（{country_code}）", country_code


def display_ip_restriction_error():
    """
    IPアドレス制限エラー画面を表示
    """
    st.error("🚫 アクセスが制限されています")
    st.markdown("""
    ### アクセス制限について
    
    申し訳ございませんが、セキュリティ上の理由により、
    一部の地域からのアクセスを制限させていただいております。
    
    ### お問い合わせ
    
    正当な理由でアクセスが必要な場合は、
    システム管理者までお問い合わせください。
    
    ご理解とご協力をお願いいたします。
    """)
    
    # 詳細な説明を折りたたみ表示
    with st.expander("詳細な制限理由"):
        st.markdown("""
        - 不正な登録申請の防止
        - システムセキュリティの向上
        - 適切なサービス運用の確保
        """)