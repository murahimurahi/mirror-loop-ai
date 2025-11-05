import os, json, sqlite3, datetime as dt
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

# ---------------------------------------------------------------------
# 基本設定
# ---------------------------------------------------------------------
app = Flask(__name__)
client = OpenAI()
MODEL = os.getenv("MODEL", "gpt-4o-mini")  # 速くて安定

DB_PATH = "mirrorloop.db"

# ---------------------------------------------------------------------
# DB 初期化
# ---------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS reflections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            text TEXT,
            summary TEXT,
            advice TEXT,
            category TEXT,
            score REAL,
            followup TEXT
        )"""
    )
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------------------
# AI呼び出し設定
# ---------------------------------------------------------------------
SYSTEM = (
    "You are Mirror Loop, a concise Japanese reflection coach. "
    "Output MUST follow the JSON schema exactly. "
    "Be brief, actionable, and empathetic."
)

JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "一文での要約"},
        "advice": {
            "type": "array",
            "items": {"type": "string"},
            "description": "具体的行動（最大3）"
        },
        "category": {
            "type": "string",
            "enum": [
                "work", "study", "health", "family",
                "relationship", "finance", "other"
            ]
        },
        "score": {"type": "number", "minimum": 0, "maximum": 100},
        "followup": {"type": "string", "description": "次に答えやすい質問"}
    },
    "required": ["summary", "advice", "category", "score", "followup"],
    "additionalProperties": False
}


def call_ai(reflect_text: str) -> dict:
    """OpenAI Responses API を利用して構造化出力を生成"""
    prompt = f"""ユーザーの日誌:
{reflect_text}

出力は必ずJSON。以下の定義に従ってください。
- summary: 本質を外さない一文要約（25〜60字）
- advice: 実行可能な助言を3つ以内。動詞で始める。
- category: work, study, health, family, relationship, finance, other のいずれか。
- score: 感情スコア(0-100)。70=穏やか。
- followup: 次に書きやすい一問。
"""

    resp = client.responses.create(
        model=MODEL,
        system=SYSTEM,
        input=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "mirror_loop", "schema": JSON_SCHEMA},
        },
    )

    try:
        data = json.loads(resp.output_parsed)
    except Exception:
        # モデルがスキーマを守らなかった場合のフォールバック
        data = {
            "summary": "解析できませんでした",
            "advice": ["もう少し具体的に書いてみましょう"],
            "category": "other",
            "score": 50,
            "followup": "今日は何を感じましたか？"
        }
    return data


# ---------------------------------------------------------------------
# ルートページ
# ---------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index_v36.html")


# ---------------------------------------------------------------------
# Reflect エンドポイント
# ---------------------------------------------------------------------
@app.post("/reflect")
def reflect():
    user_input = (request.json or {}).get("user_input", "").strip()
    if not user_input:
        return jsonify({"error": "empty"}), 400

    data = call_ai(user_input)

    # DBに保存
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reflections (date, text, summary, advice, category, score, followup) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            dt.date.today().isoformat(),
            user_input,
            data.get("summary"),
            "\n".join(data.get("advice", [])),
            data.get("category"),
            data.get("score"),
            data.get("followup"),
        ),
    )
    conn.commit()
    conn.close()

    return jsonify(data)


# ---------------------------------------------------------------------
# 週報生成
# ---------------------------------------------------------------------
@app.post("/weekly_report")
def weekly_report():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    week_ago = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    cur.execute(
        "SELECT date, summary, score FROM reflections WHERE date >= ? ORDER BY date",
        (week_ago,),
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return jsonify({"report": "過去7日分の記録がありません。"})

    avg_score = sum([r[2] or 0 for r in rows]) / len(rows)
    summaries = "\n".join([f"{r[0]}：{r[1]}" for r in rows])
    prompt = f"""
以下はあなたの過去7日間の要約です：
{summaries}

平均スコア：{avg_score:.1f}

上記をもとに「この一週間の総評」「改善の方向性」「次週の目標提案」を簡潔に書いてください。
"""
    resp = client.responses.create(
        model=MODEL,
        system=SYSTEM,
        input=[{"role": "user", "content": prompt}],
    )

    text = ""
    try:
        text = resp.output[0].content[0].text
    except Exception:
        text = "週報を生成できませんでした。"

    return jsonify({"report": text})


# ---------------------------------------------------------------------
# 実行
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
