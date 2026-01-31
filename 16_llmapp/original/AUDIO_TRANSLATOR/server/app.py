from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR.parent / "web"
GLOSSARY_PATH = BASE_DIR / "data" / "glossary.txt"

app = Flask(__name__)


def load_glossary(path: Path):
    """
    glossary.txt の形式:
      alias1, alias2, ... | 固定訳 | 説明
    例:
      implant, インプラント | インプラント | 顎骨に埋入する人工歯根
    """
    items = []
    if not path.exists():
        return items

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            term, translation, note = parts[:3]
            items.append(
                {"term": term, "translation": translation, "note": note}
            )

    # 長い用語を先にマッチさせたい（例：implant body が implant より先）
    def max_alias_len(item):
        aliases = [a.strip() for a in item["term"].split(",") if a.strip()]
        return max((len(a) for a in aliases), default=0)

    items.sort(key=max_alias_len, reverse=True)
    return items


GLOSSARY = load_glossary(GLOSSARY_PATH)


def detect_direction(text: str) -> str:
    # 日本語が含まれていれば JA->EN、そうでなければ EN->JA（ざっくり）
    for ch in text:
        if "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff":
            return "JA2EN"
    return "EN2JA"


def find_terms(text: str):
    """
    入力文に含まれる重要語を返す（日本語/英語の両方対応）。
    左側(aliases)に「implant, インプラント」のように書いておけば、
    どちらが文中に出ても検出します。
    """
    found = []
    used = set()

    for item in GLOSSARY:
        aliases = [a.strip() for a in item["term"].split(",") if a.strip()]

        for alias in aliases:
            # 日本語はそのまま、英語は小文字でも判定
            if alias in text or alias.lower() in text.lower():
                key = item["translation"]  # 重複表示防止（同じ固定訳は1回だけ）
                if key not in used:
                    found.append(item)
                    used.add(key)
                break

    return found


def translate_with_terms(text: str, direction: str, terms: list) -> str:
    if direction == "AUTO":
        direction = detect_direction(text)

    # 用語ルール（固定訳）
    rules = ""
    if terms:
        rules = "Use the following fixed translations:\n"
        for t in terms:
            # aliasのうち英語っぽいもの（最初）を代表として見せる
            representative = t["term"].split(",")[0].strip().lower()
            rules += f"- {representative} = {t['translation']}\n"

    if direction == "JA2EN":
        sys = (
            "Translate Japanese into natural English. Keep meaning and tone. "
            "Do not summarize.\n" + rules
        )
    else:
        sys = (
            "Translate English into natural Japanese. Keep meaning and tone. "
            "Do not summarize.\n" + rules
        )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": text},
        ],
    )
    return resp.choices[0].message.content.strip()


@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/style.css")
def style():
    return send_from_directory(WEB_DIR, "style.css")


@app.get("/main.js")
def js():
    return send_from_directory(WEB_DIR, "main.js")


@app.post("/api/translate")
def api_translate():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    direction = (data.get("direction") or "AUTO").strip()

    if not text:
        return jsonify({"translated": "", "terms": []})

    terms = find_terms(text)
    translated = translate_with_terms(text, direction, terms)

    return jsonify({"translated": translated, "terms": terms})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
