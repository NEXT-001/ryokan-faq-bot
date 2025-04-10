import streamlit as st
import pandas as pd
from datetime import datetime
import os

HISTORY_FILE = "data/history.csv"

def log_interaction(question, answer, input_tokens, output_tokens):
    """
    ユーザーとの対話をCSVファイルに記録する
    """
    # data ディレクトリが存在しない場合は作成
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # 記録用のデータフレームを作成
    df = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "answer": answer,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }])
    
    # CSVファイルに保存
    if not os.path.exists(HISTORY_FILE):
        df.to_csv(HISTORY_FILE, index=False)
    else:
        df.to_csv(HISTORY_FILE, mode='a', header=False, index=False)

def show_history():
    """
    保存された対話履歴を表示する
    """
    if os.path.exists(HISTORY_FILE):
        try:
            df = pd.read_csv(HISTORY_FILE)
            if len(df) > 0:
                st.subheader("FAQ利用履歴")
                # より見やすいフォーマットで表示
                for i, row in df.iterrows():
                    st.write(f"**日時:** {row['timestamp']}")
                    st.write(f"**質問:** {row['question']}")
                    st.write(f"**回答:** {row['answer']}")
                    st.write(f"**トークン:** 入力 {row['input_tokens']}、出力 {row['output_tokens']}")
                    st.markdown("---")
            else:
                st.info("履歴は空です")
        except Exception as e:
            st.error(f"履歴の読み込みエラー: {e}")
    else:
        st.info("まだ履歴がありません")