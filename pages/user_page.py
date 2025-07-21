"""
ユーザーページ
pages/user_page.py
"""
import streamlit as st
from config.unified_config import UnifiedConfig
from services.chat_service import get_response
from services.history_service import log_interaction
from services.company_service import get_company_name
from streamlit_js_eval import get_geolocation
from services.tourism_service import detect_language, generate_tourism_response_by_city


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
    
    # セッション状態の初期化
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []
    
    # 履歴クリアボタン
    if st.button("会話履歴をクリア"):
        st.session_state.conversation_history = []
        st.session_state["user_input"] = ""
        st.session_state["user_info"] = ""
        st.session_state["city_input"] = ""
        st.session_state["tourism_input"] = ""
        st.success("会話履歴をクリアしました！")
    
    # ユーザー情報入力欄
    user_info = st.text_input("お部屋番号：", key="user_info", placeholder="例: 101")
    
    # FAQ質問窓
    user_input = st.text_input("ご質問をどうぞ：", key="user_input", placeholder="例: チェックインの時間は何時ですか？")
    st.caption("💡 メッセージ入力後に入力欄から離れると結果が表示されます")
    
    if user_input:
        with st.spinner("回答を生成中..."):
            try:
                response, input_tokens, output_tokens = get_response(
                    user_input, 
                    company_id,
                    user_info
                )
                log_interaction(
                    question=user_input,
                    answer=response,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    company_id=company_id,
                    user_info=user_info
                )
                st.session_state.conversation_history.append({
                    "user_info": user_info,
                    "question": user_input, 
                    "answer": response
                })
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.session_state.conversation_history.append({
                    "user_info": user_info,
                    "question": user_input, 
                    "answer": "申し訳ございません。現在システムに問題が発生しております。しばらくお待ちください。"
                })

    # 会話履歴の表示
    if st.session_state.conversation_history:
        st.subheader("会話履歴")
        with st.container():
            for i, exchange in enumerate(st.session_state.conversation_history[-5:]):
                st.markdown(f"**質問 {i+1}:** {exchange['question']}")
                st.markdown(f"**回答 {i+1}:** {exchange['answer']}")
                if exchange.get("user_info"):
                    st.markdown(f"**お客様情報:** {exchange['user_info']}")
                st.markdown("---")

    # 🔹 追加部分：観光・交通情報専用UI
    st.markdown("---")
    st.header("🌍 周辺観光・グルメ情報 AI ガイド")

    # 都市名入力フィールド（メイン）
    city_name = st.text_input(
        "都市名または地域名を入力してください：",
        key="city_input",
        placeholder="例: 大分市、別府市、西宮市、大阪、京都"
    )
    st.caption("💡 正確な情報のため、都市名・地域名の入力をおすすめします")

    tourism_question = st.text_input(
        "周辺の観光・グルメについて質問してみてください！",
        key="tourism_input",
        placeholder="例: おすすめの観光スポットは？美味しいレストランは？"
    )

    if tourism_question and city_name:
        with st.spinner("観光・グルメ情報を取得中..."):
            try:
                user_lang = detect_language(tourism_question)
                
                # 都市名ベースで検索（メイン機能）
                answer, links = generate_tourism_response_by_city(tourism_question, city_name, user_lang)

                st.markdown(f"**回答:**\n\n{answer}")

                # ぐるなびとじゃらんのリンクのみ表示
                for l in links:
                    if 'ぐるなび' in l['name'] or 'じゃらん' in l['name'] or 'Gurunavi' in l['name'] or 'Jalan' in l['name']:
                        st.markdown(f"**[{l['name']}]({l['map_url']})**")

            except Exception as e:
                st.error(f"観光・グルメ情報取得中にエラーが発生しました: {str(e)}")
    elif tourism_question and not city_name:
        st.warning("都市名または地域名を入力してください。")

    # フッター
    st.markdown("---")
    st.markdown("### 管理者の方")
    st.markdown(f"[🔐 管理者ログイン](?mode=admin&company={company_id})")
