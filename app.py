import os
from flask import Flask, render_template, request, redirect, url_for, flash
from urllib.parse import quote
import mysql.connector

app = Flask(__name__)
app.secret_key = "vinayaka123"

USERNAME = "admin"
PASSWORD = "12345"

# MySQL Connection
db_host = os.environ.get('DB_HOST')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_name = os.environ.get('DB_NAME')

mydb = mysql.connector.connect(
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)

cursor = conn.cursor(dictionary=True)


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


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    if request.method == "POST":

        name = request.form["name"]
        mobile = request.form["mobile"].replace("+91", "").replace(" ", "")
        area = request.form["area"]
        house = request.form["house"]
        donation = float(request.form["donation"])
        payment = request.form["payment"]
        date = request.form["date"]
        collector = request.form["collector"]
        remarks = request.form["remarks"]

        # Save Data
        sql = """
        INSERT INTO donations
        (name,mobile,area,house,donation,payment,collector,remarks,donation_date)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
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

        # WhatsApp Message
        message = f"""
🪔 Vinayaka Chavithi Committee 🪔

Dear {name},

Your Chandha has been collected successfully.

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

    # Today's Collection
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

    # Total Donors Today
    cursor.execute("""
        SELECT COUNT(*) AS donors
        FROM donations
        WHERE donation_date = CURDATE()
    """)
    today_donors = cursor.fetchone()["donors"]

    return render_template(
        "dashboard.html",
        daily=daily,
        weekly=weekly,
        today_donors=today_donors
    )


if __name__ == "__main__":
    app.run(debug=True)