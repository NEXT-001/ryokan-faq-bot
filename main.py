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
from line_settings import line_settings_page

# .envファイルを読み込む
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="マルチ企業FAQボット",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# URLパラメータの取得
def get_url_params():
    """URLパラメータを取得する"""
    # st.query_paramsを使用
    
    # モードの取得（デフォルトはuser）
    mode = st.query_params.get("mode", "user")
    if mode not in ["admin", "user"]:
        mode = "user"
    
    # 会社IDの取得（デフォルトはdemo-company）
    company_id = st.query_params.get("company", "demo-company")
    
    # ログイン状態も取得
    logged_in = st.query_params.get("logged_in", "false")
    
    return mode, company_id, logged_in == "true"

# セッション状態の初期化
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

# URLパラメータからモードと会社IDを取得
current_mode, current_company_id, url_logged_in = get_url_params()

# URLパラメータからログイン状態を復元
if url_logged_in and "is_logged_in" not in st.session_state:
    st.session_state["is_logged_in"] = True

# セッションに保存（URLパラメータを優先）
if current_company_id:
    st.session_state.selected_company = current_company_id

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

# モード切替関数
def switch_to_admin_mode(company_id=None):
    """管理者モードに切り替える"""
    if not company_id and 'selected_company' in st.session_state:
        company_id = st.session_state.selected_company
    elif not company_id:
        company_id = "demo-company"
    
    # URLパラメータを設定
    st.query_params.mode = "admin"
    st.query_params.company = company_id
    
    # ログイン状態を維持
    if is_logged_in():
        st.query_params.logged_in = "true"

def switch_to_user_mode(company_id=None):
    """ユーザーモードに切り替える"""
    if not company_id and 'selected_company' in st.session_state:
        company_id = st.session_state.selected_company
    elif not company_id:
        company_id = "demo-company"
    
    # URLパラメータを設定
    st.query_params.mode = "user"
    st.query_params.company = company_id

# ログインページ
def login_page():
    st.title("💬 マルチ企業FAQボット - ログイン")
    
    # 会社名を表示（もし選択されている場合）
    if 'selected_company' in st.session_state:
        company_name = get_company_name(st.session_state.selected_company)
        if company_name:
            st.header(f"企業: {company_name}")
    
    # テストモード表示
    if is_test_mode():
        st.info("📝 テストモードで実行中です")
        st.info("スーパー管理者: 企業ID「admin」、ユーザー名「admin」、パスワード「admin」")
        st.info("デモ企業管理者: 企業ID「demo-company」、ユーザー名「admin」、パスワード「admin123」")
    
    # ログイン状態を確認
    if is_logged_in():
        st.success("すでにログインしています。")
        # リンクを明示的に表示
        company_id = get_current_company_id() or st.session_state.get('selected_company', 'demo-company')
        # 現在のURLからadminページへのリンクを作成
        admin_url = f"?mode=admin&company={company_id}&logged_in=true"
        st.markdown(f"### [管理者ページに移動する]({admin_url})")
        return
    
    # ログインフォーム
    with st.form("login_form"):
        st.subheader("ログイン")
        company_id = st.text_input("企業ID", value=st.session_state.get('selected_company', ''))
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
                    st.success(f"{message} ログインしました。")
                    # 選択中の会社を更新
                    st.session_state.selected_company = company_id
                    
                    # 管理者ページへの明示的なリンクを表示（ログイン状態付き）
                    admin_url = f"?mode=admin&company={company_id}&logged_in=true"
                    st.markdown(f"### [管理者ページに移動する]({admin_url})")
                    
                    # セッション状態を表示（デバッグ用）
                    if is_test_mode():
                        st.write("セッション状態:", st.session_state)
                else:
                    st.error(message)
    
    # お客様向けページに戻るリンク（ボタンではなくリンクを使用）
    company_id = st.session_state.get('selected_company', 'demo-company')
    user_url = f"?mode=user&company={company_id}"
    st.markdown(f"[お客様向けページに戻る]({user_url})")

