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
    # 呼吸グラデ版のテンプレート
    return render_template("index_v36.html")

def _extract_json(text: str) -> dict:
    """
    モデルの出力から最初のJSONブロックを安全に取り出す。
    JSONフェンス```json ...```にも対応。
    """
    if not text:
        return {}
    # ```json ... ``` を優先
    fence = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text, re.I)
    if fence:
        cand = fence.group(1)
    else:
        # 最初の { ... } をローンジーに抜く
        brace = re.search(r"\{[\s\S]*\}", text)
        cand = brace.group(0) if brace else "{}"
    try:
        return json.loads(cand)
    except Exception:
        # 軽い補正（末尾カンマ除去など）
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
            "あなたは簡潔で温かいライフコーチです。"
            "ユーザー文を要約し、感情スコア(0-100)と短い助言配列、感情カテゴリ、"
            "次に促す一言を必ずJSONで返して。"
            'フォーマット: {"summary":"要約","advice":["助言1","助言2"],'
            '"category":"感情カテゴリ","score":数値,"followup":"一言"}'
        )

        # ★ Chat Completions（v1）に切替：response_formatは使わない
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            temperature=0.5,
        )
        text = resp.choices[0].message.content or ""
        data = _extract_json(text)

        return jsonify({
            "summary":  data.get("summary", ""),
            "advice":   data.get("advice", []),
            "category": data.get("category", ""),
            "score":    data.get("score", 50),
            "followup": data.get("followup", "")
        })
    except Exception as e:
        logging.exception("reflect error")
        return jsonify({"error": str(e)}), 500

@app.post("/weekly_report")
def weekly_report():
    return jsonify({"report": "週報は次リリースでDB連携予定です。"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
