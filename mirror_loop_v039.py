import os, json, logging, re
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def index():
    return render_template("index_v39.html")

def strip_head_number(s: str) -> str:
    """行頭の番号付き箇条(1. / １． / (1) / 1) など) を除去。"""
    return re.sub(r"^\s*[\d０-９]+[\.\)．]\s*|\s*^\(\s*[\d０-９]+\s*\)\s*", "", s, flags=re.MULTILINE)

def sanitize_sections(d):
    """番号・ラベル・記号を除いて返す（読み上げ用/表示用共通の保険）。"""
    def clean(x: str) -> str:
        if not x: return ""
        x = strip_head_number(x)
        # ラベルワードを除去
        x = re.sub(r"^(要約|助言|次の一言|カテゴリ)\s*[:：]\s*", "", x, flags=re.MULTILINE)
        # 箇条書き記号
        x = re.sub(r"^\s*[・\-＊*•●◆■◉▶▷➤→]\s*", "", x, flags=re.MULTILINE)
        # 絵文字・装飾記号（代表的なもの）
        x = re.sub(r"[💡⭐️✨🔥✅▶️➤→•●◆■◉※★☆◎○●▲△■□◆◇▶▷➤➔➜]", "", x)
        # 余計な空白
        x = re.sub(r"\s+\n", "\n", x)
        return x.strip()
    return {k: clean(v) for k, v in d.items()}

@app.route("/reflect", methods=["POST"])
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "入力が空です"}), 400

        sys = (
            "あなたは共感的な日本語コーチ。出力は必ず JSON 一行のみ。"
            "キーは summary, advice, next の3つ。"
            "箇条番号やラベル（要約/助言/次の一言/カテゴリ）や絵文字は付けない。"
            "自然で会話的な短い文で。"
        )
        usr = f"入力文：{user_input}\n短く端的に。"

        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":sys},{"role":"user","content":usr}],
            temperature=0.8,
        )
        raw = r.choices[0].message.content.strip()

        data = {"summary":"", "advice":"", "next":""}
        try:
            data.update(json.loads(raw))
        except Exception:
            # 万一JSONでなければ3行に割当
            parts = [p.strip() for p in raw.splitlines() if p.strip()]
            if parts:   data["summary"] = parts[0]
            if len(parts)>1: data["advice"]  = parts[1]
            if len(parts)>2: data["next"]    = parts[2]

        clean = sanitize_sections(data)
        return jsonify({"reply": clean})

    except Exception as e:
        logging.exception("Reflect error")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
