import os, json, logging, re
from io import BytesIO
from flask import Flask, render_template, request, jsonify, Response
from openai import OpenAI

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- OpenAI ---
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# --- 表示/読み上げクリーンアップ ---
HEAD_NUM = re.compile(r"^\s*(?:\(?\s*[\d０-９]+\s*\)?[\.．\)]\s*)", re.MULTILINE)
LABELS   = re.compile(r"^(要約|助言|次の一言|カテゴリ)\s*[:：]\s*", re.MULTILINE)
EMOJIS   = re.compile(r"[💡⭐️✨🔥✅▶️➤→•●◆■◉※★☆◎○●▲△■□◆◇]")

def _clean_line(s: str) -> str:
    if not s: 
        return ""
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

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/reflect", methods=["POST"])
def reflect():
    user_input = (request.json or {}).get("user_input", "").strip()
    if not user_input:
        return jsonify({"error": "入力が空です"}), 400

    sys = (
        "あなたは温かいトーンの日本語コーチ。返答は必ずJSON一行で、"
        "キーは summary, advice, next。絵文字や番号・ラベルは不要。"
        "思いやりを込め、声に出して自然に聞こえるよう短く答えて。"
    )
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": f"入力文：{user_input}。3つの短い返答で。"}
        ],
        temperature=0.9,
    )
    raw = r.choices[0].message.content.strip()
    data = {"summary": "", "advice": "", "next": ""}
    try:
        data.update(json.loads(raw))
    except Exception:
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if lines: data["summary"] = lines[0]
        if len(lines)>1: data["advice"] = lines[1]
        if len(lines)>2: data["next"] = lines[2]
    return jsonify({"reply": _sanitize(data)})

@app.route("/summarize", methods=["POST"])
def summarize():
    """1日のReflect群を、話し言葉の1段落に要約"""
    items = (request.json or {}).get("items", [])
    if not items:
        return jsonify({"error": "データがありません"}), 400
    text = "\n".join(f"- {i}" for i in items)
    sys = (
        "あなたは共感的な日記ライター。以下のメモを、"
        "その日の流れとして温かく自然な1段落に要約してください。"
        "番号やラベル・絵文字は使わない。"
    )
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": text}
        ],
        temperature=0.8,
    )
    summary = r.choices[0].message.content.strip()
    return jsonify({"summary": _clean_line(summary)})

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    1日のReflect群から、気分スコア(0-100)と感情タグ(3つ程度)を推定。
    ※可視化用の軽い分析。番号/絵文字なしのJSON一行で返す指示。
    """
    items = (request.json or {}).get("items", [])
    if not items:
        return jsonify({"error": "データがありません"}), 400
    text = "\n".join(f"- {i}" for i in items)
    sys = (
        "あなたは感情分析アシスタント。入力の短文群から、"
        "1) mood_score: 0〜100（高いほど前向き）"
        "2) tags: 日本語の感情・状態ラベルを3つ（例: 前向き, 不安, 疲れ）"
        "のみを含むJSON一行で返してください。"
        "番号や絵文字は不要。"
    )
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": sys},
            {"role": "user", "content": text}
        ],
        temperature=0.3,
    )
    raw = r.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
        score = int(data.get("mood_score", 50))
        tags = data.get("tags", [])
        # サニタイズ
        score = max(0, min(100, score))
        tags  = [ _clean_line(str(t)) for t in tags ][:3]
        return jsonify({"mood_score": score, "tags": tags})
    except Exception:
        # フォールバック
        return jsonify({"mood_score": 50, "tags": ["未分類", "保留", "様子見"]})

@app.route("/tts", methods=["POST"])
def tts():
    """
    OpenAI TTS（gpt-4o-mini-tts）で若い男性寄りのイケボを生成して返す。
    フロントはaudio要素で再生。
    """
    body = request.json or {}
    text = (body.get("text") or "").strip()
    voice = (body.get("voice") or "alloy").strip()  # "alloy" は自然系。日本語OK。
    if not text:
        return jsonify({"error": "textが空です"}), 400

    # 生成
    speech = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,            # "alloy" / "verse" / "haru" など環境に合わせて
        input=text,
        format="mp3"
    )
    audio_bytes = speech.content  # SDK v1系は .content にバイナリ
    return Response(audio_bytes, mimetype="audio/mpeg")

if __name__ == "__main__":
    # RenderのPORT環境変数があればそれを使う
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
