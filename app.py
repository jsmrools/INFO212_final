from __future__ import annotations
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from wtforms import StringField, IntegerField, TextAreaField, SelectField, PasswordField
from wtforms.validators import DataRequired, NumberRange, Length
from flask_wtf import FlaskForm
import json, os
import models
from plan_logic import generate_plan, generate_weekly_plan

app = Flask(__name__)
app.config.update(SECRET_KEY="change-me-please")

os.makedirs("instance", exist_ok=True)
with app.app_context():
    models.init_db()

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ----------------- Auth model -----------------
class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.username = row["username"]
        self.password_hash = row["password_hash"]
    @staticmethod
    def from_username(username: str):
        row = models.user_get_by_username(username)
        return User(row) if row else None
    @staticmethod
    def from_id(user_id: int):
        row = models.user_get(user_id)
        return User(row) if row else None

@login_manager.user_loader
def load_user(user_id):
    return User.from_id(int(user_id))

# ----------------- Forms -----------------
class WorkoutForm(FlaskForm):
    name = StringField("Navn", validators=[DataRequired(), Length(max=100)])
    sets = IntegerField("Sett", validators=[DataRequired(), NumberRange(min=1, max=100)])
    duration_min = IntegerField("Varighet (min)", validators=[DataRequired(), NumberRange(min=1, max=600)])
    notes = TextAreaField("Notater", validators=[Length(max=500)])

class LoginForm(FlaskForm):
    username = StringField("Brukernavn", validators=[DataRequired(), Length(max=50)])
    password = PasswordField("Passord", validators=[DataRequired(), Length(min=3, max=200)])

class QuizForm(FlaskForm):
    goal = SelectField("Mål", choices=[
        ("hypertrofi","Hypertrofi"),("styrke","Styrke"),
        ("spenst","Spenst"),("utholdenhet","Utholdenhet")], validators=[DataRequired()])
    level = SelectField("Nivå", choices=[
        ("nybegynner","Nybegynner"),("middels","Middels"),("avansert","Avansert")], validators=[DataRequired()])
    gear = SelectField("Utstyr", choices=[
        ("fullt_gym","Fullt gym"),("kroppsvekt","Kroppsvekt"),("hjemme_enkle","Hjemme – enkle")], validators=[DataRequired()])

# ----------------- Pages -----------------
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/workouts")
@login_required
def workouts():
    form = WorkoutForm()
    workouts = models.workout_list(current_user.id)
    stats = models.workout_stats(current_user.id)
    quiz = QuizForm()
    return render_template("index.html", form=form, workouts=workouts, stats=stats, quiz=quiz)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        username = form.username.data.strip()
        password = form.password.data
        existing = models.user_get_by_username(username)
        if existing:
            user = User(existing)
            if bcrypt.check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for("workouts"))
            else:
                flash("Feil passord", "error")
        else:
            pw_hash = bcrypt.generate_password_hash(password).decode()
            uid = models.user_create(username, pw_hash)
            login_user(User.from_id(uid))
            return redirect(url_for("workouts"))
    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))

# ----------------- Workouts CRUD -----------------
@app.route("/workouts/create", methods=["POST"])
@login_required
def create_workout():
    form = WorkoutForm()
    ex_json = request.form.get("exercises_json", "[]")
    try:
        exercises = json.loads(ex_json)
        if not isinstance(exercises, list):
            exercises = []
    except Exception:
        exercises = []
    if form.validate_on_submit():
        models.workout_create(
            current_user.id,
            form.name.data,
            form.sets.data,
            form.duration_min.data,
            form.notes.data or None,
            exercises=exercises
        )
    workouts = models.workout_list(current_user.id)
    return render_template("workouts_list.html", workouts=workouts)

@app.route("/workouts/delete", methods=["POST"])
@login_required
def delete_workout():
    wid = int(request.form.get("workout_id", "0"))
    models.workout_delete(current_user.id, wid)
    workouts = models.workout_list(current_user.id)
    return render_template("workouts_list.html", workouts=workouts)

@app.route("/stats")
@login_required
def stats_partial():
    stats = models.workout_stats(current_user.id)
    return render_template("_stats.html", stats=stats)

# ----------------- Plan generators (yours) -----------------
@app.route("/questionnaire", methods=["POST"])
@login_required
def questionnaire():
    goal = request.form.get("goal","hypertrofi")
    level = request.form.get("level","nybegynner")
    gear = request.form.get("gear","fullt_gym")
    plan = generate_plan(goal, level, gear)
    return render_template("_plan_result.html", plan=plan, goal=goal, level=level, gear=gear)

@app.post("/questionnaire/weekly")
@login_required
def questionnaire_weekly():
    goal  = request.form.get("goal")
    level = request.form.get("level")
    gear  = request.form.get("gear")
    days  = int(request.form.get("days_per_week", 3))
    week  = generate_weekly_plan(goal, level, gear, days)
    return render_template("_weekly_plan.html", week=week)

@app.get("/example-card/<kind>")
def example_plan_card(kind):
    if kind == "strength":
        plan = generate_plan("hypertrofi", "middels", "full_gym")
        title = "Eksempel – Styrke"
    elif kind == "cardio":
        plan = generate_plan("utholdenhet", "nybegynner", "kroppsvekt")
        title = "Eksempel – Kondisjon"
    else:
        plan = generate_plan("hypertrofi", "nybegynner", "kroppsvekt")
        title = "Eksempel – Økt"
    return render_template("_mini_plan_card.html", title=title, items=plan[:5])

# ----------------- Calendar APIs (Marcus) -----------------
@app.get("/api/workouts")
@login_required
def api_workouts():
    # Prefer Marcus' helper if present; otherwise fall back to the list you already have
    if hasattr(models, "workouts_for_user"):
        return jsonify(models.workouts_for_user(current_user.id))
    return jsonify(models.workout_list(current_user.id))

@app.get("/api/sessions")
@login_required
def api_sessions():
    q_date = request.args.get("date")
    q_from = request.args.get("from")
    q_to = request.args.get("to")
    if q_date and hasattr(models, "sessions_on"):
        return jsonify(models.sessions_on(current_user.id, q_date))
    if q_from and q_to and hasattr(models, "sessions_between"):
        return jsonify(models.sessions_between(current_user.id, q_from, q_to))
    return jsonify({"error": "missing date/from/to or server not supporting sessions API"}), 400

@app.post("/api/sessions")
@login_required
def api_sessions_create():
    if not hasattr(models, "session_create"):
        return jsonify({"error": "sessions API not available on server"}), 501
    data = request.get_json(force=True) or {}
    date_str = data.get("date")
    workout_id = data.get("workout_id")
    notes = data.get("notes")
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    if not date_str or not workout_id:
        return jsonify({"error": "missing date/workout_id"}), 400
    created = models.session_create(current_user.id, int(workout_id), date_str, notes, start_time, end_time)
    return jsonify(created), 201

@app.delete("/api/sessions/<int:sid>")
@login_required
def api_sessions_delete(sid: int):
    if not hasattr(models, "session_delete"):
        return jsonify({"error": "sessions API not available on server"}), 501
    models.session_delete(current_user.id, sid)
    return jsonify({"ok": True})

@app.get("/calendar")
@login_required
def calendar_page():
    return render_template("calendar.html")

# ----------------- Entry -----------------
if __name__ == "__main__":
    app.run(debug=True)