# 管理者ダッシュボード
def admin_dashboard():
    # 未ログインの場合はログインページに転送
    if not is_logged_in():
        st.warning("管理者機能を利用するにはログインが必要です")
        login_page()
        return
    
    # スーパー管理者かどうかを確認
    is_super = is_super_admin()
    
    # 会社名を取得
    if is_super:
        company_name = "スーパー管理者"
    else:
        # 会社IDを取得し、セッションの整合性を確保
        company_id = get_current_company_id()
        
        # 会社IDが取得できなかった場合、URLパラメータから会社IDを取得
        if not company_id:
            # URLパラメータから会社IDを取得
            _, param_company_id, _ = get_url_params()
            if param_company_id:
                company_id = param_company_id
                # セッションに会社IDを保存
                st.session_state["company_id"] = company_id
        
        # 会社名を取得
        company_name = st.session_state.get("company_name", get_company_name(company_id) or "不明な会社")
        
        # デバッグ情報を表示
        if is_test_mode():
            st.sidebar.write(f"デバッグ情報: 会社ID={company_id}")
    
    # タイトル表示
    st.title(f"💬 {company_name} - 管理画面")
    
    # テストモード表示
    if is_test_mode():
        st.info("📝 テストモードで実行中です")
    
    # サイドバーのナビゲーション
    with st.sidebar:
        st.header(f"ようこそ、{st.session_state.get('username', '')}さん")
        
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
                ["FAQ管理", "FAQ履歴", "LINE通知設定", "管理者設定", "FAQプレビュー"]
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
        
        # ログアウト機能（フォームの外に置く）
        logout_btn = st.button("ログアウト")
        if logout_btn:
            logout_user()
            # 現在の会社IDを維持したままユーザーモードに切り替え
            company_id = st.session_state.get('selected_company', 'demo-company')
            # ログアウト後のURLを設定
            user_url = f"?mode=user&company={company_id}"
            st.query_params.mode = "user"
            st.query_params.company = company_id
            if "logged_in" in st.query_params:
                # logged_inパラメータを削除
                current_params = dict(st.query_params)
                if "logged_in" in current_params:
                    del current_params["logged_in"]
                # 他のパラメータを維持
                st.query_params.update(**current_params)
            
            st.success("ログアウトしました。ユーザーモードに移動します。")
            st.markdown(f"[お客様向けページに移動]({user_url})")
            st.stop()  # これ以上の処理を停止
        
        # ユーザーモードへのリンク
        company_id = st.session_state.get('selected_company', 'demo-company')
        user_url = f"?mode=user&company={company_id}"
        st.markdown(f"[お客様向けページを表示]({user_url})")
    
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
            
            # 選択した会社を保存してURL更新（st.rerunを避ける）
            if selected_company_id != st.session_state.get('selected_company'):
                st.session_state.selected_company = selected_company_id
                # ログイン状態を維持したままURLを更新
                new_url = f"?mode=admin&company={selected_company_id}&logged_in=true"
                st.markdown(f"[選択した企業のFAQを表示]({new_url})")
            
            # プレビュー表示
            faq_preview_page(selected_company_id)
    else:
        # 企業管理者ページ
        company_id = get_current_company_id()
        
        if admin_page == "FAQ管理":
            faq_management_page()
        elif admin_page == "FAQ履歴":
            show_history(company_id)
        elif admin_page == "LINE通知設定":
            line_settings_page(company_id)
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
        
        # 企業データをシンプルに表示
        company_data = []
        for company in companies:
            company_data.append({
                "ID": company["id"],
                "名前": company["name"],
                "管理者数": company["admin_count"],
                "作成日時": company["created_at"]
            })
        
        # シンプルなデータフレーム表示
        company_df = pd.DataFrame(company_data)
        st.dataframe(company_df)
        
        # 企業切り替え（シンプルなリンクリスト）
        st.subheader("企業切り替え")
        
        for company in companies:
            # ログイン状態を維持
            admin_url = f"?mode=admin&company={company['id']}&logged_in=true"
            user_url = f"?mode=user&company={company['id']}"
            st.markdown(f"**{company['name']}**: [管理者として表示]({admin_url}) | [ユーザーとして表示]({user_url})")
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
                        # 直接URLを提供してリンクとして表示（ログイン状態を維持）
                        admin_url = f"?mode=admin&company={company_id}&logged_in=true"
                        st.markdown(f"新しい企業の管理画面を表示するには[ここをクリック]({admin_url})")
                    else:
                        st.error(message)

