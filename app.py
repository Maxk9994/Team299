from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")
    
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
    return render_template("alerts.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

if __name__ == "__main__":
    app.run(debug=True)