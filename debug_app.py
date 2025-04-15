"""
デバッグ用の簡易Webアプリケーション
Streamlitを使って、FAQシステムをデバッグするためのインターフェースを提供
"""
import streamlit as st
import os
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from services.embedding_service import get_embedding, get_test_embedding
from services.chat_service import get_response

# ページ設定
st.set_page_config(page_title="FAQ Bot デバッグ", page_icon="🐞", layout="wide")

# タイトル
st.title("FAQ Bot デバッグインターフェース")

# テストモードの状態
test_mode_state = st.sidebar.checkbox("テストモードを有効化", value=True)
if test_mode_state:
    os.environ["TEST_MODE"] = "true"
    st.sidebar.success("テストモードが有効です")
else:
    os.environ["TEST_MODE"] = "false"
    st.sidebar.warning("本番モードで実行中")

# FAQデータの確認
if os.path.exists("data/faq_with_embeddings.pkl"):
    st.sidebar.success("FAQデータが存在します")
    df = pd.read_pickle("data/faq_with_embeddings.pkl")
    st.sidebar.info(f"FAQエントリ数: {len(df)}")
else:
    st.sidebar.error("FAQデータが存在しません")
    df = None

# タブの設定
tab1, tab2, tab3 = st.tabs(["FAQチャット", "エンベディング分析", "データ表示"])

# タブ1: FAQチャット
with tab1:
    st.header("FAQチャットデバッグ")
    
    # 入力フォーム
    with st.form("chat_form"):
        user_input = st.text_input("質問を入力してください:", "温泉について教えてください")
        room_number = st.text_input("部屋番号 (任意):", "101")
        submit_button = st.form_submit_button("送信")
    
    if submit_button:
        # 回答を取得
        with st.spinner("回答を生成中..."):
            answer, q_words, a_words = get_response(user_input, room_number)
        
        # 結果の表示
        st.subheader("チャット結果")
        st.write("**質問:**")
        st.info(user_input)
        st.write("**回答:**")
        st.success(answer)
        
        # デバッグ情報
        st.subheader("デバッグ情報")
        st.write(f"質問の単語数: {q_words}")
        st.write(f"回答の単語数: {a_words}")
        
        # もしFAQデータが存在する場合、類似度情報を表示
        if df is not None:
            st.subheader("類似度情報")
            
            # ユーザー入力のエンベディングを取得
            if test_mode_state:
                user_embedding = get_test_embedding(user_input)
                st.write("テストモードのエンベディングを使用")
            else:
                user_embedding = get_embedding(user_input)
                st.write("本番モードのエンベディングを使用")
            
            # 類似度の計算
            embeddings_list = []
            for emb in df["embedding"]:
                if isinstance(emb, str):
                    # 文字列からリストに変換
                    emb = eval(emb)
                embeddings_list.append(emb)
            
            similarities = cosine_similarity([user_embedding], embeddings_list)[0]
            
            # 結果をデータフレームにまとめる
            result_df = pd.DataFrame({
                "質問": df["question"],
                "類似度": similarities,
                "回答": df["answer"]
            })
            
            # 類似度の高い順にソート
            result_df = result_df.sort_values(by="類似度", ascending=False).reset_index(drop=True)
            
            # 結果の表示
            st.dataframe(result_df.head(5))

