import os
from dotenv import load_dotenv
from flask import Flask, request, render_template_string
from tavily import TavilyClient
from openai import OpenAI

# .env 読み込み（app.py と同じフォルダに .env がある前提）
load_dotenv()

app = Flask(__name__)

tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

MODEL_NAME = "gpt-4.1-mini"

HTML = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>Web検索連動チャットボット</title>
  <style>
    body { font-family: sans-serif; margin: 24px; }
    textarea { width: 100%; height: 90px; }
    .box { white-space: pre-wrap; border: 1px solid #ddd; padding: 12px; margin-top: 12px; border-radius: 8px; }
    .hint { color: #666; font-size: 13px; }
  </style>
</head>
<body>
  <h1>Web検索連動チャットボット</h1>
  <p class="hint">TavilyでWeb検索 → 検索結果を根拠にChatGPTが要約します（URL付き）</p>

  <form method="post">
    <label>質問（例：最近1週間のAIニュースを3つ要約して）</label><br>
    <textarea name="q">{{ q }}</textarea><br><br>
    <button type="submit">検索して回答</button>
  </form>

  {% if answer %}
    <h2>回答</h2>
    <div class="box">{{ answer }}</div>
  {% endif %}
</body>
</html>
"""

def build_search_text(result: dict) -> str:
    text = ""
    for item in result.get("results", []):
        text += f"タイトル: {item.get('title','')}\n"
        text += f"概要: {item.get('content','')}\n"
        text += f"URL: {item.get('url','')}\n\n"
    return text

@app.route("/", methods=["GET", "POST"])
def index():
    q = ""
    answer = ""

    if request.method == "POST":
        q = request.form.get("q", "").strip()

        if not q:
            answer = "質問を入力してください。"
            return render_template_string(HTML, q=q, answer=answer)

        # ① Tavily検索（まとめページを避けるための除外ワード入り）
        query = q + " -compass -theme -topics -word -tag -category -archive -ranking"
        result = tavily.search(query=query, max_results=5)
        search_text = build_search_text(result)

        # ② ChatGPTで要約（検索結果のみ根拠）
        prompt = f"""
以下はWeb検索で取得した情報です。
この情報だけを根拠にして、重要な項目を3つ選び、日本語で要約してください。

【出力ルール】
- 3件
- 各項目は「タイトル（30文字以内）」「要約（120文字以内）」「URL」の3行
- 書式は必ず以下：

1)
タイトル:
要約:
URL:

2)
タイトル:
要約:
URL:

3)
タイトル:
要約:
URL:

【検索結果】
{search_text}
"""

        try:
            response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
        {
            "role": "system",
            "content": "あなたはニュース案内係のキャラクターです。丁寧に、検索結果だけを根拠に要約してください。"
        },
        {
            "role": "user",
            "content": prompt
        },
    ],
)

            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"エラーが発生しました: {e}"

    return render_template_string(HTML, q=q, answer=answer)

if __name__ == "__main__":
    app.run(debug=True)



