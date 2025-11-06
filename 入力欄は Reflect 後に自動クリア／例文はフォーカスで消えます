import os, json, logging, re
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def index():
    return render_template("index_v40.html")

# -------------------------------------------------
# 文字整形（数字・ラベル・記号の除去）
# -------------------------------------------------
def _strip_head_number(s: str) -> str:
    return re.sub(r"^\s*(?:\(?\s*[\d０-９]+\s*\)?[\.．\)]\s*)", "", s, flags=re.MULTILINE)

def _clean_for_readable(s: str) -> str:
    if not s:
        return ""
    s = _strip_head_number(s)
    s = re.sub(r"^(要約|助言|次の一言|カテゴリ)\s*[:：]\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"^\s*[・\-＊*•●◆■◉▶▷➤→]\s*", "", s, flags=re.MULTILINE)
    s = re.sub(r"[💡⭐️✨🔥✅▶️➤→•●◆■◉※★☆◎○●▲△■□◆◇▶▷➤➔➜]", "", s)
    return s.strip()

def _sanitize_sections(dct):
    return {
        "summary": _clean_for_readable(dct.get("summary", "")),
        "advice":  _clean_for_readable(dct.get("advice", "")),
        "next":    _clean_for_readable(dct.get("next", "")),
    }

# -------------------------------------------------
# 反映エンドポイント
# -------------------------------------------------
@app.route("/reflect", methods=["POST"])
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "入力が空です"}), 400

        system_prompt = (
            "あなたは優しい日本語コーチです。出力は必ずJSON一行。"
            "キーは summary, advice, next の3つ。"
            "数字やラベル（要約/助言/次の一言/カテゴリ）や絵文字は付けない。"
            "短く自然な会話文で。声に出しても滑らかになるように書いてください。"
        )

        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
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

        clean = _sanitize_sections(data)
        return jsonify({"reply": clean})

    except Exception as e:
        logging.exception("Reflect error")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
