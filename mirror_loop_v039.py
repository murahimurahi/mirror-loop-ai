import os, json, logging
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def index():
    return render_template("index_v39.html")

@app.route("/reflect", methods=["POST"])
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "入力が空です"}), 400

        # 数字ラベル禁止 & JSON で返すよう強制
        sys = (
            "あなたは共感的な日本語コーチです。"
            "出力は必ず JSON 1 行のみ。キーは summary, advice, next の3つ。"
            "いかなるラベル（要約・助言・次の一言等）や番号（1. 2. 3.）は付けない。"
            "全体の語調は落ち着いた自然な会話文で。"
        )
        usr = f"入力文：{user_input}\n短く過不足なく。句読点は日本語。絵文字や記号は不要。"

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": usr},
            ],
            temperature=0.8,
        )

        raw = resp.choices[0].message.content.strip()

        # JSON で来なかったらフェイルセーフ
        data = {"summary": "", "advice": "", "next": ""}
        try:
            data.update(json.loads(raw))
        except Exception:
            # 行分割してそれっぽく埋める
            text = raw.replace("要約", "").replace("助言", "").replace("次の一言", "")
            parts = [p.strip(" ・-") for p in text.splitlines() if p.strip()]
            if parts:
                data["summary"] = parts[0]
            if len(parts) > 1:
                data["advice"] = parts[1]
            if len(parts) > 2:
                data["next"] = parts[2]

        # 余計な先頭番号や記号をサニタイズ（保険）
        def strip_head(s: str) -> str:
            import re
            s = re.sub(r"^\s*[\d０-９]+[)\.．]\s*", "", s)  # 1. / １． / 1) など
            s = re.sub(r"^\s*[・\-＊*]\s*", "", s)        # 箇条書き記号
            return s.strip()

        clean = {k: strip_head(v) for k, v in data.items()}

        return jsonify({"reply": clean})

    except Exception as e:
        logging.exception("Reflect error")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
