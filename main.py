# main.py
import streamlit as st
import os
import pandas as pd
from datetime import datetime
from config.settings import load_api_key, is_test_mode, get_data_path
from services.chat_service import get_response
from services.history_service import log_interaction, show_history
from services.login_service import login_user, logout_user, is_logged_in, is_super_admin, get_current_company_id, admin_management_page
from services.company_service import load_companies, add_company, get_company_name, get_company_list
from admin_faq_management import faq_management_page, faq_preview_page
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="マルチ企業FAQボット",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if 'page' not in st.session_state:
    st.session_state.page = "customer"  # デフォルトはお客様用ページ

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'selected_company' not in st.session_state:
    st.session_state.selected_company = "demo-company"  # デフォルトはデモ企業

# APIキーのロード
try:
    load_api_key()
except ValueError as e:
    st.error(f"エラー: {e}")
    st.info("APIキーが設定されていないため、テストモードで実行します")
    # テストモードを有効化
    os.environ["TEST_MODE"] = "true"

# .envファイルの特定の値を更新する関数
def update_env_file(key, value):
    """
    .envファイルの特定のキーの値を更新する
    """
    # 既存のファイル内容を読み込む
    env_dict = {}
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_dict[k] = v
    except FileNotFoundError:
        pass
    
    # 値を更新
    env_dict[key] = value
    
    # ファイルに書き戻す
    with open(".env", "w", encoding="utf-8") as f:
        for k, v in env_dict.items():
            f.write(f"{k}={v}\n")

# ログインページ
def login_page():
    st.title("💬 マルチ企業FAQボット - ログイン")
    
    # テストモード表示
    if is_test_mode():
        st.info("📝 テストモードで実行中です")
        st.info("スーパー管理者: 企業ID「admin」、ユーザー名「admin」、パスワード「admin」")
        st.info("デモ企業管理者: 企業ID「demo-company」、ユーザー名「admin」、パスワード「admin123」")
    
    # ログインフォーム
    with st.form("login_form"):
        st.subheader("ログイン")
        company_id = st.text_input("企業ID")
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")
        submit = st.form_submit_button("ログイン")
        
        if submit:
            if not company_id or not username or not password:
                st.error("企業ID、ユーザー名、パスワードを入力してください")
            else:
                # ログイン処理
                success, message = login_user(company_id, username, password)
                if success:
                    st.success(message)
                    st.session_state.page = "admin"  # 管理者ページに切り替え
                    st.rerun()
                else:
                    st.error(message)
    
    # お客様向けページに戻るボタン
    if st.button("お客様向けページに戻る"):
        st.session_state.page = "customer"
        st.rerun()

# 管理者ダッシュボード
def admin_dashboard():
    # スーパー管理者かどうかを確認
    is_super = is_super_admin()
    
    # 会社名を取得
    company_name = st.session_state.get("company_name", "不明な会社")
    
    if is_super:
        st.title("💬 マルチ企業FAQボット - スーパー管理者画面")
    else:
        st.title(f"💬 {company_name} - 管理画面")
    
    # テストモード表示
    if is_test_mode():
        st.info("📝 テストモードで実行中です")
    
    # サイドバーのナビゲーション
    with st.sidebar:
        st.header(f"ようこそ、{st.session_state.username}さん")
        
        # メニュー
        if is_super:
            # スーパー管理者メニュー
            admin_page = st.radio(
                "管理メニュー",
                ["企業管理", "FAQデモ"]
            )
        else:
            # 企業管理者メニュー
            admin_page = st.radio(
                "管理メニュー",
                ["FAQ管理", "FAQ履歴", "管理者設定", "FAQプレビュー"]
            )
        
        # テストモード切り替え
        current_test_mode = is_test_mode()
        new_test_mode = st.checkbox("テストモード", value=current_test_mode)
        if new_test_mode != current_test_mode:
            os.environ["TEST_MODE"] = str(new_test_mode).lower()
            # 環境変数を.envファイルにも書き込み
            update_env_file("TEST_MODE", str(new_test_mode).lower())
            st.success(f"テストモードを{'有効' if new_test_mode else '無効'}にしました。")
        
        st.markdown("---")
        if st.button("ログアウト"):
            logout_user()
            st.session_state.page = "customer"
            st.rerun()
        
        if st.button("お客様向けページを表示"):
            st.session_state.page = "customer"
            st.rerun()
    
    # 選択したページを表示
    if is_super:
        # スーパー管理者ページ
        if admin_page == "企業管理":
            super_admin_company_management()
        elif admin_page == "FAQデモ":
            # 企業選択
            companies = get_company_list()
            company_options = {company["name"]: company["id"] for company in companies}
            
            selected_company_name = st.selectbox("企業を選択", list(company_options.keys()))
            selected_company_id = company_options[selected_company_name]
            
            # プレビュー表示
            faq_preview_page(selected_company_id)
    else:
        # 企業管理者ページ
        company_id = get_current_company_id()
        
        if admin_page == "FAQ管理":
            faq_management_page()
        elif admin_page == "FAQ履歴":
            show_history(company_id)
        elif admin_page == "管理者設定":
            admin_management_page()
        elif admin_page == "FAQプレビュー":
            faq_preview_page(company_id)

