import os, json, logging
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

# ------------------------------------------------------------
# 基本設定
# ------------------------------------------------------------
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# OpenAIクライアント初期化
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))


# ------------------------------------------------------------
# ルート（トップページ）
# ------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index_v36.html")


# ------------------------------------------------------------
# /reflect（AI要約・助言・スコア生成）
# ------------------------------------------------------------
@app.post("/reflect")
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "empty"}), 400

        # ---- プロンプト内容 ----
        system_prompt = (
            "あなたは簡潔で温かいライフコーチです。"
            "ユーザーの文章を要約し、感情スコアと短い助言を出してください。"
            "必ず次の形式のJSONで返答してください："
            '{"summary": "要約", "advice": ["助言1","助言2"], '
            '"category": "感情カテゴリ", "score": 数値0-100, "followup": "次の質問"}'
        )

        # ---- OpenAI呼び出し（v1仕様）----
        resp = client.responses.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.5,
        )

        content = resp.output_text  # JSON文字列として取得
        data = json.loads(content)

        return jsonify({
            "summary": data.get("summary", ""),
            "advice": data.get("advice", []),
            "category": data.get("category", ""),
            "score": data.get("score", 50),
            "followup": data.get("followup", "")
        })

    except Exception as e:
        logging.exception("Reflect処理エラー")
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------
# /weekly_report（ダミー）
# ------------------------------------------------------------
@app.post("/weekly_report")
def weekly_report():
    return jsonify({
        "report": "週報生成は準備中です。次のアップデートでDB連携します。"
    })


# ------------------------------------------------------------
# メイン実行
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
