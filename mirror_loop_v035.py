import os, re, json, logging
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", "")).with_options(timeout=15.0)

def _extract_json(text: str) -> dict:
    if not text:
        return {}
    m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.I)
    body = m.group(1) if m else (re.search(r"\{[\s\S]*\}", text).group(0) if re.search(r"\{[\s\S]*\}", text) else "{}")
    try:
        return json.loads(body)
    except Exception:
        body = re.sub(r",\s*([\}\]])", r"\1", body)
        try:
            return json.loads(body)
        except Exception:
            return {}

@app.get("/")
def index():
    return render_template("index_v36.html")

@app.get("/health")
def health():
    return "ok", 200

@app.post("/reflect")
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error":"empty"}), 400

        system = (
            "あなたは共感的なメンタルコーチ。日本語で次のJSONだけを返す。"
            '形式: {"summary":"1行要約","advice":["助言1","助言2"],'
            '"category":"感情カテゴリ","score":数値(0-100),"followup":"次の一言(20字以内)"}'
            " 出力以外の文は一切書かない。"
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.6,
            max_tokens=220,
            messages=[{"role":"system","content":system},{"role":"user","content":user_input}]
        )
        txt = (resp.choices[0].message.content or "").strip()
        data = _extract_json(txt)

        summary  = data.get("summary") or "今日の気づきを簡潔に言語化できました。"
        advice   = [f"💡 {a}" for a in (data.get("advice") or ["小さく始める行動を1つ決めよう","明日の自分へ一言メモを書こう"])][:2]
        category = data.get("category") or "reflection"
        score    = max(0, min(100, int(data.get("score") or 55)))
        followup = data.get("followup") or "もう1つだけ具体例を教えてください"

        return jsonify({"summary":summary,"advice":advice,"category":category,"score":score,"followup":followup})
    except Exception as e:
        logging.exception("reflect error")
        return jsonify({"error":str(e)}), 500

@app.post("/weekly_report")
def weekly_report():
    return jsonify({"report":"（次回）過去7日の入力から要約と推移を自動生成します。"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
