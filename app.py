import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

DATABASE = "calendar.db"


def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to access that page.")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped_view


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT NOT NULL UNIQUE,
            Email TEXT NOT NULL UNIQUE,
            PasswordHash TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def create_notification(user_id, message, notif_type="info"):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO Notifications (user_id, message, type, is_read)
        VALUES (?, ?, ?, 0)
        """,
        (user_id, message, notif_type)
    )
    conn.commit()
    conn.close()


def time_ago(timestamp):
    now = datetime.now()
    diff = now - datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"

    hours = seconds // 3600
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"

    days = seconds // 86400
    return f"{days} day{'s' if days != 1 else ''} ago"


@app.context_processor
def inject_notifications():
    if not session.get("user_id"):
        return dict(unread_count=0, time_ago=time_ago)

    conn = get_db_connection()
    unread_count = conn.execute(
        "SELECT COUNT(*) FROM Notifications WHERE user_id = ? AND is_read = 0",
        (session["user_id"],)
    ).fetchone()[0]
    conn.close()

    return dict(unread_count=unread_count, time_ago=time_ago)

@app.route("/")
def index():
    if not session.get("user_id"):
        return render_template("landing.html")

    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()

    notifications = conn.execute(
        "SELECT * FROM Notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 2",
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template("index.html", notifications=notifications)



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM Users WHERE Email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["PasswordHash"], password):
            session["user_id"] = user["UserID"]
            session["username"] = user["Username"]
            flash("Login successful!")
            return redirect(url_for("index"))

        flash("Invalid email or password.")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("register"))

        conn = get_db_connection()
        existing_user = conn.execute(
            "SELECT * FROM Users WHERE Username = ? OR Email = ?",
            (username, email)
        ).fetchone()

        if existing_user:
            conn.close()
            flash("Username or email already exists.")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        conn.execute(
            "INSERT INTO Users (Username, Email, PasswordHash) VALUES (?, ?, ?)",
            (username, email, password_hash)
        )
        conn.commit()
        conn.close()

        flash("Account created successfully. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/availability")
@login_required
def availability():
    return render_template("availability.html")


@app.route("/meetings")
@login_required
def meetings():
    return render_template("meetings.html")


@app.route("/alerts")
@login_required
def alerts():
    conn = get_db_connection()

    notifications = conn.execute(
        "SELECT * FROM Notifications WHERE user_id = ? ORDER BY created_at DESC",
        (session["user_id"],)
    ).fetchall()

    unread_count = conn.execute(
        "SELECT COUNT(*) FROM Notifications WHERE user_id = ? AND is_read = 0",
        (session["user_id"],)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "alerts.html",
        notifications=notifications,
        unread_count=unread_count
    )


@app.route("/mark-read/<int:id>", methods=["POST"])
@login_required
def mark_read(id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE Notifications SET is_read = 1 WHERE notification_id = ? AND user_id = ?",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("alerts"))



@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@app.route("/calendar")
@login_required
def calendar():
    return render_template("calendar.html")


@app.route("/test-notification")
@login_required
def test_notification():
    create_notification(session["user_id"], "Database notification working!", "test")
    return "Notification added!"


@app.route("/test-meeting")
@login_required
def test_meeting():
    create_notification(session["user_id"], "Meeting 'Team Sync' created!", "meeting")
    return "Meeting + notification created!"


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
