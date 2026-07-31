import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from urllib.parse import quote
import mysql.connector

load_dotenv()
app = Flask(__name__)
app.secret_key = "vinayaka123"

USERNAME = "admin"
PASSWORD = "12345"
print(os.getenv("MYSQLHOST"))
print(os.getenv("MYSQLPORT"))
print(os.getenv("MYSQLUSER"))
print(os.getenv("MYSQLDATABASE"))
# ------------------ MySQL Connection ------------------
def get_db():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        port=int(os.getenv("MYSQLPORT")),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        ssl_disabled=False
    )
    return conn, conn.cursor(dictionary=True)

# Test Connection
conn, cursor = get_db()

cursor.execute("SELECT DATABASE() AS db")
print("Database:", cursor.fetchone())

cursor.execute("SELECT COUNT(*) AS total FROM donations")
print("Total donations:", cursor.fetchone())

cursor.close()
conn.close()

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

    conn, cursor = get_db()

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
            cursor.close()
            conn.close()

            flash("✅ Donation Saved Successfully!")

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

       

    # Total Collection
    cursor.execute("""
        SELECT IFNULL(SUM(donation),0) AS total
        FROM donations
    """)
    total_collection = cursor.fetchone()["total"]

    # Total Expenses
    cursor.execute("""
        SELECT IFNULL(SUM(amount),0) AS total
        FROM expenses
    """)
    total_expenses = cursor.fetchone()["total"]

    # Balance
    balance = total_collection - total_expenses

    
    # Donation List
    cursor.execute("""
        SELECT
            id,
            name,
            mobile,
            donation,
            'paid' AS status
        FROM donations
        ORDER BY id DESC
    """)
    members = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template(
        "dashboard.html",
    total_collection=total_collection,
    total_expenses=total_expenses,
    balance=balance,
    members=members
    )

@app.route("/add_expense", methods=["POST"])
def add_expense():
    try:
        expense_name = request.form["expense_name"]
        amount = float(request.form["amount"])
        payment_mode = request.form["payment_mode"]
        spent_by = request.form["spent_by"]
        expense_date = request.form["expense_date"]
        remarks = request.form["remarks"]

        cursor.execute("""
            INSERT INTO expenses
            (expense_name, amount, payment_mode, spent_by, remarks, expense_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            expense_name,
            amount,
            payment_mode,
            spent_by,
            remarks,
            expense_date
        ))

        conn.commit()
        return redirect(url_for("dashboard"))

    except Exception as e:
        return f"<h2>Error</h2><pre>{e}</pre>"

if __name__ == "__main__":
    app.run(debug=True)