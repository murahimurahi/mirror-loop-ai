import os, json, logging, re
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

@app.route("/")
def index():
    # 必ず v39 を返す
    return render_template("index_v39.html")

# ——— 表示＆読み上げの安全クリーニング ———
def _strip_head_number(s: str) -> str:
    # 1. / １． / 1) / (1) など行頭の番号表現を除去
    return re.sub(r"^\s*(?:\(?\s*[\d０-９]+\s*\)?[\.．\)]\s*)", "", s, flags=re.MULTILINE)

def _clean_for_readable(s: str) -> str:
    if not s:
        return ""
    s = _strip_head_number(s)
    # ラベル語を除去
    s = re.sub(r"^(要約|助言|次の一言|カテゴリ)\s*[:：]\s*", "", s, flags=re.MULTILINE)
    # 箇条記号を除去
    s = re.sub(r"^\s*[・\-＊*•●◆■◉▶▷➤→]\s*", "", s, flags=re.MULTILINE)
    # 装飾系絵文字/記号を除去
    s = re.sub(r"[💡⭐️✨🔥✅▶️➤→•●◆■◉※★☆◎○●▲△■□◆◇▶▷➤➔➜]", "", s)
    return s.strip()

def _sanitize_sections(dct):
    return {
        "summary": _clean_for_readable(dct.get("summary", "")),
        "advice":  _clean_for_readable(dct.get("advice", "")),
        "next":    _clean_for_readable(dct.get("next", "")),
    }

@app.route("/reflect", methods=["POST"])
def reflect():
    try:
        user_input = (request.json or {}).get("user_input", "").strip()
        if not user_input:
            return jsonify({"error": "入力が空です"}), 400

        system = (
            "あなたは共感的な日本語コーチ。出力は必ず JSON 一行のみ。"
            "キーは summary, advice, next の3つ。"
            "各値は自然な会話文。箇条番号や『要約/助言/次の一言/カテゴリ』等のラベル、絵文字は入れない。"
            "短く端的に、相手の背中を押す一言も忘れずに。"
        )
        prompt = f"入力文：{user_input}\n3つの短い会話文で。"

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":system},
                      {"role":"user","content":prompt}],
            temperature=0.8,
        )
        raw = (res.choices[0].message.content or "").strip()

        data = {"summary":"", "advice":"", "next":""}
        try:
            data.update(json.loads(raw))
        except Exception:
            # JSONでなければ3行に割り当て
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
