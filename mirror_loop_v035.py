import os, logging, sqlite3, datetime, json, statistics
from flask import Flask, request, jsonify, render_template, g
from openai import OpenAI

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
DB_PATH = "mirrorloop.db"


# ---------------------------------------------------------------------
# DB接続
# ---------------------------------------------------------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                date TEXT,
                emotion TEXT,
                score INTEGER,
                category TEXT
            )
        """)
        db.commit()


def save_emotion(user_id, emotion, score, category):
    db = get_db()
    db.execute(
        "INSERT INTO reflections (user_id, date, emotion, score, category) VALUES (?, ?, ?, ?, ?)",
        (user_id, datetime.date.today().isoformat(), emotion, score, category),
    )
    db.commit()


def fetch_weekly(user_id):
    db = get_db()
    cur = db.execute(
        "SELECT date, emotion, score FROM reflections WHERE user_id=? ORDER BY date DESC LIMIT 7",
        (user_id,),
    )
    return cur.fetchall()


# ---------------------------------------------------------------------
# OpenAI分析関数
# ---------------------------------------------------------------------
def analyze_emotion(user_input):
    prompt = f"""
    あなたは「Mirror Loop」という短文リフレクションAIです。
    ユーザー入力を読み取り、以下のJSONのみを出力してください（説明文や余計な文字は禁止）。

    {{
      "emotion": "（感情1〜2語）",
      "score": 数値0〜100,
      "advice": "70文字以内の一言アドバイス",
      "category": "healing" または "learning" または "action" または "creative",
      "followup": "次に聞く短い質問（20文字以内）"
    }}

    ユーザー入力: 「{user_input}」
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return resp.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI error: {e}")
        return json.dumps({
            "emotion": "不明",
            "score": 50,
            "advice": "深呼吸でリセットしましょう。",
            "category": "healing",
            "followup": "今日は何が印象的でしたか？"
        }, ensure_ascii=False)


def weekly_comment_ai(summary):
    prompt = f"""
    以下の1週間の感情データをまとめ、簡潔にまとめてください。
    1) 100文字以内の「今週のまとめ」
    2) 箇条書き3つの「来週への提案」
    日本語で出力。

    データ:
    {json.dumps(summary, ensure_ascii=False)}
    """

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Weekly comment error: {e}")
        return "今週のまとめ：データ解析に失敗しました。\n・短い深呼吸\n・10分散歩\n・早寝"


# ---------------------------------------------------------------------
# ルート
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index_v35.html")


@app.route("/reflect", methods=["POST"])
def reflect():
    data = request.get_json(force=True)
    user_input = data.get("message", "")
    user_id = data.get("user_id", "guest")

    ai_json = analyze_emotion(user_input)
    try:
        result = json.loads(ai_json)
    except Exception as e:
        logging.warning("JSON parse fallback: %s", e)
        result = {}

    result = {
        "emotion": result.get("emotion", "不明"),
        "score": int(result.get("score", 50) or 50),
        "advice": result.get("advice", "深呼吸でリセットしましょう。"),
        "category": result.get("category", "healing"),
        "followup": result.get("followup", "今日は何が印象的でしたか？"),
    }

    try:
        save_emotion(user_id, result["emotion"], int(result["score"]), result["category"])
    except Exception as e:
        logging.error("DB save failed: %s", e)

    return jsonify(result)


@app.route("/weekly_report", methods=["GET"])
def weekly_report():
    user_id = request.args.get("user_id", "guest")
    rows = fetch_weekly(user_id)
    if not rows:
        return jsonify({"summary": "まだデータがありません。"})

    scores = [r[2] for r in rows]
    summary = {
        "平均スコア": round(statistics.mean(scores), 1),
        "最高スコア": max(scores),
        "最低スコア": min(scores),
        "件数": len(rows),
    }

    comment = weekly_comment_ai(summary)
    return jsonify({"summary": summary, "comment": comment})


# ---------------------------------------------------------------------
# 起動
# ---------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
