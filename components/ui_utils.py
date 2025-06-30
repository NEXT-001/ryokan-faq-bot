# components/ui_utils.py - UI共通機能
import streamlit as st

def hide_sidebar_navigation():
    """Streamlitのデフォルトページナビゲーションを非表示にする（管理モードのサイドバーは保持）"""
    st.markdown("""
        <style>
            /* サイドバーのページナビゲーションのみを非表示（サイドバー自体は保持） */
            .css-1d391kg {display: none !important;}
            .css-17lntkn {display: none !important;}
            .css-pkbazv {display: none !important;}
            
            /* 新しいStreamlitバージョン対応 */
            [data-testid="stSidebarNav"] {display: none !important;}
            [data-testid="stSidebarNavItems"] {display: none !important;}
            [data-testid="stSidebarNavLink"] {display: none !important;}
            
            /* ナビゲーションリンク全般を非表示 */
            div[data-testid="stSidebar"] nav {display: none !important;}
            div[data-testid="stSidebar"] ul {display: none !important;}
            div[data-testid="stSidebar"] li {display: none !important;}
            div[data-testid="stSidebar"] a[href*="main"] {display: none !important;}
            div[data-testid="stSidebar"] a[href*="verify"] {display: none !important;}
            
            /* より具体的なナビゲーション要素のみを非表示 */
            .stSidebar .css-1544g2n {display: none !important;}
            .stSidebar .css-10trblm {display: none !important;}
            
            /* Streamlit最新版のナビゲーション要素 */
            [class*="navigation"] {display: none !important;}
            [class*="nav-link"] {display: none !important;}
            [class*="sidebar-nav"] {display: none !important;}
            
            /* 最新版対応 - ナビゲーション部分のみ */
            .st-emotion-cache-1cypcdb {display: none !important;}
            .st-emotion-cache-pkbazv {display: none !important;}
            .st-emotion-cache-1rs6os {display: none !important;}
            .st-emotion-cache-16txtl3 {display: none !important;}
        </style>
    """, unsafe_allow_html=True)

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

def show_admin_sidebar():
    """管理者サイドバーを確実に表示するための設定"""
    st.markdown("""
        <style>
            /* サイドバー自体は表示する */
            [data-testid="stSidebar"] {
                display: block !important;
            }
            section[data-testid="stSidebar"] {
                display: block !important;
            }
        </style>
    """, unsafe_allow_html=True)