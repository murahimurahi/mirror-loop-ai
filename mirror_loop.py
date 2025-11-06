import os, json, logging, re
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------- text cleaners (数字/ラベル/記号を読み上げから除去) ----------
HEAD_NUM = re.compile(r"^\s*(?:\(?\s*[\d０-９]+\s*\)?[\.．\)]\s*)", re.MULTILINE)
LABELS   = re.compile(r"^(要約|助言|次の一言|カテゴリ)\s*[:：]\s*", re.MULTILINE)
BULLETS  = re.compile(r"^\s*[・\-＊*•●◆■◉▶▷➤→]\s*", re.MULTILINE)
EMOJIS   = re.compile(r"[💡⭐️✨🔥✅▶️➤→•●◆■◉※★☆◎○●▲△■□◆◇]")

def _clean_line(s: str) -> str:
    if not s: return ""
    s = HEAD_NUM.sub("", s)
    s = LABELS.sub("", s)
    s = BULLETS.sub("", s)
    s = EMOJIS.sub("", s)
    return s.strip()

def _sanitize(d):
    return {
        "summary": _clean_line(d.get("summary", "")),
        "advice":  _clean_line(d.get("advice", "")),
        "next":    _clean_line(d.get("next", "")),
    }

# ---------- routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/reflect", methods=["POST"])
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "入力が空です"}), 400

        sys = (
            "あなたは丁寧な日本語コーチ。出力は必ずJSON一行。"
            "キーは summary, advice, next。"
            "数字やラベル（要約/助言/次の一言/カテゴリ）や絵文字は付けない。"
            "声に出して自然に聞こえる短文で。"
        )

        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": f"入力文：{user_input}。3つの短い返答で。"}
            ],
            temperature=0.85,
        )

        raw = r.choices[0].message.content.strip()
        data = {"summary": "", "advice": "", "next": ""}
        try:
            data.update(json.loads(raw))
        except Exception:
            parts = [p.strip() for p in raw.splitlines() if p.strip()]
            if parts: data["summary"] = parts[0]
            if len(parts) > 1: data["advice"] = parts[1]
            if len(parts) > 2: data["next"] = parts[2]

        return jsonify({"reply": _sanitize(data)})

    except Exception as e:
        logging.exception("Reflect error")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
