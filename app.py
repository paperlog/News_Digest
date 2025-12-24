import streamlit as st
import feedparser
import urllib.parse
from datetime import datetime, timedelta
import google.generativeai as genai
from newspaper import Article
import nltk

def format_to_jst(date_str):
    """GMT等の日付文字列を日本時間の読みやすい形式に変換する"""
    try:
        # RSSの日付形式（例: Mon, 24 Dec 2025 10:00:00 GMT）を解析
        # ※feedparserのpublished_parsedを使うとより確実です
        dt_utc = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z')
        # 9時間加算して日本時間にする
        dt_jst = dt_utc + timedelta(hours=9)
        return dt_jst.strftime('%Y年%m月%d日 %H:%M')
    except:
        # 変換に失敗した場合は元の文字列をそのまま返す
        return date_str

# 起動時に一度だけ必要なデータをダウンロード
@st.cache_resource
def download_nltk_data():
    nltk.download('punkt')
    nltk.download('punkt_tab')

download_nltk_data()

# --- サイドバーの設定 ---
with st.sidebar:
    st.title("このアプリについて")
    
    # 1. 運営者情報
    with st.expander("運営者情報"):
        st.write("""
        - **運営者**: 夕波/paperlog
        - **目的**: 若手ビジネスマン向けに政経ニュースをAIで分かりやすく解説します。
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

# Geminiの設定
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

st.title("News Digest")

# --- 1日に1回だけ実行する関数（キャッシュ機能） ---
@st.cache_data(ttl=43200) # 12時間ごとに更新（朝・晩で切り替わるよう調整）
def get_daily_pickup():
    fixed_keyword = "政治・経済"
    encoded_keyword = urllib.parse.quote(fixed_keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"
    
    feed = feedparser.parse(rss_url)
    if not feed.entries:
        return None
    
    # 最大3つの記事までリトライを試みる
    for entry in feed.entries[:3]:
        article_url = entry.link
        try:
            # 本文取得の試行
            full_article = Article(article_url, language='ja')
            full_article.download()
            full_article.parse()
            
            if len(full_article.text) > 200:
                content = f"タイトル: {full_article.title}\n本文: {full_article.text[:2000]}"
            else:
                content = f"タイトル: {entry.title}\n内容: {entry.summary}"
            
            # Geminiで要約試行
            prompt = f"""
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
            response = model.generate_content(prompt)
            
            # 成功したら辞書を返して終了（ループを抜ける）
            if response.text:
                # publishedを日本時間に変換してから格納
                jst_date = format_to_jst(entry.published)
                return {
                    "title": entry.title,
                    "text": response.text,
                    "link": article_url,
                    "published": jst_date
                }
        except Exception as e:
            # 失敗した場合はログに出力して次の記事へ
            print(f"記事取得失敗({article_url}): {e}")
            continue
            
    return None # 全部ダメだった場合

# 検索結果も短時間キャッシュ（例: 1時間）
@st.cache_data(ttl=3600)
def get_summarized_news(fixed_keyword):
    encoded_keyword = urllib.parse.quote(fixed_keyword)
    rss_url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ja&gl=JP&ceid=JP:ja"
    
    feed = feedparser.parse(rss_url)
    if not feed.entries:
        return [] # 見つからない場合は空のリストを返す
    
    summarized_results = [] # 成功した結果を溜めるリスト
    
    # 5つくらいの記事を候補にして、その中から2つ成功するまで回す
    for entry in feed.entries[:5]:
        if len(summarized_results) >= 2: # 2記事溜まったら終了
            break
            
        article_url = entry.link
        try:
            full_article = Article(article_url, language='ja')
            full_article.download()
            full_article.parse()
            
            if len(full_article.text) > 200:
                content = f"タイトル: {full_article.title}\n本文: {full_article.text[:2000]}"
            else:
                content = f"タイトル: {entry.title}\n内容: {entry.summary}"
            
            prompt = f"""
あなたは若手ビジネスマン向けのニュース解説者です。
前置きは一切禁止し、即座に内容を出力してください。
専門用語は使わず、誰でもわかる言葉に言い換えてください。
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
            response = model.generate_content(prompt)
            
            if response.text:
                # publishedを日本時間に変換してから格納
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

# --- 2. トップに「本日のピックアップ」を表示 ---
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

# --------メイン---------

news_categories = [
    "新NISA", "ベースアップ", "賃上げ", "ふるさと納税", "円安 影響", "物価高 対策",
    "働き方改革", "インボイス制度", "所得税 減税", "所得税 増税", "解散総選挙", "社会保険料 改定",
    "生成AI 導入事例", "DX推進", "カーボンニュートラル", "半導体 国産化", "スタートアップ 支援",
    "米中関係", "FRB 利上げ", "原油価格 動向"
]

# ユーザーのキーワード入力
selected_keyword = st.selectbox("テーマ選択", news_categories)
manual_keyword = st.text_input("手動入力欄(調べたいテーマがないとき)")

# 手動入力があればそちらを優先、なければ選択肢を使う
target_keyword = manual_keyword if manual_keyword else selected_keyword

if st.button("ニュースを読み込む"):
    with st.spinner(f"「{target_keyword}」に関する最新ニュースを2件要約中..."):
        # 関数を呼び出す（リストが返ってくる）
        results = get_summarized_news(target_keyword)
        
        if results:
            for i, res in enumerate(results):
                st.markdown(f"## 記事 {i+1}: {res['title']}")
                st.caption(f"公開日: {res['published']}")
                st.markdown(res['text'])
                st.caption(f"[元の記事を読む]({res['link']})")
                st.divider() # 記事の間に区切り線を入れる
        else:
            st.warning("要約できるニュースが見つかりませんでした。別のキーワードを試してください。")