# スーパー管理者の企業管理ページ
def super_admin_company_management():
    st.header("企業管理")
    
    # 企業一覧を表示
    companies = get_company_list()
    
    if companies:
        st.subheader("登録企業一覧")
        company_df = pd.DataFrame(companies)
        st.dataframe(company_df)
    else:
        st.info("登録企業がありません。")
    
    # 新規企業追加フォーム
    st.subheader("新規企業登録")
    with st.form("add_company_form"):
        company_id = st.text_input("企業ID (英数字のみ)")
        company_name = st.text_input("企業名")
        admin_username = st.text_input("管理者ユーザー名")
        admin_password = st.text_input("管理者パスワード", type="password")
        admin_email = st.text_input("管理者メールアドレス")
        
        submit = st.form_submit_button("企業を登録")
        
        if submit:
            if not company_id or not company_name or not admin_username or not admin_password:
                st.error("すべての必須項目を入力してください。")
            else:
                # IDが英数字のみかチェック
                if not company_id.isalnum():
                    st.error("企業IDは英数字のみで入力してください。")
                else:
                    success, message = add_company(company_id, company_name, admin_username, admin_password, admin_email)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

# お客様向けチャットページ
def customer_chat():
    st.title("💬 FAQチャットボット")
    
    # 企業選択
    companies = get_company_list()
    company_options = {company["name"]: company["id"] for company in companies}
    
    selected_company_name = st.selectbox(
        "企業を選択", 
        list(company_options.keys()),
        index=list(company_options.keys()).index(get_company_name("demo-company")) if "demo-company" in [c["id"] for c in companies] else 0
    )
    selected_company_id = company_options[selected_company_name]
    
    # 選択した会社を保存
    if 'selected_company' not in st.session_state or st.session_state.selected_company != selected_company_id:
        st.session_state.selected_company = selected_company_id
        st.session_state.conversation_history = []  # 会社が変わったら会話履歴をクリア
    
    # 管理者ログインへのリンク（サイドバーに表示）
    with st.sidebar:
        st.header(f"{selected_company_name} FAQボット")
        st.write("よくある質問にお答えします。質問を入力してください。")
        
        if st.button("🔐 管理者ログイン"):
            st.session_state.page = "login"
            st.rerun()
    
    # テストモードの場合はヒントを表示
    if is_test_mode():
        st.info("""
        **テストモードで実行中です**
        
        以下のキーワードを含む質問に回答できます:
        チェックイン, チェックアウト, 駐車場, wi-fi, アレルギー, 部屋, 温泉, 食事, 子供, 観光
        """)
    
    # 履歴クリアボタン - 入力フィールドの前に配置
    clear_history = st.button("会話履歴をクリア")
    if clear_history:
        # 会話履歴をクリア
        st.session_state.conversation_history = []
        # 入力欄もクリア（session_stateから削除）
        if "user_input" in st.session_state:
            st.session_state.user_input = ""
        # ユーザー情報入力欄もクリア
        if "user_info" in st.session_state:
            st.session_state.user_info = ""
        st.success("会話履歴をクリアしました！")
        st.rerun()  # 確実に再読み込み
    
    # ユーザー情報入力欄
    user_info = st.text_input("お部屋番号：", key="user_info", placeholder="例: 鈴木太郎")
    
    # ユーザー入力
    user_input = st.text_input("ご質問をどうぞ：", key="user_input", placeholder="例: チェックインの時間は何時ですか？")
    
    if user_input:
        with st.spinner("回答を生成中..."):
            # 回答を取得
            response, input_tokens, output_tokens = get_response(user_input, selected_company_id)
            
            # 会話履歴に追加
            st.session_state.conversation_history.append({
                "user_info": user_info,
                "question": user_input, 
                "answer": response
            })
            
            # ログに保存
            log_interaction(
                question=user_input,
                answer=response,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                company_id=selected_company_id,
                user_info=user_info
            )
    
    # 会話履歴の表示
    if st.session_state.conversation_history:
        st.subheader("会話履歴")
        for i, exchange in enumerate(st.session_state.conversation_history[-5:]):  # 直近5件のみ表示
            with st.container():
                if exchange.get("user_info"):
                    st.markdown(f"**お客様情報:** {exchange['user_info']}")
                st.markdown(f"**質問 {i+1}:** {exchange['question']}")
                st.markdown(f"**回答 {i+1}:** {exchange['answer']}")
                st.markdown("---")

# デバッグ情報表示（テストモード時のみ）
def show_debug_info():
    """デバッグ情報を表示する（テストモード時のみ）"""
    if is_test_mode():
        with st.expander("🔧 デバッグ情報"):
            st.write("セッション状態:")
            st.write(f"- page: {st.session_state.page}")
            
            if 'is_logged_in' in st.session_state:
                st.write(f"- is_logged_in: {st.session_state.is_logged_in}")
            
            if 'is_super_admin' in st.session_state:
                st.write(f"- is_super_admin: {st.session_state.is_super_admin}")
                
            if 'company_id' in st.session_state:
                st.write(f"- company_id: {st.session_state.company_id}")
                
            if 'company_name' in st.session_state:
                st.write(f"- company_name: {st.session_state.company_name}")
                
            if 'username' in st.session_state:
                st.write(f"- username: {st.session_state.username}")
            
            # 環境変数の状態を表示
            st.write("環境変数:")
            st.write(f"- TEST_MODE: {os.getenv('TEST_MODE', 'false')}")
            
            # セッションリセットボタン
            if st.button("セッションをリセット"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

# メイン実行部分
if __name__ == "__main__":
    # デバッグ情報表示
    show_debug_info()
    
    # ページの表示
    if st.session_state.page == "login":
        # ログインページ
        login_page()
    elif is_logged_in() and st.session_state.page == "admin":
        # 管理者ダッシュボード
        admin_dashboard()
    else:
        # お客様向けチャットページ（デフォルト）
        st.session_state.page = "customer"
        customer_chat()