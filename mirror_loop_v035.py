import os, re, json, logging
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

@app.get("/health")
def health():
    return "ok", 200

@app.route("/")
def index():
    return render_template("index_v36.html")

def _extract_json(text: str) -> dict:
    if not text:
        return {}
    fence = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.I)
    cand = fence.group(1) if fence else re.search(r"\{[\s\S]*\}", text)
    cand = cand.group(0) if cand else "{}"
    try:
        return json.loads(cand)
    except Exception:
        cand2 = re.sub(r",\s*([\}\]])", r"\1", cand)
        try:
            return json.loads(cand2)
        except Exception:
            return {}

@app.post("/reflect")
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "empty"}), 400

        system_prompt = (
            "あなたは共感的なメンタルコーチです。"
            "ユーザーの文章から気持ち・背景・学びを丁寧に読み取り、"
            "1行要約・2つの助言・感情カテゴリ・0〜100の心の安定スコア・"
            "次の一歩を促す短い質問を日本語でJSON形式で返してください。\n"
            '出力フォーマット: {"summary":"...", "advice":["...","..."], '
            '"category":"...", "score":数値, "followup":"..."}'
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.65,
        )

        text = resp.choices[0].message.content or ""
        data = _extract_json(text)

        data["advice"] = [f"💡 {a}" for a in data.get("advice", [])]
        return jsonify({
            "summary": data.get("summary", ""),
            "advice": data.get("advice", []),
            "category": data.get("category", ""),
            "score": data.get("score", 50),
            "followup": f"🪞 {data.get('followup', 'もう少し詳しく教えてください')}"
        })

    except Exception as e:
        logging.exception("reflect error")
        return jsonify({"error": str(e)}), 500

@app.post("/weekly_report")
def weekly_report():
    return jsonify({"report": "週報は次リリースでDB連携予定です。"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
