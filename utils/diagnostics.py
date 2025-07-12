"""
診断・デバッグ機能モジュール
utils/diagnostics.py
"""
import os
import sys
import streamlit as st
from datetime import datetime
from utils.constants import get_data_path, is_test_mode

def run_startup_diagnostics():
    """起動時診断を実行"""
    print("\n" + "="*50)
    print("🔧 起動時診断を開始")
    print("="*50)
    
    # システム情報
    check_system_info()
    
    # ディレクトリ構造
    check_directory_structure()
    
    # 設定ファイル
    check_config_files()
    
    # モジュールの可用性
    check_module_availability()
    
    print("="*50)
    print("✅ 起動時診断完了")
    print("="*50 + "\n")

def check_system_info():
    """システム情報をチェック"""
    print("\n📋 システム情報:")
    print(f"  - Python バージョン: {sys.version.split()[0]}")
    print(f"  - 作業ディレクトリ: {os.getcwd()}")
    print(f"  - テストモード: {is_test_mode()}")
    print(f"  - 現在時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def check_directory_structure():
    """ディレクトリ構造をチェック"""
    print("\n📁 ディレクトリ構造:")
    
    # 重要なディレクトリ
    important_dirs = [
        "data",
        "data/companies",
        "data/companies/demo-company",
        "utils",
        "services",
        "pages"
    ]
    
    for dir_path in important_dirs:
        exists = os.path.exists(dir_path)
        status = "✅" if exists else "❌"
        print(f"  {status} {dir_path}")
        
        if not exists and dir_path.startswith("data"):
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"    └─ 📝 作成しました: {dir_path}")
            except Exception as e:
                print(f"    └─ ❌ 作成失敗: {e}")

def check_config_files():
    """設定ファイルをチェック"""
    print("\n📄 設定ファイル:")
    
    # 重要な設定ファイル
    config_files = [
        # os.path.join(get_data_path("demo-company"), "settings.json"),
        os.path.join(get_data_path("demo-company"), "faq.csv"),
        ".env",
        "requirements.txt"
    ]
    
    for file_path in config_files:
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        size = f" ({os.path.getsize(file_path)} bytes)" if exists else ""
        print(f"  {status} {file_path}{size}")

def check_module_availability():
    """モジュールの可用性をチェック"""
    print("\n📦 モジュール可用性:")
    
    # 重要なモジュール
    modules_to_check = [
        ("streamlit", "st"),
        ("pandas", "pd"),
        ("json", "json"),
        ("os", "os"),
        ("datetime", "datetime"),
        ("hashlib", "hashlib")
    ]
    
    for module_name, import_name in modules_to_check:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except ImportError:
            print(f"  ❌ {module_name}")

def show_debug_info():
    """デバッグ情報を表示"""
    if not is_test_mode():
        return
    
    st.markdown("### 🔧 デバッグ情報")
    
    # システム情報
    with st.expander("📋 システム情報"):
        st.write(f"**Python バージョン:** {sys.version.split()[0]}")
        st.write(f"**作業ディレクトリ:** `{os.getcwd()}`")
        st.write(f"**テストモード:** {is_test_mode()}")
        st.write(f"**現在時刻:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # ディレクトリ構造
    with st.expander("📁 ディレクトリ構造"):
        important_dirs = [
            "data",
            "data/companies", 
            "data/companies/demo-company",
            "utils",
            "services",
            "pages"
        ]
        
        for dir_path in important_dirs:
            exists = os.path.exists(dir_path)
            status = "✅" if exists else "❌"
            st.write(f"{status} `{dir_path}`")
    
    # セッション状態
    with st.expander("💾 セッション状態"):
        if st.session_state:
            for key, value in st.session_state.items():
                st.write(f"**{key}:** {type(value).__name__} = `{str(value)[:100]}`")
        else:
            st.write("セッション状態は空です")

def show_company_info_debug():
    """会社情報のデバッグ表示"""
    if not is_test_mode():
        return
    
    st.markdown("### 🏢 会社情報デバッグ")
    
    company_id = st.session_state.get("selected_company", "demo-company")
    
    # 設定ファイルの状態
    # settings_file = os.path.join(get_data_path(company_id), "settings.json")
    
    # with st.expander(f"📄 {company_id} 設定ファイル"):
    #     st.write(f"**パス:** `{settings_file}`")
    #     st.write(f"**存在:** {os.path.exists(settings_file)}")
        
    #     if os.path.exists(settings_file):
    #         try:
    #             import json
    #             with open(settings_file, 'r', encoding='utf-8') as f:
    #                 settings = json.load(f)
                
    #             st.json(settings)
    #         except Exception as e:
    #             st.error(f"ファイル読み込みエラー: {e}")
    #     else:
    #         st.warning("設定ファイルが存在しません")
    
    # FAQファイルの状態
    faq_file = os.path.join(get_data_path(company_id), "faq.csv")
    
    with st.expander(f"❓ {company_id} FAQファイル"):
        st.write(f"**パス:** `{faq_file}`")
        st.write(f"**存在:** {os.path.exists(faq_file)}")
        
        if os.path.exists(faq_file):
            try:
                import pandas as pd
                df = pd.read_csv(faq_file)
                st.write(f"**行数:** {len(df)}")
                st.dataframe(df.head())
            except Exception as e:
                st.error(f"ファイル読み込みエラー: {e}")
        else:
            st.warning("FAQファイルが存在しません")

def log_user_action(action, details=None):
    """ユーザーアクションをログに記録"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user = st.session_state.get('admin_username', 'anonymous')
    company = st.session_state.get('company_id', 'unknown')
    
    log_entry = f"[{timestamp}] {company}/{user}: {action}"
    if details:
        log_entry += f" - {details}"
    
    print(log_entry)

def create_system_report():
    """システムレポートを作成"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "python_version": sys.version.split()[0],
            "working_directory": os.getcwd(),
            "test_mode": is_test_mode()
        },
        "directories": {},
        "files": {},
        "modules": {}
    }
    
    # ディレクトリチェック
    important_dirs = ["data", "utils", "services", "pages"]
    for dir_path in important_dirs:
        report["directories"][dir_path] = os.path.exists(dir_path)
    
    # ファイルチェック  
    important_files = [".env", "main.py", "requirements.txt"]
    for file_path in important_files:
        report["files"][file_path] = {
            "exists": os.path.exists(file_path),
            "size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
        }
    
    return report