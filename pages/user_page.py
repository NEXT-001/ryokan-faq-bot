"""
ユーザーページ
pages/user_page.py
"""
import streamlit as st
from config.settings import is_test_mode
from services.chat_service import get_response
from services.history_service import log_interaction
from services.company_service import get_company_name


def hide_entire_sidebar():
    """サイドバー全体を非表示にする"""
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
            .css-1d391kg {
                display: none;
            }
            /* メインコンテンツを全幅に */
            .css-18e3th9 {
                padding-left: 1rem;
            }
            .css-1d391kg {
                display: none;
            }
        </style>
    """, unsafe_allow_html=True)


def user_page(company_id):
    """ユーザーページ（mode=user）"""
    # サイドバー全体を非表示
    hide_entire_sidebar()
    
    # 会社名を取得
    try:
        company_name = get_company_name(company_id) or "デモ企業"
    except:
        company_name = "デモ企業"
    
    # タイトル表示
    st.title(f"💬 {company_name} FAQチャットボット")
    
    # テストモードの場合はヒントを表示
    try:
        if is_test_mode():
            st.info("""
            **テストモードで実行中です**
            
            以下のキーワードを含む質問に回答できます:
            チェックイン, チェックアウト, 駐車場, wi-fi, アレルギー, 部屋, 温泉, 食事, 子供, 観光
            """)
    except:
        st.info("⚠️ システムの一部機能が利用できません。基本的なチャット機能のみ動作します。")
    
    # セッション状態の初期化
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    # 履歴クリアボタン
    if st.button("会話履歴をクリア"):
        st.session_state.conversation_history = []
        # 入力欄を空にするために空文字列を設定
        st.session_state["user_input"] = ""
        st.session_state["user_info"] = ""
        st.success("会話履歴をクリアしました！")
    
    # ユーザー情報入力欄
    user_info = st.text_input("お部屋番号：", key="user_info", placeholder="例: 101")
    
    # ユーザー入力
    user_input = st.text_input("ご質問をどうぞ：", key="user_input", placeholder="例: チェックインの時間は何時ですか？")
    st.caption("💡 メッセージ入力後に入力欄から離れると結果が表示されます")
    
    if user_input:
        with st.spinner("回答を生成中..."):
            try:
                # 回答を取得
                response, input_tokens, output_tokens = get_response(
                    user_input, 
                    company_id,
                    user_info
                )
                
                # ログに保存
                log_interaction(
                    question=user_input,
                    answer=response,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    company_id=company_id,
                    user_info=user_info
                )
                
                # 会話履歴に追加
                st.session_state.conversation_history.append({
                    "user_info": user_info,
                    "question": user_input, 
                    "answer": response
                })
                
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                # エラー時のダミー応答
                st.session_state.conversation_history.append({
                    "user_info": user_info,
                    "question": user_input, 
                    "answer": "申し訳ございません。現在システムに問題が発生しております。しばらくお待ちください。"
                })
    
    # 会話履歴の表示
    if st.session_state.conversation_history:
        st.subheader("会話履歴")
        with st.container():
            for i, exchange in enumerate(st.session_state.conversation_history[-5:]):  # 直近5件のみ表示
                st.markdown(f"**質問 {i+1}:** {exchange['question']}")
                st.markdown(f"**回答 {i+1}:** {exchange['answer']}")
                if exchange.get("user_info"):
                    st.markdown(f"**お客様情報:** {exchange['user_info']}")
                st.markdown("---")
    
    # フッター
    st.markdown("---")
    st.markdown("### 管理者の方")
    st.markdown(f"[🔐 管理者ログイン](?mode=admin&company={company_id})")