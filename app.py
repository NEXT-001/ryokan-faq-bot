import streamlit as st

# 最小構成のテスト
st.title("🏨 旅館FAQボット - テスト版")
st.write("アプリが正常に動作しています！")

# 簡単なインタラクション
name = st.text_input("お名前を入力してください:")
if name:
    st.success(f"こんにちは、{name}さん！")

# デバッグ情報
st.sidebar.write("デバッグ情報:")
st.sidebar.write(f"Streamlitバージョン: {st.__version__}")

# ヘルスチェック用
if st.button("動作テスト"):
    st.balloons()
    st.write("✅ アプリは正常に動作しています")