import os, json, logging, re
from flask import Flask, render_template, request, jsonify, Response
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

HEAD_NUM = re.compile(r"^\s*(?:\(?\s*[\d０-９]+\s*\)?[\.．\)]\s*)", re.MULTILINE)
LABELS   = re.compile(r"^(要約|助言|次の一言|カテゴリ)\s*[:：]\s*", re.MULTILINE)
EMOJIS   = re.compile(r"[💡⭐️✨🔥✅▶️➤→•●◆■◉※★☆◎○●▲△■□◆◇]")

def _clean_line(s: str) -> str:
    if not s: return ""
    s = HEAD_NUM.sub("", s)
    s = LABELS.sub("", s)
    s = EMOJIS.sub("", s)
    return s.strip()

def _sanitize(d):
    return {
        "summary": _clean_line(d.get("summary", "")),
        "advice":  _clean_line(d.get("advice", "")),
        "next":    _clean_line(d.get("next", "")),
    }

@app.route("/")
def index():
    return render_template("index.html")

# ---- Reflect：ユーザー視点でパラフレーズ＋行動提案 ----
@app.route("/reflect", methods=["POST"])
def reflect():
    user_input = (request.json or {}).get("user_input", "").strip()
    if not user_input:
        return jsonify({"error": "入力が空です"}), 400

    sys = (
        "あなたは『要約パラフレーズ職人』です。"
        "必ず JSON 一行で出力。キーは summary, advice, next。"
        "【厳守】\n"
        "• ユーザーの発話“だけ”を材料にする（あなたの感想・推測・評価を入れない）\n"
        "• summary は『ユーザーの一人称（私）』で簡潔に言い換える\n"
        "• advice は次に取り得る具体的行動を2文以内で提案（断定や命令を避け、選択肢を示す）\n"
        "• next は次に入力するとよい一言のヒント（例：『明日やってみたい小さなことは？』）\n"
        "• 番号やラベルや絵文字は使わない\n"
    )

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": user_input}
        ],
        temperature=0.6,
    )
    raw = (r.choices[0].message.content or "").strip()
    data = {"summary": "", "advice": "", "next": ""}
    try:
        data.update(json.loads(raw))
    except Exception:
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if lines: data["summary"] = lines[0]
        if len(lines)>1: data["advice"] = lines[1]
        if len(lines)>2: data["next"] = lines[2]

    return jsonify({"reply": _sanitize(data)})

# ---- Summarize：当日まとめ（ユーザー一人称）＋明日の助言 ----
@app.route("/summarize", methods=["POST"])
def summarize():
    items = (request.json or {}).get("items", [])
    if not items:
        return jsonify({"error": "データがありません"}), 400

    text = "\n".join(f"- {i}" for i in items)
    sys = (
        "あなたは『日記編集者』です。"
        "入力されたメモだけを材料に、本日の出来事と気持ちをユーザーの一人称（私）で1段落に簡潔要約し、"
        "続けて明日のための具体的アドバイスを2文で添えてください。"
        "あなたの主観・評価・推測は入れないでください。番号や絵文字も不要。"
        "必ず JSON 一行で {\"summary\":..., \"advice\":...} を返すこと。"
    )

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": text}
        ],
        temperature=0.5,
    )
    raw = (r.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        return jsonify({
            "summary": _clean_line(data.get("summary","")),
            "advice":  _clean_line(data.get("advice",""))
        })
    except Exception:
        return jsonify({
            "summary": _clean_line(raw),
            "advice":  "深呼吸して小さく始める。無理のない一歩を選ぶ。"
        })

# ---- 軽い感情分析（グラフ用） ----
@app.route("/analyze", methods=["POST"])
def analyze():
    items = (request.json or {}).get("items", [])
    if not items:
        return jsonify({"error": "データがありません"}), 400
    text = "\n".join(f"- {i}" for i in items)
    sys = (
        "感情分析。JSON一行のみ返す。"
        "{\"mood_score\":0-100, \"tags\":[日本語ラベル3つ]}\n"
        "入力にない感情を勝手に作らない。絵文字・番号は使わない。"
    )
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":sys},{"role":"user","content":text}],
        temperature=0.2,
    )
    raw = (r.choices[0].message.content or "").strip()
    try:
        data = json.loads(raw)
        score = max(0, min(100, int(data.get("mood_score", 50))))
        tags  = [ _clean_line(str(t)) for t in data.get("tags", []) ][:3]
        return jsonify({"mood_score": score, "tags": tags})
    except Exception:
        return jsonify({"mood_score": 50, "tags": ["未分類", "保留", "様子見"]})

# ---- TTS（OpenAI） ----
@app.route("/tts", methods=["POST"])
def tts():
    body = request.json or {}
    text = (body.get("text") or "").strip()
    voice = (body.get("voice") or "alloy").strip()
    if not text:
        return jsonify({"error": "textが空です"}), 400

    try:
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=text,
            format="mp3",
        ) as resp:
            audio_bytes = resp.read()
        return Response(audio_bytes, headers={
            "Content-Type": "audio/mpeg",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        })
    except Exception as e:
        logging.exception("TTS error")
        return jsonify({"error": f"TTS生成に失敗：{e}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
