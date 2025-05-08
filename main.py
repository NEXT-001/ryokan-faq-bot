# main.py
import streamlit as st
import os
from services.chat_service import get_response
from services.history_service import log_interaction, show_history
from services.login_service import verify_user, is_admin, user_management_page
from admin_line_settings import line_settings
from admin_faq_management import faq_management_page  # 新たに追加したFAQ管理ページをインポート
from config.settings import load_api_key, is_test_mode
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# ページ設定
st.set_page_config(
    page_title="旅館FAQチャットボット",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# セッション状態の初期化
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'page' not in st.session_state:
    st.session_state.page = "customer"  # デフォルトはお客様用ページ

# テストモード状態の確認
# test_mode = is_test_mode()
# print(f"TEST_MODE環境変数: {os.getenv('TEST_MODE', 'false')}")
# print(f"設定されたTEST_MODE値: {test_mode}")

# APIキーのロード
try:
    load_api_key()
except ValueError as e:
    st.error(f"エラー: {e}")
    st.info("APIキーが設定されていないため、テストモードで実行します")
    # テストモードを有効化
    os.environ["TEST_MODE"] = "true"

# 管理者ログイン処理
def admin_login_page():
    st.title("🏨 旅館FAQチャットボット - 管理者ログイン")
    
    # テストモード表示
    if is_test_mode():
        st.info("📝 テストモードで実行中です - 管理者: admin / パスワード: admin")
    
    # ログインフォーム
    with st.form("login_form"):
        st.subheader("ログイン")
        username = st.text_input("ユーザー名")
        password = st.text_input("パスワード", type="password")
        submit = st.form_submit_button("ログイン")
        
        if submit:
            if not username or not password:
                st.error("ユーザー名とパスワードを入力してください")
            else:
                # テストモードの場合は簡易認証
                if is_test_mode() and username == "admin" and password == "admin":
                    st.session_state.admin_logged_in = True
                    st.session_state.username = username
                    st.session_state.user_role = "admin"
                    st.session_state.page = "admin"  # 管理者ページに切り替え
                    st.success("テスト管理者としてログインしました！")
                    st.rerun()
                else:
                    # 通常の認証
                    success, role = verify_user(username, password)
                    if success and role == "admin":
                        st.session_state.admin_logged_in = True
                        st.session_state.username = username
                        st.session_state.user_role = role
                        st.session_state.page = "admin"  # 管理者ページに切り替え
                        st.success("ログインしました！")
                        st.rerun()
                    else:
                        st.error("管理者アカウントでログインしてください")
    
    # お客様向けページに戻るボタン
    if st.button("お客様向けページに戻る"):
        st.session_state.page = "customer"
        st.rerun()

# 管理者ダッシュボード
def admin_dashboard():
    st.title("🏨 旅館FAQチャットボット - 管理画面")
    
    # テストモード表示
    if is_test_mode():
        st.info("📝 テストモードで実行中です")
    
    # サイドバーのナビゲーション
    with st.sidebar:
        st.header(f"ようこそ、{st.session_state.username}さん")
        
        # メニュー - FAQ管理を追加
        admin_page = st.radio(
            "管理メニュー",
            ["FAQ管理", "FAQ履歴", "ユーザー管理", "LINE通知設定", "FAQチャットプレビュー"]
        )
        
        # テストモード切り替え
        current_test_mode = is_test_mode()
        new_test_mode = st.checkbox("テストモード", value=current_test_mode)
        if new_test_mode != current_test_mode:
            os.environ["TEST_MODE"] = str(new_test_mode).lower()
            # 環境変数を.envファイルにも書き込み
            update_env_file("TEST_MODE", str(new_test_mode).lower())
            st.success(f"テストモードを{'有効' if new_test_mode else '無効'}にしました。反映するにはページを再読み込みしてください。")
        
        st.markdown("---")
        if st.button("ログアウト"):
            st.session_state.admin_logged_in = False
            st.session_state.username = None
            st.session_state.user_role = None
            st.session_state.page = "customer"
            st.rerun()
        
        if st.button("お客様向けページを表示"):
            st.session_state.page = "customer"
            st.rerun()
    
    # 選択したページを表示
    if admin_page == "FAQ管理":
        # FAQ管理ページを表示
        faq_management_page()
    elif admin_page == "FAQ履歴":
        st.header("FAQ利用履歴")
        show_history()
    elif admin_page == "ユーザー管理":
        user_management_page()
    elif admin_page == "LINE通知設定":
        line_settings()
    elif admin_page == "FAQチャットプレビュー":
        customer_chat(is_preview=True)

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

# お客様向けチャットページ
def customer_chat(is_preview=False):
    if not is_preview:
        st.title("🏨 旅館FAQチャットボット")
        
        # 管理者ログインへのリンク（サイドバーに表示）
        with st.sidebar:
            st.header("旅館FAQチャットボット")
            st.write("旅館に関するよくある質問にお答えします。質問を入力してください。")
            
            if st.button("🔐 管理者ログイン"):
                st.session_state.page = "admin_login"
                st.rerun()
    else:
        st.header("FAQチャットプレビュー（管理者モード）")
    
    # テストモードの場合はヒントを表示
    if is_test_mode():
        st.info("""
        **テストモードで実行中です**
        
        以下のキーワードに関する質問が利用できます:
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
        # 部屋番号入力欄もクリア
        if "room_number" in st.session_state:
            st.session_state.room_number = ""
        st.success("会話履歴をクリアしました！")
        st.experimental_rerun()  # 確実に再読み込み
    
    # 部屋番号入力欄を追加
    room_number = st.text_input("部屋番号：", key="room_number", placeholder="例: 101")
    
    # ユーザー入力
    user_input = st.text_input("ご質問をどうぞ：", key="user_input")
    
    if user_input:
        with st.spinner("回答を生成中..."):
            # 回答を取得
            response, input_tokens, output_tokens = get_response(user_input, room_number)
            
            # 会話履歴に追加（部屋番号も含める）
            st.session_state.conversation_history.append({
                "room_number": room_number,
                "question": user_input, 
                "answer": response
            })
            
            # ログに保存（プレビューモードではログを記録しない）
            if not is_preview:
                log_interaction(user_input, response, input_tokens, output_tokens, room_number)
    
    # 会話履歴の表示
    if st.session_state.conversation_history:
        st.subheader("会話履歴")
        for i, exchange in enumerate(st.session_state.conversation_history[-5:]):  # 直近5件のみ表示
            with st.container():
                room_info = f"**部屋番号:** {exchange.get('room_number', '未入力')}"
                st.markdown(room_info)
                st.markdown(f"**質問 {i+1}:** {exchange['question']}")
                st.markdown(f"**回答 {i+1}:** {exchange['answer']}")
                st.markdown("---")

# デバッグ情報表示（テストモード時のみ）
def show_debug_info():
    if is_test_mode():
        with st.expander("🔧 デバッグ情報"):
            st.write("セッション状態:")
            st.write(f"- page: {st.session_state.page}")
            st.write(f"- admin_logged_in: {st.session_state.admin_logged_in}")
            if 'username' in st.session_state:
                st.write(f"- username: {st.session_state.username}")
            if 'user_role' in st.session_state:
                st.write(f"- user_role: {st.session_state.user_role}")
            
            # 環境変数の状態を表示
            st.write("環境変数:")
            st.write(f"- TEST_MODE: {os.getenv('TEST_MODE', 'false')}")
            st.write(f"- 実際のテストモード状態: {is_test_mode()}")
            
            # セッションリセットボタン
            if st.button("セッションをリセット"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

# メイン実行部分
if __name__ == "__main__":
    # デバッグ情報表示
    show_debug_info()
    
    if st.session_state.page == "admin_login":
        # 管理者ログイン画面
        admin_login_page()
    elif st.session_state.admin_logged_in and st.session_state.page == "admin":
        # 管理者ダッシュボード
        admin_dashboard()
    elif st.session_state.page == "customer" or st.session_state.page == "":
        # お客様向けチャット画面
        customer_chat()
    else:
        # 不正な状態の場合はお客様向けページにリダイレクト
        st.session_state.page = "customer"
        st.rerun()