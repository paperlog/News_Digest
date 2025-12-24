import streamlit as st
import feedparser
import urllib.parse
from datetime import datetime, timedelta
import google.generativeai as genai
from newspaper import Article
import nltk

# --- 初期設定 ---
def format_to_jst(date_str):
    """GMT等の日付文字列を日本時間の読みやすい形式に変換する"""
    try:
        dt_utc = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        dt_jst = dt_utc + timedelta(hours=9)
        return dt_jst.strftime('%Y年%m月%d日 %H:%M')
    except:
        return date_str

@st.cache_resource
def download_nltk_data():
    nltk.download('punkt')
    nltk.download('punkt_tab')

download_nltk_data()

# Geminiの設定
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

# --- ロジックの共通化 ---

def create_prompt(content):
    """AIへのプロンプトを作成する"""
    return f"""
あなたは若手ビジネスマン向けのニュース解説者です。
前置き（「多忙なところ〜」「解説しましょう」等）は一切禁止し、即座に内容を出力してください。
専門用語（デカップリング、地政学的リスク、バタフライエフェクト等）は使わず、誰でもわかる言葉に言い換えてください。
全体的に短く、簡潔にまとめてください。また、必ず敬語を使用してください。

【形式】
・[10秒でわかる要約]
（結論を3行以内で。専門用語は禁止）

・[なぜこれが大事なの？]
（自分たちの仕事や生活にどう影響するか、100文字程度で簡単に）

・[明日使える雑談ネタ]
（上司や同僚にそのまま言える意外な事実の「短文」を2つまで）

【ニュース情報】
{content}
"""

def get_news(keyword, max_results=2):
    """
    指定されたキーワードでニュースを取得し、要約してリストで返す
    max_results: 正常に要約できた記事をいくつまで取得するか
    """
    encoded_keyword = urllib.parse.quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"
    
    feed = feedparser.parse(rss_url)
    if not feed.entries:
        return []
    
    summarized_results = []
    
    # 取得失敗を考慮し、少し多め（5件）にループを回す
    for entry in feed.entries[:5]:
        if len(summarized_results) >= max_results:
            break
            
        article_url = entry.link
        try:
            # 本文取得
            full_article = Article(article_url, language='ja')
            full_article.download()
            full_article.parse()
            
            if len(full_article.text) > 200:
                content = f"タイトル: {full_article.title}\n本文: {full_article.text[:2000]}"
            else:
                content = f"タイトル: {entry.title}\n内容: {entry.summary}"
            
            # 要約生成
            prompt_text = create_prompt(content)
            response = model.generate_content(prompt_text)
            
            if response.text:
                jst_date = format_to_jst(entry.published)
                summarized_results.append({
                    "title": entry.title,
                    "text": response.text,
                    "link": article_url,
                    "published": jst_date
                })
        except Exception as e:
            print(f"記事取得失敗({article_url}): {e}")
            continue
            
    return summarized_results

# --- キャッシュ層 ---

@st.cache_data(ttl=43200)
def get_daily_pickup():
    """12時間キャッシュ：政治・経済のトップ1件"""
    results = get_news("政治・経済", max_results=1)
    return results[0] if results else None

@st.cache_data(ttl=10800)
def get_summarized_news(keyword):
    """3時間キャッシュ：指定キーワード2件"""
    return get_news(keyword, max_results=2)

# --- UI (サイドバー) ---
with st.sidebar:
    st.title("このアプリについて")
    
    # 1. 運営者情報
    with st.expander("運営者情報"):
        st.write("""
        - **運営者**: 夕波/paperlog
        - **目的**: 普段ニュースを読む時間がない、めんどくさい人へ  
                    ニュースを早く、わかりやすく
        """)

    # 2. お問い合わせ（ボタンをサイドバーに）
    with st.expander("お問い合わせ"):
        st.write("不具合報告やご要望はこちら")
        st.link_button("フォームを開く", "https://docs.google.com/forms/d/e/1FAIpQLScZcoikvhrNGyq6EJdyb0kWedTkba0kHKkNcMnQQS4rMHDWLw/viewform?usp=dialog")

    # 3. プライバシーポリシー & 免責事項（これらを1つにまとめるとスッキリします）
    with st.expander("利用規約・免責事項"):
        st.caption("""
        **免責事項**
        - 要約結果はAIによる自動生成であり、正確性を保証しません。
        - 本アプリの利用による損害について、開発者は一切の責任を負いません。
        - 記事の著作権は各配信元に帰属します。
        
        **プライバシーポリシー**
        - 検索キーワードはニュース取得と要約に使用されます。
        - 広告配信（Googleアドセンス）に伴いCookieを使用する場合があります。
        """)

# --- UI (メイン) ---
st.title("News Digest")

# 本日のピックアップ
st.subheader("本日のピックアップニュース")
daily_data = get_daily_pickup()
if daily_data:
    with st.expander(f"今日の重要トピック：{daily_data['title']}", expanded=True):
        st.caption(f"公開日: {daily_data['published']}")
        st.markdown(daily_data['text'])
        st.caption(f"[元の記事を読む]({daily_data['link']})")
else:
    st.write("今日のニュースを読み込み中です...")

st.divider()

# キーワード検索
news_categories = ["新NISA", "賃上げ", "ふるさと納税", "働き方改革", "生成AI 導入事例", "DX推進"]
selected_keyword = st.selectbox("テーマ選択", news_categories)
manual_keyword = st.text_input("手動入力欄(調べたいテーマがないとき)")
target_keyword = manual_keyword if manual_keyword else selected_keyword

if st.button("ニュースを読み込む"):
    with st.spinner(f"「{target_keyword}」に関する最新ニュースを要約中..."):
        results = get_summarized_news(target_keyword)
        if results:
            for i, res in enumerate(results):
                st.markdown(f"### 記事 {i+1}: {res['title']}")
                st.caption(f"公開日: {res['published']}")
                st.markdown(res['text'])
                st.caption(f"[元の記事を読む]({res['link']})")
                st.divider()
        else:
            st.warning("ニュースが見てかりませんでした。")