# タブ2: エンベディング分析
with tab2:
    st.header("エンベディング分析")
    
    if df is not None:
        # エンベディングの基本情報
        st.subheader("エンベディング基本情報")
        
        # 最初のエンベディングを取得
        first_embedding = df["embedding"].iloc[0]
        if isinstance(first_embedding, str):
            first_embedding = eval(first_embedding)
        
        st.write(f"エンベディングの次元数: {len(first_embedding)}")
        
        # テスト用テキストの入力
        test_text = st.text_input("テスト用テキスト:", "温泉の効能について")
        
        if st.button("エンベディングを生成"):
            with st.spinner("エンベディングを生成中..."):
                # テストモードと本番モードの両方のエンベディングを生成
                test_embedding = get_test_embedding(test_text)
                
                # 結果の表示
                st.subheader("生成されたエンベディング")
                st.write("テストモードのエンベディング (先頭10要素):")
                st.write(test_embedding[:10])
                
                # ヒストグラムの表示
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(10, 5))
                ax.hist(test_embedding, bins=50)
                ax.set_title("エンベディングの分布")
                ax.set_xlabel("値")
                ax.set_ylabel("頻度")
                st.pyplot(fig)
                
                # FAQデータとの類似度
                st.subheader("FAQデータとの類似度")
                
                # すべてのエンベディングを取得
                embeddings_list = []
                for emb in df["embedding"]:
                    if isinstance(emb, str):
                        # 文字列からリストに変換
                        emb = eval(emb)
                    embeddings_list.append(emb)
                
                similarities = cosine_similarity([test_embedding], embeddings_list)[0]
                
                # 結果をデータフレームにまとめる
                result_df = pd.DataFrame({
                    "質問": df["question"],
                    "類似度": similarities
                })
                
                # 類似度の高い順にソート
                result_df = result_df.sort_values(by="類似度", ascending=False).reset_index(drop=True)
                
                # 結果の表示
                st.dataframe(result_df)
    else:
        st.error("FAQデータが存在しないため、分析できません。")

# タブ3: データ表示
with tab3:
    st.header("FAQデータ")
    
    if df is not None:
        # FAQデータの表示
        st.dataframe(df[["question", "answer"]])
        
        # エンベディングの統計情報
        st.subheader("エンベディングの統計情報")
        
        # エンベディングを取得
        embeddings_list = []
        for emb in df["embedding"]:
            if isinstance(emb, str):
                # 文字列からリストに変換
                emb = eval(emb)
            embeddings_list.append(emb)
        
        # 類似度行列を計算
        similarity_matrix = cosine_similarity(embeddings_list)
        
        # 対角要素を0にする
        np.fill_diagonal(similarity_matrix, 0)
        
        # 統計情報
        avg_similarity = np.mean(similarity_matrix)
        max_similarity = np.max(similarity_matrix)
        min_similarity = np.min(similarity_matrix)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均類似度", f"{avg_similarity:.4f}")
        with col2:
            st.metric("最大類似度", f"{max_similarity:.4f}")
        with col3:
            st.metric("最小類似度", f"{min_similarity:.4f}")
        
        # 最も類似しているペアを見つける
        max_i, max_j = np.unravel_index(np.argmax(similarity_matrix), similarity_matrix.shape)
        
        st.subheader("最も類似しているペア")
        st.write(f"質問1: {df['question'].iloc[max_i]}")
        st.write(f"質問2: {df['question'].iloc[max_j]}")
        st.write(f"類似度: {similarity_matrix[max_i, max_j]:.4f}")
        
        # ヒートマップの表示
        st.subheader("類似度ヒートマップ")
        
        if st.checkbox("ヒートマップを表示"):
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            fig, ax = plt.subplots(figsize=(10, 8))
            sns.heatmap(similarity_matrix, cmap='viridis', ax=ax)
            ax.set_title("FAQエントリ間の類似度")
            st.pyplot(fig)
    else:
        st.error("FAQデータが存在しないため、表示できません。")

# FAQデータを更新するオプション
st.sidebar.subheader("FAQデータの操作")

if st.sidebar.button("FAQデータを再生成"):
    # 修正: サイドバー内のスピナーをメインスピナーに変更
    st.sidebar.text("FAQデータを再生成中...")
    
    from services.embedding_service import create_embeddings
    
    # テストモードを一時的に有効化して再生成
    temp_test_mode = os.environ.get("TEST_MODE", "false")
    os.environ["TEST_MODE"] = "true"
    
    try:
        with st.spinner("FAQデータを再生成中..."):
            create_embeddings()
        st.sidebar.success("FAQデータを再生成しました。ページを更新してください。")
    except Exception as e:
        st.sidebar.error(f"FAQデータの再生成中にエラーが発生しました: {e}")
    
    # 元のテストモード設定を復元
    os.environ["TEST_MODE"] = temp_test_mode