from flask import Flask, render_template, redirect, url_for
import sqlite3
from datetime import datetime

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


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
    conn = get_db_connection()
    unread_count = conn.execute(
        "SELECT COUNT(*) FROM Notifications WHERE is_read = 0"
    ).fetchone()[0]
    conn.close()

    return dict(unread_count=unread_count, time_ago=time_ago)


@app.route("/")
def home():
    conn = get_db_connection()

    notifications = conn.execute(
        "SELECT * FROM Notifications ORDER BY created_at DESC LIMIT 2"
    ).fetchall()

    conn.close()

    return render_template("index.html", notifications=notifications)


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/register")
def register():
    return render_template("register.html")


@app.route("/availability")
def availability():
    return render_template("availability.html")


@app.route("/meetings")
def meetings():
    return render_template("meetings.html")


@app.route("/alerts")
def alerts():
    conn = get_db_connection()

    notifications = conn.execute(
        "SELECT * FROM Notifications ORDER BY created_at DESC"
    ).fetchall()

    unread_count = conn.execute(
        "SELECT COUNT(*) FROM Notifications WHERE is_read = 0"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "alerts.html",
        notifications=notifications,
        unread_count=unread_count
    )


@app.route("/mark-read/<int:id>", methods=["POST"])
def mark_read(id):
    conn = get_db_connection()
    conn.execute(
        "UPDATE Notifications SET is_read = 1 WHERE notification_id = ?",
        (id,)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("alerts"))


@app.route("/profile")
def profile():
    return render_template("profile.html")


@app.route("/calendar")
def calendar():
    return render_template("calendar.html")


@app.route("/test-notification")
def test_notification():
    create_notification(1, "Database notification working!", "test")
    return "Notification added!"


@app.route("/test-meeting")
def test_meeting():
    create_notification(1, "Meeting 'Team Sync' created!", "meeting")
    return "Meeting + notification created!"


if __name__ == "__main__":
    app.run(debug=True)