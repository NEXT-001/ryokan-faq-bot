# history_service.py
import streamlit as st
import pandas as pd
from datetime import datetime
import os

HISTORY_FILE = "data/history.csv"

# ログ記録関数も部屋番号に対応させる
def log_interaction(question, answer, input_tokens, output_tokens, room_number=""):
    """
    ユーザーとの対話をCSVファイルに記録する
    部屋番号情報を追加
    改行を処理して安全に保存
    """
    # data ディレクトリが存在しない場合は作成
    if not os.path.exists("data"):
        os.makedirs("data")
    
    # 改行を含む可能性のあるテキストから改行を削除
    def sanitize_text(text):
        if isinstance(text, str):
            # 改行をスペースに置換
            return text.replace('\n', ' ').replace('\r', ' ')
        return text
    
    # 記録用のデータフレームを作成
    df = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "room_number": sanitize_text(room_number),  # 部屋番号を追加
        "question": sanitize_text(question),
        "answer": sanitize_text(answer),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }])
    
    # CSVファイルに保存
    file_exists = os.path.exists(HISTORY_FILE)
    
    try:
        # 改行文字の削除に加えて、CSVライブラリを使って適切に引用符処理
        if not file_exists:
            df.to_csv(HISTORY_FILE, index=False, quoting=1)  # quoting=1 は csv.QUOTE_ALL と同等
        else:
            df.to_csv(HISTORY_FILE, mode='a', header=False, index=False, quoting=1)
        
        print(f"対話を記録しました: {HISTORY_FILE}")
    except Exception as e:
        print(f"対話記録エラー: {e}")

def show_history():
    """
    保存された対話履歴を表示する
    """
    if os.path.exists(HISTORY_FILE):
        try:
            # カスタムCSV読み込み - パースエラーに対処
            import csv
            
            # 手動でCSVを読み込み
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # データを前処理 - 行の終わりが正しいか確認
            processed_content = []
            in_quotes = False
            current_line = ""
            
            for char in content:
                if char == '"':
                    in_quotes = not in_quotes
                
                current_line += char
                
                # 引用符の外で改行に達した場合、それは実際の行区切り
                if char == '\n' and not in_quotes:
                    processed_content.append(current_line.strip())
                    current_line = ""
            
            # 最後の行があれば追加
            if current_line:
                processed_content.append(current_line.strip())
            
            # リストからCSVを読み込む
            from io import StringIO
            csv_data = StringIO('\n'.join(processed_content))
            
            # カラム名を明示的に指定
            columns = ["timestamp", "room_number", "question", "answer", "input_tokens", "output_tokens"]
            df = pd.read_csv(csv_data, names=columns, quotechar='"', escapechar='\\')
            
            if len(df) > 0:
                st.subheader("FAQ利用履歴")
                # 部屋番号も表示するように変更
                for i, row in df.iterrows():
                    st.write(f"**日時:** {row['timestamp']}")
                    
                    # 部屋番号があれば表示
                    if 'room_number' in row and pd.notna(row['room_number']) and row['room_number']:
                        st.write(f"**部屋番号:** {row['room_number']}")
                    
                    st.write(f"**質問:** {row['question']}")
                    st.write(f"**回答:** {row['answer']}")
                    
                    # トークン情報が存在する場合のみ表示
                    if 'input_tokens' in row and 'output_tokens' in row:
                        st.write(f"**トークン:** 入力 {row['input_tokens']}、出力 {row['output_tokens']}")
                    
                    st.markdown("---")
            else:
                st.info("履歴は空です")
        except Exception as e:
            st.error(f"履歴の読み込みエラー: {str(e)}")
            # デバッグ情報を表示（開発中のみ使用し、本番では削除してください）
            import traceback
            st.error(traceback.format_exc())
    else:
        st.info("まだ履歴がありません")