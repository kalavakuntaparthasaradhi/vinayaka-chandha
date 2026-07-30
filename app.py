import os
from flask import Flask, render_template, request, redirect, url_for, flash
from urllib.parse import quote
import mysql.connector

app = Flask(__name__)
app.secret_key = "vinayaka123"

USERNAME = "admin"
PASSWORD = "12345"

# ------------------ MySQL Connection ------------------
conn = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    port=int(os.getenv("MYSQLPORT")),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE")
)

cursor = conn.cursor(dictionary=True)

# ------------------ Login ------------------
@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == USERNAME and password == PASSWORD:
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            msg="❌ Invalid Username or Password"
        )

    return render_template("login.html")


# ------------------ Dashboard ------------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if request.method == "POST":
        try:
            name = request.form["name"]
            mobile = request.form["mobile"].replace("+91", "").replace(" ", "")
            area = request.form["area"]
            house = request.form["house"]
            donation = float(request.form["donation"])
            payment = request.form["payment"]
            date = request.form["date"]
            collector = request.form["collector"]
            remarks = request.form["remarks"]

            sql = """
            INSERT INTO donations
            (name, mobile, area, house, donation, payment, collector, remarks, donation_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            values = (
                name,
                mobile,
                area,
                house,
                donation,
                payment,
                collector,
                remarks,
                date
            )

            cursor.execute(sql, values)
            conn.commit()

            flash("✅ Chandha Collected Successfully!")

            message = f"""
🪔 Lakshmi Ganapathi Youth 🪔

Dear {name},

Your Donation has been collected successfully.

💰 Amount : ₹{donation}
📅 Date : {date}
📍 Area : {area}
🏠 House No : {house}
💳 Payment : {payment}

Thank you for your valuable contribution.

🌺 Happy Vinayaka Chavithi 🌺
"""

            whatsapp_url = f"https://wa.me/91{mobile}?text={quote(message)}"

            return redirect(whatsapp_url)

        except Exception as e:
            conn.rollback()
            return f"Error: {e}"

    # Daily Collection
    cursor.execute("""
        SELECT IFNULL(SUM(donation),0) AS total
        FROM donations
        WHERE donation_date = CURDATE()
    """)
    daily = cursor.fetchone()["total"]

    # Weekly Collection
    cursor.execute("""
        SELECT IFNULL(SUM(donation),0) AS total
        FROM donations
        WHERE YEARWEEK(donation_date,1)=YEARWEEK(CURDATE(),1)
    """)
    weekly = cursor.fetchone()["total"]

    # Today's Donors
    cursor.execute("""
        SELECT COUNT(*) AS donors
        FROM donations
        WHERE donation_date = CURDATE()
    """)
    today_donors = cursor.fetchone()["donors"]

    # All Donations
    cursor.execute("""
        SELECT
            id,
            name,
            mobile,
            area,
            house,
            donation,
            payment,
            collector,
            remarks,
            donation_date
        FROM donations
        ORDER BY id DESC
    """)

    members = cursor.fetchall()

    return render_template(
        "dashboard.html",
        daily=daily,
        weekly=weekly,
        today_donors=today_donors,
        members=members
    )


if __name__ == "__main__":
    app.run(debug=True)