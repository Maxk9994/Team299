import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

DATABASE = "calendar.db"


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
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return render_template("index.html")


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
def availability():
    return render_template("availability.html")


@app.route("/meetings")
def meetings():
    return render_template("meetings.html")


@app.route("/alerts")
def alerts():
    return render_template("alerts.html")


@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
