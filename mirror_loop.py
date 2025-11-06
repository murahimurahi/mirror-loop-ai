import os, json, logging, re
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------- text cleaners ----------
HEAD_NUM = re.compile(r"^\s*(?:\(?\s*[\d０-９]+\s*\)?[\.．\)]\s*)", re.MULTILINE)
LABELS   = re.compile(r"^(要約|助言|次の一言|カテゴリ)\s*[:：]\s*", re.MULTILINE)
EMOJIS   = re.compile(r"[💡⭐️✨🔥✅▶️➤→•●◆■◉※★☆◎○●▲△■□◆◇]")

def _clean_line(s: str) -> str:
    if not s: return ""
    s = HEAD_NUM.sub("", s)
    s = LABELS.sub("", s)
    s = EMOJIS.sub("", s)
    return s.strip()

def _sanitize(d):
    return {
        "summary": _clean_line(d.get("summary", "")),
        "advice":  _clean_line(d.get("advice", "")),
        "next":    _clean_line(d.get("next", "")),
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/reflect", methods=["POST"])
def reflect():
    user_input = (request.json or {}).get("user_input", "").strip()
    if not user_input:
        return jsonify({"error": "入力が空です"}), 400

    sys = (
        "あなたは温かいトーンのAIコーチ。返答は必ずJSON一行で、"
        "キーは summary, advice, next。絵文字や番号は不要。"
        "思いやりを込め、声に出して自然に聞こえるよう短く答えて。"
    )
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": f"入力文：{user_input}。3つの短い返答で。"}
        ],
        temperature=0.9,
    )
    raw = r.choices[0].message.content.strip()
    data = {"summary": "", "advice": "", "next": ""}
    try:
        data.update(json.loads(raw))
    except Exception:
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if lines: data["summary"] = lines[0]
        if len(lines)>1: data["advice"] = lines[1]
        if len(lines)>2: data["next"] = lines[2]
    return jsonify({"reply": _sanitize(data)})

@app.route("/summarize", methods=["POST"])
def summarize():
    """複数Reflect結果を受け取り、その日のまとめを生成"""
    items = (request.json or {}).get("items", [])
    if not items:
        return jsonify({"error": "データがありません"}), 400
    text = "\n".join(f"- {i}" for i in items)
    sys = (
        "あなたは共感的な日記ライター。"
        "以下のReflectメモを1日の流れとして温かく要約してください。"
        "出力は話し言葉の自然な1段落で。"
    )
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": text}
        ],
        temperature=0.8,
    )
    summary = r.choices[0].message.content.strip()
    return jsonify({"summary": summary})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
