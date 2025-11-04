import os, logging, sqlite3, datetime, statistics, json
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
    あなたは「Mirror Loop」という短文リフレクションAIです。
    ユーザー入力を読み取り、以下のJSONのみを出力してください（説明文や余計な文字は出さない）。

    要件:
    - "emotion": 直感的な感情名（日本語, 1〜2語）
    - "score": 0〜100の整数（70=良い, 50=普通, 30=低い）
    - "advice": 70文字以内の前向きな一言。絵文字1つ程度OK
    - "category": "healing" | "learning" | "action" | "creative" のいずれか
    - "followup": 次に聞く短い質問（20文字以内, 敬語, 絵文字なし）

    形式のみ:
    {{"emotion":"", "score": 0, "advice":"", "category":"", "followup":""}}

    ユーザー: 「{user_input}」
    """.strip()

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        return response.choices[0].message["content"]
    except Exception as e:
        logging.error(e)
        # フォールバック
        return json.dumps({
            "emotion":"不明","score":50,
            "advice":"深呼吸でリセットしましょう。",
            "category":"healing",
            "followup":"今日は何が印象的でしたか？"
        }, ensure_ascii=False)

def weekly_comment_ai(summary):
    prompt = f"""
    以下の1週間の感情データ要約に基づき、
    1) 100文字以内の「今週のひとこと」
    2) 箇条書き3つの「来週のおすすめ行動」
    を日本語で短く出力してください。

    データ:
    {json.dumps(summary, ensure_ascii=False)}
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        logging.error(e)
        return "今週のひとこと：データ解析に失敗しました。\n・短い深呼吸\n・10分散歩\n・早寝"

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
    except Exception as e:
        logging.warning("JSON parse fallback: %s", e)
        result = {
            "emotion":"不明","score":50,
            "advice":"深呼吸でリセットしましょう。",
            "category":"healing",
            "followup":"今日は何が印象的でしたか？"
        }

    # 保存（会話はクライアント側で管理。蓄積はスコア統計のみ）
    try:
        save_emotion(user_id, result["emotion"], int(result["score"]), result["category"])
    except Exception as e:
        logging.error("DB save failed: %s", e)

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

# ---------- 広告（カテゴリ別リンク） ----------
ADS = {
    "healing": "https://www.amazon.co.jp/s?k=%E7%99%92%E3%81%97",
    "learning": "https://www.amazon.co.jp/s?k=%E8%B3%87%E6%A0%BC",
    "action": "https://www.amazon.co.jp/s?k=%E3%82%AC%E3%82%B8%E3%82%A7%E3%83%83%E3%83%88",
    "creative": "https://www.amazon.co.jp/s?k=AI+%E3%82%A2%E3%83%BC%E3%83%88"
}
DEFAULT_AD = ADS["healing"]

def pick_ad_by_category(cat):
    return ADS.get(cat, DEFAULT_AD)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
