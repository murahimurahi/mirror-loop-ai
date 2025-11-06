import os, logging
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def index():
    return render_template("index_v38.html")

@app.route("/reflect", methods=["POST"])
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "入力が空です"}), 400

        prompt = f"""
あなたは共感的で温かく話す日本語コーチです。
以下の入力文を基に、人間味のある自然な文体で、
短く3ステップ（要約・助言・次の一言）にまとめてください。

入力文：
{user_input}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは優しく、会話のように話す日本語AIです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.85,
        )

        result = response.choices[0].message.content.strip()
        return jsonify({"reply": result})

    except Exception as e:
        logging.exception("Reflect error")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
