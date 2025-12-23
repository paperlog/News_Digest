import streamlit as st
import feedparser
import urllib.parse
import google.generativeai as genai

# Geminiの設定
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

st.title("News Digest")

news_categories = [
    "新NISA", "ベースアップ", "賃上げ", "ふるさと納税", "円安 影響", "物価高 対策",
    "働き方改革", "インボイス制度", "所得税 減税", "所得税 増税", "解散総選挙", "社会保険料 改定",
    "生成AI 導入事例", "DX推進", "カーボンニュートラル", "半導体 国産化", "スタートアップ 支援",
    "米中関係", "FRB 利上げ", "原油価格 動向"
]

# ユーザーが入力する代わりに選択肢を作る
keyword = st.selectbox("テーマ選択", news_categories)

keyword = st.text_input("手動入力欄(調べたいテーマがないとき)", news_categories)

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
以下のニュースを、政治・経済に詳しくない若手ビジネスマンのために要約してください。
必ず敬語を用い、以下の【形式】で出力してください。

【形式】
・[10秒でわかる要約]
（専門用語を使わず、結論を3行で記載してください）

・[なぜこれが大事なの？]
（社会や自分たちの生活にどう影響するか、噛み砕いて解説してください）

・[明日使える雑談ネタ]
（上司や同僚とこのニュースについて話すときの一言ヒントを記載してください）

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
st.subheader("お問い合わせ・不具合報告")
st.write("アプリの動作不良や、追加してほしい機能の要望はこちらからご連絡ください。")

st.link_button("お問い合わせフォーム", "https://docs.google.com/forms/d/e/1FAIpQLScZcoikvhrNGyq6EJdyb0kWedTkba0kHKkNcMnQQS4rMHDWLw/viewform?usp=dialog")

st.divider()
st.caption("""
**免責事項**
- 本アプリはGoogleニュースのRSSおよびGemini APIを利用して情報を取得・要約しています。
- 要約の結果はAIによる自動生成であり、その正確性や妥当性を保証するものではありません。
- 本アプリの利用により生じた直接的・間接的な損害について、開発者は一切の責任を負いません。
- ニュース記事の著作権は、各配信元に帰属します。
""")



















