import os, random, logging, sqlite3, datetime, statistics, json
from flask import Flask, request, jsonify, render_template, g
import openai

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

openai.api_key = os.environ.get("OPENAI_API_KEY")
DB_PATH = "mirrorloop.db"

# ---------- DB ----------
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS emotions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            emotion TEXT,
            score INTEGER,
            category TEXT,
            date TEXT
        )
    """)
    conn.commit()
    conn.close()
init_db()

# ---------- AI ----------
def analyze_emotion(user_input):
    prompt = f"""
    あなたはMirror Loopです。
    ユーザーの文章を読み取り、感情カテゴリ・スコア(0-100)・短いアドバイスを生成してください。
    JSON形式：
    {{
      "emotion": "感情名",
      "score": 数値,
      "advice": "アドバイス",
      "category": "healing | learning | action | creative"
    }}
    ユーザー入力:「{user_input}」
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message["content"]
    except Exception as e:
        logging.error(e)
        return '{"error":"AI応答失敗"}'

def weekly_comment_ai(summary):
    prompt = f"""
    以下の1週間の感情データ要約に基づき、
    1) 100文字以内の「今週のひとこと」
    2) 箇条書きで3つの「来週のおすすめ行動」
    を日本語で短く出力してください。

    データ:
    {json.dumps(summary, ensure_ascii=False)}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        logging.error(e)
        return "今週のひとこと：データ解析に失敗しました。\n・深呼吸をしてリセット\n・短時間の散歩\n・睡眠時間の確保"

# ---------- 保存/取得 ----------
def save_emotion(user_id, emotion, score, category):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO emotions (user_id, emotion, score, category, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, emotion, score, category, datetime.date.today().isoformat())
    )
    conn.commit()

def get_recent_emotions(user_id, days=7):
    conn = get_db()
    c = conn.cursor()
    since = (datetime.date.today() - datetime.timedelta(days=days-1)).isoformat()
    c.execute(
        "SELECT date, score, emotion, category FROM emotions WHERE user_id=? AND date>=? ORDER BY date ASC",
        (user_id, since)
    )
    return c.fetchall()

# ---------- 広告 ----------
ADS = {
    "healing": "https://www.amazon.co.jp/s?k=%E7%99%92%E3%81%97",
    "learning": "https://www.amazon.co.jp/s?k=%E8%B3%87%E6%A0%BC",
    "action": "https://www.amazon.co.jp/s?k=%E3%82%AC%E3%82%B8%E3%82%A7%E3%83%83%E3%83%88",
    "creative": "https://www.amazon.co.jp/s?k=AI+%E3%82%A2%E3%83%BC%E3%83%88"
}
DEFAULT_AD = ADS["healing"]

def pick_ad_by_category(cat):
    return ADS.get(cat, DEFAULT_AD)

# ---------- ルーティング ----------
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
    except:
        result = {"emotion":"不明","score":50,"advice":"深呼吸でリセットしましょう","category":"healing"}

    save_emotion(user_id, result["emotion"], int(result["score"]), result["category"])
    return jsonify(result)

@app.route("/history/<user_id>")
def history(user_id):
    rows = get_recent_emotions(user_id, days=7)
    return jsonify(rows)

@app.route("/weekly_report/<user_id>")
def weekly_report(user_id):
    rows = get_recent_emotions(user_id, days=7)
    if not rows:
        return jsonify({"error":"データがありません"}), 404

    days = [r[0] for r in rows]
    scores = [int(r[1]) for r in rows]
    emotions = [r[2] for r in rows]
    cats = [r[3] for r in rows]

    avg = round(statistics.mean(scores), 1)
    mx = max(scores); mn = min(scores)
    delta = scores[-1] - scores[0]
    trend = "上向き" if delta>=5 else ("下向き" if delta<=-5 else "横ばい")

    from collections import Counter
    top_category = Counter(cats).most_common(1)[0][0]

    summary = {
        "days": days,
        "scores": scores,
        "emotions": emotions,
        "avg": avg,
        "max": mx,
        "min": mn,
        "trend": trend,
        "top_category": top_category
    }

    comment = weekly_comment_ai(summary)
    ad_url = pick_ad_by_category(top_category)

    return jsonify({
        "summary": summary,
        "comment": comment,
        "ad_url": ad_url
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
