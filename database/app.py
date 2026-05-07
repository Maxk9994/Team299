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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS Availability (
            AvailabilityID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID INTEGER NOT NULL,
            DayOfWeek TEXT NOT NULL,
            StartTime TEXT NOT NULL,
            EndTime TEXT NOT NULL,
            Status TEXT NOT NULL CHECK(Status IN ('available', 'unavailable')),
            FOREIGN KEY (UserID) REFERENCES Users(UserID)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS Meetings (
            MeetingID INTEGER PRIMARY KEY AUTOINCREMENT,
            OrganizerUserID INTEGER NOT NULL,
            Title TEXT NOT NULL,
            Description TEXT NOT NULL,
            MeetingDate TEXT NOT NULL,
            StartTime TEXT NOT NULL,
            EndTime TEXT NOT NULL,
            Status TEXT NOT NULL DEFAULT 'scheduled',
            FOREIGN KEY (OrganizerUserID) REFERENCES Users(UserID)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS MeetingInvites (
            InviteID INTEGER PRIMARY KEY AUTOINCREMENT,
            MeetingID INTEGER NOT NULL,
            UserID INTEGER NOT NULL,
            ResponseStatus TEXT NOT NULL DEFAULT 'pending',
            FOREIGN KEY (MeetingID) REFERENCES Meetings(MeetingID),
            FOREIGN KEY (UserID) REFERENCES Users(UserID),
            UNIQUE (MeetingID, UserID)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS Connections (
            ConnectionID INTEGER PRIMARY KEY AUTOINCREMENT,
            RequesterUserID INTEGER NOT NULL,
            AddresseeUserID INTEGER NOT NULL,
            Status TEXT NOT NULL CHECK(Status IN ('pending', 'accepted', 'rejected')),
            CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (RequesterUserID) REFERENCES Users(UserID),
            FOREIGN KEY (AddresseeUserID) REFERENCES Users(UserID),
            UNIQUE (RequesterUserID, AddresseeUserID)
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


def evaluate_user_availability(conn, user_id, day_of_week, start_time, end_time):
    records = conn.execute(
        """
        SELECT StartTime, EndTime, Status
        FROM Availability
        WHERE UserID = ? AND DayOfWeek = ?
        """,
        (user_id, day_of_week),
    ).fetchall()

    if not records:
        return "no availability set"

    has_available_overlap = False
    for record in records:
        overlaps = record["StartTime"] < end_time and record["EndTime"] > start_time
        if not overlaps:
            continue
        if record["Status"] == "unavailable":
            return "unavailable"
        if record["Status"] == "available":
            has_available_overlap = True

    if has_available_overlap:
        return "available"
    return "unavailable"


def get_connected_users(conn, user_id):
    return conn.execute(
        """
        SELECT DISTINCT u.UserID, u.Username, u.Email
        FROM Connections c
        JOIN Users u ON (
            (c.RequesterUserID = ? AND c.AddresseeUserID = u.UserID)
            OR
            (c.AddresseeUserID = ? AND c.RequesterUserID = u.UserID)
        )
        WHERE c.Status = 'accepted'
        ORDER BY u.Username
        """,
        (user_id, user_id),
    ).fetchall()


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


@app.route("/availability", methods=["GET", "POST"])
@login_required
def availability():
    days_of_week = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    status_options = ["available", "unavailable"]

    if request.method == "POST":
        day_of_week = request.form.get("day_of_week", "").strip()
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()
        status = request.form.get("status", "").strip().lower()

        if not day_of_week or not start_time or not end_time or not status:
            flash("All availability fields are required.")
            return redirect(url_for("availability"))

        if day_of_week not in days_of_week or status not in status_options:
            flash("Please choose valid availability options.")
            return redirect(url_for("availability"))

        try:
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")
        except ValueError:
            flash("Please enter valid start and end times.")
            return redirect(url_for("availability"))

        if end_dt <= start_dt:
            flash("End time must be later than start time.")
            return redirect(url_for("availability"))

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO Availability (UserID, DayOfWeek, StartTime, EndTime, Status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session["user_id"], day_of_week, start_time, end_time, status),
        )
        conn.commit()
        conn.close()

        flash("Availability added successfully.")
        return redirect(url_for("availability"))

    conn = get_db_connection()
    availability_records = conn.execute(
        """
        SELECT AvailabilityID, DayOfWeek, StartTime, EndTime, Status
        FROM Availability
        WHERE UserID = ?
        ORDER BY
            CASE DayOfWeek
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END,
            StartTime
        """,
        (session["user_id"],),
    ).fetchall()
    conn.close()

    return render_template(
        "availability.html",
        availability_records=availability_records,
        days_of_week=days_of_week,
        status_options=status_options,
    )


@app.route("/availability/delete/<int:availability_id>", methods=["POST"])
@login_required
def delete_availability(availability_id):
    conn = get_db_connection()
    deleted = conn.execute(
        "DELETE FROM Availability WHERE AvailabilityID = ? AND UserID = ?",
        (availability_id, session["user_id"]),
    )
    conn.commit()
    conn.close()

    if deleted.rowcount == 0:
        flash("Availability record not found.")
    else:
        flash("Availability record deleted.")

    return redirect(url_for("availability"))


@app.route("/meetings")
@login_required
def meetings():
    conn = get_db_connection()

    created_meetings = conn.execute(
        """
        SELECT MeetingID, Title, Description, MeetingDate, StartTime, EndTime, Status
        FROM Meetings
        WHERE OrganizerUserID = ?
        ORDER BY MeetingDate, StartTime
        """,
        (session["user_id"],),
    ).fetchall()

    invited_meetings = conn.execute(
        """
        SELECT
            m.MeetingID,
            m.Title,
            m.Description,
            m.MeetingDate,
            m.StartTime,
            m.EndTime,
            m.Status,
            u.Username AS OrganizerName,
            mi.ResponseStatus
        FROM MeetingInvites mi
        JOIN Meetings m ON m.MeetingID = mi.MeetingID
        JOIN Users u ON u.UserID = m.OrganizerUserID
        WHERE mi.UserID = ?
        ORDER BY m.MeetingDate, m.StartTime
        """,
        (session["user_id"],),
    ).fetchall()

    conn.close()

    return render_template(
        "meetings.html",
        created_meetings=created_meetings,
        invited_meetings=invited_meetings,
    )


@app.route("/meetings/create", methods=["GET", "POST"])
@login_required
def create_meeting():
    form_data = {
        "title": "",
        "description": "",
        "meeting_date": "",
        "start_time": "",
        "end_time": "",
    }
    selected_user_ids = []
    availability_results = []
    show_confirmation = False

    conn = get_db_connection()
    invite_candidates = get_connected_users(conn, session["user_id"])

    if request.method == "POST":
        form_data["title"] = request.form.get("title", "").strip()
        form_data["description"] = request.form.get("description", "").strip()
        form_data["meeting_date"] = request.form.get("meeting_date", "").strip()
        form_data["start_time"] = request.form.get("start_time", "").strip()
        form_data["end_time"] = request.form.get("end_time", "").strip()
        selected_user_ids = request.form.getlist("invited_users")
        confirm_create = request.form.get("confirm_create") == "1"

        if (
            not form_data["title"]
            or not form_data["description"]
            or not form_data["meeting_date"]
            or not form_data["start_time"]
            or not form_data["end_time"]
        ):
            conn.close()
            flash("Title, description, date, start time, and end time are required.")
            return redirect(url_for("create_meeting"))

        try:
            meeting_date = datetime.strptime(form_data["meeting_date"], "%Y-%m-%d")
            start_dt = datetime.strptime(form_data["start_time"], "%H:%M")
            end_dt = datetime.strptime(form_data["end_time"], "%H:%M")
        except ValueError:
            conn.close()
            flash("Please enter a valid date and time.")
            return redirect(url_for("create_meeting"))

        if end_dt <= start_dt:
            conn.close()
            flash("End time must be later than start time.")
            return redirect(url_for("create_meeting"))

        valid_user_ids = {str(user["UserID"]) for user in invite_candidates}
        selected_user_ids = [int(user_id) for user_id in selected_user_ids if user_id in valid_user_ids]
        day_of_week = meeting_date.strftime("%A")

        for user in invite_candidates:
            if user["UserID"] not in selected_user_ids:
                continue
            availability_status = evaluate_user_availability(
                conn,
                user["UserID"],
                day_of_week,
                form_data["start_time"],
                form_data["end_time"],
            )
            availability_results.append(
                {
                    "user_id": user["UserID"],
                    "username": user["Username"],
                    "email": user["Email"],
                    "status": availability_status,
                }
            )

        if not confirm_create:
            show_confirmation = True
            flash("Availability checked. Review results, then confirm meeting creation.")
            conn.close()
            return render_template(
                "create_meeting.html",
                invite_candidates=invite_candidates,
                form_data=form_data,
                selected_user_ids=selected_user_ids,
                availability_results=availability_results,
                show_confirmation=show_confirmation,
                day_of_week=day_of_week,
            )

        cursor = conn.execute(
            """
            INSERT INTO Meetings (
                OrganizerUserID, Title, Description, MeetingDate, StartTime, EndTime, Status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                form_data["title"],
                form_data["description"],
                form_data["meeting_date"],
                form_data["start_time"],
                form_data["end_time"],
                "scheduled",
            ),
        )
        meeting_id = cursor.lastrowid

        for invited_user_id in selected_user_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO MeetingInvites (MeetingID, UserID, ResponseStatus)
                VALUES (?, ?, 'pending')
                """,
                (meeting_id, invited_user_id),
            )
            conn.execute(
                """
                INSERT INTO Notifications (user_id, message, type, is_read)
                VALUES (?, ?, 'meeting', 0)
                """,
                (
                    invited_user_id,
                    f"You were invited to meeting '{form_data['title']}'.",
                ),
            )

        conn.commit()
        conn.close()

        flash("Meeting created successfully.")
        return redirect(url_for("meetings"))

    conn.close()
    return render_template(
        "create_meeting.html",
        invite_candidates=invite_candidates,
        form_data=form_data,
        selected_user_ids=selected_user_ids,
        availability_results=availability_results,
        show_confirmation=show_confirmation,
        day_of_week="",
    )


@app.route("/friends")
@login_required
def friends():
    current_user_id = session["user_id"]
    query = request.args.get("q", "").strip()

    conn = get_db_connection()

    incoming_requests = conn.execute(
        """
        SELECT c.ConnectionID, u.UserID, u.Username, u.Email, c.CreatedAt
        FROM Connections c
        JOIN Users u ON u.UserID = c.RequesterUserID
        WHERE c.AddresseeUserID = ? AND c.Status = 'pending'
        ORDER BY c.CreatedAt DESC
        """,
        (current_user_id,),
    ).fetchall()

    outgoing_requests = conn.execute(
        """
        SELECT c.ConnectionID, u.UserID, u.Username, u.Email, c.CreatedAt
        FROM Connections c
        JOIN Users u ON u.UserID = c.AddresseeUserID
        WHERE c.RequesterUserID = ? AND c.Status = 'pending'
        ORDER BY c.CreatedAt DESC
        """,
        (current_user_id,),
    ).fetchall()

    accepted_friends = get_connected_users(conn, current_user_id)

    search_results = []
    if query:
        candidate_rows = conn.execute(
            """
            SELECT UserID, Username, Email
            FROM Users
            WHERE UserID != ? AND Username LIKE ?
            ORDER BY Username
            LIMIT 20
            """,
            (current_user_id, f"%{query}%"),
        ).fetchall()

        for user in candidate_rows:
            connection = conn.execute(
                """
                SELECT Status
                FROM Connections
                WHERE
                    (RequesterUserID = ? AND AddresseeUserID = ?)
                    OR
                    (RequesterUserID = ? AND AddresseeUserID = ?)
                LIMIT 1
                """,
                (current_user_id, user["UserID"], user["UserID"], current_user_id),
            ).fetchone()

            if not connection:
                action_label = "add"
            elif connection["Status"] == "accepted":
                action_label = "connected"
            elif connection["Status"] == "pending":
                action_label = "pending"
            else:
                action_label = "add"

            search_results.append(
                {
                    "user_id": user["UserID"],
                    "username": user["Username"],
                    "email": user["Email"],
                    "action_label": action_label,
                }
            )

    conn.close()

    return render_template(
        "friends.html",
        query=query,
        incoming_requests=incoming_requests,
        outgoing_requests=outgoing_requests,
        accepted_friends=accepted_friends,
        search_results=search_results,
    )


@app.route("/friends/request", methods=["POST"])
@login_required
def send_friend_request():
    current_user_id = session["user_id"]
    target_user_id = request.form.get("target_user_id", "").strip()

    if not target_user_id.isdigit():
        flash("Invalid user selection.")
        return redirect(url_for("friends"))

    target_user_id = int(target_user_id)
    if target_user_id == current_user_id:
        flash("You cannot add yourself.")
        return redirect(url_for("friends"))

    conn = get_db_connection()
    target_user = conn.execute(
        "SELECT UserID FROM Users WHERE UserID = ?",
        (target_user_id,),
    ).fetchone()
    if not target_user:
        conn.close()
        flash("User not found.")
        return redirect(url_for("friends"))

    connection = conn.execute(
        """
        SELECT ConnectionID, Status
        FROM Connections
        WHERE
            (RequesterUserID = ? AND AddresseeUserID = ?)
            OR
            (RequesterUserID = ? AND AddresseeUserID = ?)
        LIMIT 1
        """,
        (current_user_id, target_user_id, target_user_id, current_user_id),
    ).fetchone()

    if connection:
        if connection["Status"] == "accepted":
            conn.close()
            flash("You are already connected.")
            return redirect(url_for("friends"))
        if connection["Status"] == "pending":
            conn.close()
            flash("A friend request already exists.")
            return redirect(url_for("friends"))

        conn.execute(
            """
            UPDATE Connections
            SET RequesterUserID = ?, AddresseeUserID = ?, Status = 'pending', CreatedAt = CURRENT_TIMESTAMP
            WHERE ConnectionID = ?
            """,
            (current_user_id, target_user_id, connection["ConnectionID"]),
        )
    else:
        conn.execute(
            """
            INSERT INTO Connections (RequesterUserID, AddresseeUserID, Status)
            VALUES (?, ?, 'pending')
            """,
            (current_user_id, target_user_id),
        )

    conn.execute(
        """
        INSERT INTO Notifications (user_id, message, type, is_read)
        VALUES (?, ?, 'info', 0)
        """,
        (target_user_id, "You received a new friend request."),
    )
    conn.commit()
    conn.close()

    flash("Friend request sent.")
    return redirect(url_for("friends"))


@app.route("/friends/respond/<int:connection_id>", methods=["POST"])
@login_required
def respond_friend_request(connection_id):
    action = request.form.get("action", "").strip().lower()
    if action not in ("accept", "reject"):
        flash("Invalid action.")
        return redirect(url_for("friends"))

    conn = get_db_connection()
    connection = conn.execute(
        """
        SELECT ConnectionID, RequesterUserID, AddresseeUserID, Status
        FROM Connections
        WHERE ConnectionID = ?
        """,
        (connection_id,),
    ).fetchone()

    if not connection:
        conn.close()
        flash("Friend request not found.")
        return redirect(url_for("friends"))

    if connection["AddresseeUserID"] != session["user_id"]:
        conn.close()
        flash("You are not allowed to update this request.")
        return redirect(url_for("friends"))

    if connection["Status"] != "pending":
        conn.close()
        flash("This request has already been handled.")
        return redirect(url_for("friends"))

    new_status = "accepted" if action == "accept" else "rejected"
    conn.execute(
        "UPDATE Connections SET Status = ? WHERE ConnectionID = ?",
        (new_status, connection_id),
    )

    notification_message = (
        "Your friend request was accepted."
        if new_status == "accepted"
        else "Your friend request was rejected."
    )
    conn.execute(
        """
        INSERT INTO Notifications (user_id, message, type, is_read)
        VALUES (?, ?, 'info', 0)
        """,
        (connection["RequesterUserID"], notification_message),
    )
    conn.commit()
    conn.close()

    flash(f"Friend request {new_status}.")
    return redirect(url_for("friends"))


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
    return redirect(url_for("friends"))


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
