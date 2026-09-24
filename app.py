import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, url_for

DATA_DIR = Path(os.environ.get("GYM_DATA_DIR", "./data"))
DATABASE = DATA_DIR / "gym.db"
ROUTINE_PATH = Path(os.environ.get("GYM_ROUTINE_FILE", "./routine.json"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-if-exposed-outside-your-home-network")

def load_routine():
    """Load the workout rotation from routine.json so it can be edited/regenerated
    (e.g. weekly, from a chat prompt fed your logged history) without touching code."""
    with open(ROUTINE_PATH) as handle:
        plans = json.load(handle)
    return [
        (plan["key"], plan["name"], [
            (ex["name"], ex["sets"], ex["reps"], ex["weight"]) for ex in plan["exercises"]
        ])
        for plan in plans
    ]

ROUTINE = load_routine()

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS workouts (
  id INTEGER PRIMARY KEY, routine_key TEXT NOT NULL, name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','complete')),
  completed_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exercises (
  id INTEGER PRIMARY KEY, workout_id INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
  position INTEGER NOT NULL, name TEXT NOT NULL, target_sets INTEGER, target_reps INTEGER, target_weight REAL
);
CREATE TABLE IF NOT EXISTS sets (
  id INTEGER PRIMARY KEY, exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
  position INTEGER NOT NULL, reps INTEGER NOT NULL, weight REAL NOT NULL
);
"""

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def format_completed(value):
    """Render a stored completed_at value for display. Real timestamps become a
    short date; the "Imported from chat" placeholder (no original date) passes through."""
    try:
        return datetime.fromisoformat(value).strftime("%-d %b %Y")
    except (TypeError, ValueError):
        return value

def with_display_date(rows):
    return [dict(row, completed_display=format_completed(row["completed_at"])) for row in rows]

def db():
    if "db" not in g:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "images").mkdir(exist_ok=True)
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error):
    connection = g.pop("db", None)
    if connection: connection.close()

def add_workout(connection, key, name, exercises, completed_at=None):
    status = "complete" if completed_at else "pending"
    cur = connection.execute("INSERT INTO workouts (routine_key,name,status,completed_at,created_at) VALUES (?,?,?,?,?)",
                             (key, name, status, completed_at, completed_at or now()))
    workout_id = cur.lastrowid
    for pos, item in enumerate(exercises, 1):
        exercise_name, target_sets, target_reps, target_weight, logged_sets = item
        ex_id = connection.execute("INSERT INTO exercises (workout_id,position,name,target_sets,target_reps,target_weight) VALUES (?,?,?,?,?,?)",
                                   (workout_id, pos, exercise_name, target_sets, target_reps, target_weight)).lastrowid
        for set_pos, (reps, weight) in enumerate(logged_sets, 1):
            connection.execute("INSERT INTO sets (exercise_id,position,reps,weight) VALUES (?,?,?,?)", (ex_id, set_pos, reps, weight))
    return workout_id

def migrate_and_seed():
    connection = db()
    connection.executescript(SCHEMA)
    exists = connection.execute("SELECT 1 FROM schema_migrations WHERE version=1").fetchone()
    if not exists:
        # Imported chat history has no original dates, so it is deliberately labelled as imported.
        add_workout(connection, "upper-push", "Upper Push (imported history)", [
            ("Dumbbell Bench Press",3,10,15,[(10,15)]*3), ("Incline Dumbbell Bench Press",3,10,15,[(10,15)]*3),
            ("Seated Dumbbell Shoulder Press",3,10,10,[(10,10)]*3), ("Cable Lateral Raise",3,10,7.5,[(10,7.5)]*3),
            ("Tricep Rope Pushdown",3,10,17.5,[(10,17.5)]*3), ("Overhead Rope Extension",2,10,15,[(10,15)]*2),
        ], "Imported from chat")
        add_workout(connection, "full-body", "Full Body Re-entry (imported history)", [
            ("Leg Press",3,10,40,[(10,40)]*3), ("Dumbbell Bench Press",3,10,15,[(10,15)]*3),
            ("Lat Pulldown",3,10,42.5,[(10,27.5),(10,35),(10,42.5)]), ("Romanian Barbell Deadlift",3,10,20,[(10,20)]*3),
            ("Cable Lateral Raise",2,12,7.5,[(12,7.5)]*2),
        ], "Imported from chat")
        key, name, exercises = ROUTINE[0]
        add_workout(connection, key, name, [(n,s,r,w,[]) for n,s,r,w in exercises])
        connection.execute("INSERT INTO schema_migrations (version,applied_at) VALUES (1,?)", (now(),))
    connection.commit()

@app.before_request
def bootstrap(): migrate_and_seed()

def workout_detail(workout_id):
    workout = db().execute("SELECT * FROM workouts WHERE id=?", (workout_id,)).fetchone()
    if not workout: abort(404)
    exercises = db().execute("SELECT * FROM exercises WHERE workout_id=? ORDER BY position", (workout_id,)).fetchall()
    return workout, [(ex, db().execute("SELECT * FROM sets WHERE exercise_id=? ORDER BY position", (ex["id"],)).fetchall()) for ex in exercises]

def short_exercises(exercises):
    # A quick session retains the main compound lifts and first accessory.
    return exercises[:min(3, len(exercises))]

@app.route("/")
def home():
    pending = db().execute("SELECT * FROM workouts WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
    recent = db().execute("SELECT * FROM workouts WHERE status='complete' ORDER BY id DESC LIMIT 5").fetchall()
    return render_template("home.html", pending=pending, recent=with_display_date(recent))

@app.route("/workout/<int:workout_id>")
def workout(workout_id):
    item, exercises = workout_detail(workout_id)
    mode = request.args.get("mode", "long")
    return render_template("workout.html", workout=item, exercises=short_exercises(exercises) if mode == "quick" else exercises, mode=mode)

@app.route("/workout/<int:workout_id>/complete", methods=["POST"])
def complete(workout_id):
    workout, exercises = workout_detail(workout_id)
    if workout["status"] == "complete": return redirect(url_for("history"))
    selected_ids = {int(value) for value in request.form.getlist("exercise-id")}
    selected = [(ex, sets) for ex, sets in exercises if ex["id"] in selected_ids]
    if not selected:
        flash("Choose at least one exercise before completing.")
        return redirect(url_for("workout", workout_id=workout_id))
    for ex, _sets in selected:
        for number in range(1, ex["target_sets"] + 1):
            reps = request.form.get(f"reps-{ex['id']}-{number}", type=int)
            weight = request.form.get(f"weight-{ex['id']}-{number}", type=float)
            if reps is None or weight is None or reps < 0 or weight < 0:
                flash("Every set needs non-negative reps and weight before completing.")
                return redirect(url_for("workout", workout_id=workout_id))
            db().execute("INSERT INTO sets (exercise_id,position,reps,weight) VALUES (?,?,?,?)", (ex["id"], number, reps, weight))
    db().execute("UPDATE workouts SET status='complete', completed_at=? WHERE id=?", (now(), workout_id))
    index = next((i for i, plan in enumerate(ROUTINE) if plan[0] == workout["routine_key"]), -1)
    key, name, plan = ROUTINE[(index + 1) % len(ROUTINE)]
    add_workout(db(), key, name, [(n,s,r,w,[]) for n,s,r,w in plan])
    db().commit()
    flash("Workout saved. Your next session is ready when you are.")
    return redirect(url_for("home"))

@app.route("/history")
def history():
    workouts = db().execute("SELECT * FROM workouts WHERE status='complete' ORDER BY id DESC").fetchall()
    exercise_names = db().execute("SELECT DISTINCT e.name FROM exercises e JOIN workouts w ON w.id=e.workout_id WHERE w.status='complete' ORDER BY e.name").fetchall()
    return render_template("history.html", workouts=with_display_date(workouts), exercise_names=exercise_names)

@app.route("/history/exercise")
def exercise_history():
    name = request.args.get("name", "")
    rows = db().execute("""SELECT w.name AS workout_name, w.completed_at, s.position, s.reps, s.weight
        FROM sets s JOIN exercises e ON e.id=s.exercise_id JOIN workouts w ON w.id=e.workout_id
        WHERE w.status='complete' AND e.name=? ORDER BY w.id DESC, s.position""", (name,)).fetchall()
    return render_template("exercise_history.html", name=name, rows=with_display_date(rows))

@app.route("/export")
def export_history():
    """Dump the current routine plus recent logged sets per exercise, as JSON, for
    pasting into a chat LLM prompt to get an updated routine.json back (see
    WEEKLY_PROMPT.md). No API keys or external calls involved."""
    names = [row["name"] for row in db().execute(
        "SELECT DISTINCT e.name FROM exercises e JOIN workouts w ON w.id=e.workout_id WHERE w.status='complete' ORDER BY e.name"
    ).fetchall()]
    history = {}
    for name in names:
        rows = db().execute("""SELECT w.completed_at, s.position, s.reps, s.weight
            FROM sets s JOIN exercises e ON e.id=s.exercise_id JOIN workouts w ON w.id=e.workout_id
            WHERE w.status='complete' AND e.name=? ORDER BY w.id DESC, s.position LIMIT 30""", (name,)).fetchall()
        sessions = {}
        for row in rows:
            sessions.setdefault(row["completed_at"], []).append({"reps": row["reps"], "weight": row["weight"]})
        history[name] = [{"completed_at": completed_at, "sets": sets} for completed_at, sets in sessions.items()]
    with open(ROUTINE_PATH) as handle:
        current_routine = json.load(handle)
    return {"routine": current_routine, "history": history}

if __name__ == "__main__": app.run(host="0.0.0.0", port=8000, debug=True)
