import os, logging
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def index():
    return render_template("index_v37.html")

@app.route("/reflect", methods=["POST"])
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "入力が空です"}), 400

        prompt = f"""
        あなたは親しみやすく、簡潔にアドバイスをする日本語AIです。
        入力内容を以下の3段階でまとめてください。

        1. 要約：内容を一文で。
        2. 助言：ポジティブな短い提案を。
        3. 次の一言：話しかけるように締めくくる。

        入力文：
        {user_input}
        """

        response = OpenAI(api_key=os.environ.get("OPENAI_API_KEY")).chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "あなたは共感的で明るい日本語コーチです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
        )

        result = response.choices[0].message.content.strip()
        return jsonify({"reply": result})
    except Exception as e:
        logging.exception("Reflect error")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