# お客様向けチャットページ
def customer_chat():
    # 会社IDを取得
    company_id = st.session_state.get('selected_company', 'demo-company')
    company_name = get_company_name(company_id)
    
    # タイトル表示
    st.title(f"💬 {company_name} FAQチャットボット")
    
    # サイドバーメニュー
    with st.sidebar:
        st.header(f"{company_name} FAQボット")
        st.write("よくある質問にお答えします。質問を入力してください。")
        
        # 企業選択（シンプル化）
        st.subheader("企業を選択")
        companies = get_company_list()
        
        # 会社名のみのリストを作成
        company_names = [company["name"] for company in companies]
        company_ids = [company["id"] for company in companies]
        
        # 現在の会社名のインデックスを取得
        try:
            current_index = company_ids.index(company_id)
        except ValueError:
            current_index = 0
        
        # シンプルなセレクトボックス
        selected_company_name = st.selectbox(
            "企業", 
            company_names,
            index=current_index
        )
        
        # 選択された会社名のインデックスから会社IDを取得
        selected_index = company_names.index(selected_company_name)
        selected_company_id = company_ids[selected_index]
        
        # 企業が変更されたらURLを更新
        if selected_company_id != company_id:
            st.session_state.selected_company = selected_company_id
            # URLパラメータを更新
            new_url = f"?mode=user&company={selected_company_id}"
            st.markdown(f"[選択した企業を表示するにはここをクリック]({new_url})")
        
        # 管理者ログインへのリンク
        admin_url = f"?mode=admin&company={company_id}"
        st.markdown(f"[🔐 管理者ログイン]({admin_url})")
    
    # テストモードの場合はヒントを表示
    if is_test_mode():
        st.info("""
        **テストモードで実行中です**
        
        以下のキーワードを含む質問に回答できます:
        チェックイン, チェックアウト, 駐車場, wi-fi, アレルギー, 部屋, 温泉, 食事, 子供, 観光
        """)
    
    # 履歴クリアボタン
    if st.button("会話履歴をクリア"):
        # 会話履歴をクリア
        if "conversation_history" in st.session_state:
            st.session_state.conversation_history = []
        # 入力欄もクリア
        if "user_input" in st.session_state:
            st.session_state.user_input = ""
        if "user_info" in st.session_state:
            st.session_state.user_info = ""
        st.success("会話履歴をクリアしました！")
    
    # ユーザー情報入力欄
    user_info = st.text_input("お部屋番号：", key="user_info", placeholder="例: 101")
    
    # ユーザー入力
    user_input = st.text_input("ご質問をどうぞ：", key="user_input", placeholder="例: チェックインの時間は何時ですか？")
    
    if user_input:
        with st.spinner("回答を生成中..."):
            try:
                # 回答を取得
                response, input_tokens, output_tokens = get_response(
                    user_input, 
                    company_id,
                    user_info
                )
                
                # 会話履歴がなければ初期化
                if "conversation_history" not in st.session_state:
                    st.session_state.conversation_history = []
                    
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
                    company_id=company_id,
                    user_info=user_info
                )
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
    
    # 会話履歴の表示
    if "conversation_history" in st.session_state and st.session_state.conversation_history:
        st.subheader("会話履歴")
        # スクロール可能なコンテナ内で表示（レイアウト安定化）
        with st.container():
            for i, exchange in enumerate(st.session_state.conversation_history[-5:]):  # 直近5件のみ表示
                st.markdown(f"**質問 {i+1}:** {exchange['question']}")
                st.markdown(f"**回答 {i+1}:** {exchange['answer']}")
                if exchange.get("user_info"):
                    st.markdown(f"**お客様情報:** {exchange['user_info']}")
                st.markdown("---")

# デバッグ情報表示（テストモード時のみ）
def show_debug_info():
    """デバッグ情報を表示する（テストモード時のみ）"""
    if is_test_mode():
        with st.expander("🔧 デバッグ情報"):
            # URLパラメータ
            mode, company_id, url_logged_in = get_url_params()
            st.write("URL パラメータ:")
            st.write(f"- mode: {mode}")
            st.write(f"- company: {company_id}")
            st.write(f"- logged_in: {url_logged_in}")
            
            # セッション状態
            st.write("セッション状態:")
            for key, value in st.session_state.items():
                # ユーザー情報とチャット履歴は長くなるので表示しない
                if key not in ["conversation_history"]:
                    st.write(f"- {key}: {value}")
            
            # ログイン状態のチェック
            st.write(f"is_logged_in()の結果: {is_logged_in()}")
            
            # 環境変数の状態
            st.write("環境変数:")
            st.write(f"- TEST_MODE: {os.getenv('TEST_MODE', 'false')}")
            
            # URL生成テスト
            st.write("URL生成テスト:")
            test_company = "demo-company"
            st.write(f"- テスト会社ID: {test_company}")
            
            # モード切替リンク
            admin_url = f"?mode=admin&company={test_company}&logged_in=true"
            user_url = f"?mode=user&company={test_company}"
            st.write("モード切替リンク:")
            st.markdown(f"- [管理者モードに切替]({admin_url})")
            st.markdown(f"- [ユーザーモードに切替]({user_url})")
            
            # セッションリセットボタン
            if st.button("セッションをリセット"):
                # セッションだけクリアして、URLはそのまま
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("セッションをリセットしました。")

# メイン実行部分
if __name__ == "__main__":
    # URLパラメータに基づいて画面を切り替え
    mode, company_id, url_logged_in = get_url_params()
    
    # 会社IDをセッションに保存
    if company_id:
        st.session_state.selected_company = company_id
    
    # URLのログイン状態からセッション状態を復元
    if url_logged_in and "is_logged_in" not in st.session_state:
        st.session_state["is_logged_in"] = True
    
    # モードに基づいてパラメータを直接更新
    if mode == "admin":
        # クエリパラメータのmodeを確実にadminに
        st.query_params.mode = "admin"
    else:
        # それ以外はuserモードに
        st.query_params.mode = "user"
    
    # 会社IDも更新
    if company_id:
        st.query_params.company = company_id
    
    # ログイン状態もURLに反映
    if is_logged_in():
        st.query_params.logged_in = "true"
    
    # デバッグ情報表示（常に最初に実行）
    show_debug_info()
    
    # モードに応じた表示
    if mode == "admin":
        # 未ログインの場合はログインページを表示
        if not is_logged_in():
            login_page()
        else:
            admin_dashboard()
    else:
        # ユーザーモード（デフォルト）
        customer_chat()