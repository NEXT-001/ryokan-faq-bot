"""
ユーザーページ（統合型会話AI対応）
pages/user_page.py
"""
import streamlit as st
from config.unified_config import UnifiedConfig
from services.unified_chat_service import UnifiedChatService
from services.history_service import log_interaction
from services.company_service import get_company_name
# GPS機能は削除されました


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
        # ウィジェットのキーは直接クリアせず、rerunで対応
        st.success("会話履歴をクリアしました！")
        st.rerun()
    
    # 📍 位置情報設定（観光・グルメ質問の精度向上のため）
    st.info("🌍 より正確な観光・グルメ情報を提供するため、地域を設定してください")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        city_name = st.text_input(
            "観光・グルメ情報を調べたい地域：",
            key="city_input",
            placeholder="例: 別府市、西宮市、大阪、京都（空欄の場合は旅館周辺）"
        )
    with col2:
        if city_name:
            st.success(f"📍 {city_name}")
        else:
            st.info(f"📍 旅館周辺")
    
    if city_name:
        st.caption(f"💡 {city_name}の観光・グルメ情報を含めて回答します")
    else:
        st.caption(f"💡 未設定の場合は{company_name}周辺の観光・グルメ情報を含めて回答します")
    
    st.markdown("---")
    
    # ユーザー情報入力欄
    user_info = st.text_input("お部屋番号（お名前など：任意）：", key="user_info", placeholder="例: 101")
    
    # 統合チャット入力窓
    user_input = st.text_input(
        "ご質問をどうぞ（FAQ・観光・グルメ何でもお答えします）：", 
        key="user_input", 
        placeholder="例: チェックインの時間は？ / 別府の観光スポットは？ / おすすめのレストランは？"
    )
    st.caption("💡 FAQ、観光情報、グルメ情報をまとめてお答えします")
    
    if user_input:
        with st.spinner("回答を生成中...（FAQ・観光・グルメ情報を統合）"):
            try:
                # 統合チャットサービスを初期化
                unified_chat = UnifiedChatService()
                
                # 位置情報コンテキスト準備
                location_context = {
                    'manual_location': city_name,
                    'gps_coords': None  # GPS使用は停止
                }
                
                # 統合レスポンス取得
                unified_result = unified_chat.get_unified_response(
                    user_input, 
                    company_id, 
                    user_info,
                    location_context
                )
                
                # 履歴記録
                log_interaction(
                    question=user_input,
                    answer=unified_result["answer"],
                    input_tokens=0,  # 統合サービスでトークン数を管理
                    output_tokens=0,
                    company_id=company_id,
                    user_info=user_info
                )
                
                # 会話履歴に追加
                st.session_state.conversation_history.append({
                    "user_info": user_info,
                    "question": user_input, 
                    "answer": unified_result["answer"],
                    "response_type": unified_result["response_type"],
                    "confidence_score": unified_result["confidence_score"],
                    "needs_human_support": unified_result["needs_human_support"]
                })
                
                # 人間サポートが必要な場合の表示
                if unified_result["needs_human_support"]:
                    st.info("📞 担当者に通知いたしました。詳しい回答をお待ちください。")
                    
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
                st.session_state.conversation_history.append({
                    "user_info": user_info,
                    "question": user_input, 
                    "answer": "申し訳ございません。現在システムに問題が発生しております。しばらくお待ちください。",
                    "response_type": "error"
                })

    # 会話履歴の表示（新しいものから上に表示）
    if st.session_state.conversation_history:
        st.subheader("会話履歴")
        with st.container():
            # 最新の5件を逆順で表示（新しいものが上）
            recent_history = st.session_state.conversation_history[-5:]
            for i, exchange in enumerate(reversed(recent_history)):
                question_num = len(recent_history) - i
                st.markdown(f"**質問 {question_num}:** {exchange['question']}")
                st.markdown(f"**回答 {question_num}:** {exchange['answer']}")
                if exchange.get("user_info"):
                    st.markdown(f"**お客様情報:** {exchange['user_info']}")
                st.markdown("---")


    # フッター
    st.markdown("---")
    st.markdown("### 管理者の方")
    st.markdown(f"[🔐 管理者ログイン](?mode=admin&company={company_id})")
