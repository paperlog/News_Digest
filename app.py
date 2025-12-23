import streamlit as st
import feedparser
import urllib.parse
import google.generativeai as genai

# Geminiの設定
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

st.title("📰ニュース要約")

# ユーザーが入力したキーワードをURL用にエンコード
keyword = st.text_input("検索したいキーワード", "今日のニュース")
encoded_keyword = urllib.parse.quote(keyword)

# GoogleニュースのRSS URL（日本語、日本リージョン設定）
rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"

if st.button("ニュースを読み込む"):
    # RSSを解析
    feed = feedparser.parse(rss_url)
    
    if not feed.entries:
        st.warning("ニュースが見つかりませんでした。")
    else:
        for entry in feed.entries[:3]: # 最新5件を表示
            st.markdown(f"### {entry.title}")
            st.write(f"📅 {entry.published}")
            
            # 要約用のテキスト（タイトルとサマリーを結合）
            news_content = f"タイトル: {entry.title}\n内容: {entry.summary}"

            with st.spinner("Geminiが考え中..."):
                try:
                    prompt = f"""
以下のニュース記事を、忙しいサラリーマンのために要約してください。
必ず敬語を用い、以下の【見本】と全く同じ改行・段落形式で出力してください。
「」や【見本】という文字、余計な前置きは一切不要です。

【見本】
・[3行要約]
ここに内容を記載します。
ここに内容を記載します。
ここに内容を記載します。

・[業界/社会への影響]
ここに業界全体への影響を丁寧に記載します。

・[今後の注目ポイント]
ここに今後の動向を記載します。

記事内容：
{news_content}
"""
                    response = model.generate_content(prompt)
                    
                    st.markdown(response.text)
                    st.caption(f"[元の記事を読む]({entry.link})")
                except Exception as e:
                    st.error(f"要約中にエラーが発生しました: {e}")
            

            st.divider()

# お問い合わせセクション
st.divider()
st.subheader("📩 お問い合わせ・不具合報告")
st.write("アプリの動作不良や、追加してほしい機能の要望はこちらからご連絡ください。")

col1= st.columns(1)
with col1:
    st.link_button("お問い合わせフォーム", "https://docs.google.com/forms/d/e/1FAIpQLScZcoikvhrNGyq6EJdyb0kWedTkba0kHKkNcMnQQS4rMHDWLw/viewform?usp=dialog")

st.divider()
st.caption("""
**免責事項**
- 本アプリはGoogleニュースのRSSおよびGemini APIを利用して情報を取得・要約しています。
- 要約の結果はAIによる自動生成であり、その正確性や妥当性を保証するものではありません。
- 本アプリの利用により生じた直接的・間接的な損害について、開発者は一切の責任を負いません。
- ニュース記事の著作権は、各配信元に帰属します。
""")













