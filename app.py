
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from urllib.parse import quote
import mysql.connector

load_dotenv()
app = Flask(__name__)
app.secret_key = "vinayaka123"

USERS = {
    "Sai": {
        "password": "6281085945",
        "name": "Sai"
    },
    "Deepak": {
        "password": "7090430530",
        "name": "Deepak"
    },
    "Pardhu": {
        "password": "6305777042",
        "name": "Pardhu"
    },
    "Gopal": {
        "password": "9177981391",
        "name": "Gopal"
    }
}



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

        if username in USERS and USERS[username]["password"] == password:
            session["username"] = username
            session["name"] = USERS[username]["name"]
            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            msg="❌ Invalid Username or Password"
        )

    return render_template("login.html")
# ------------------ Logout ------------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

Dear {name} Garu,

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

    # Donors
    cursor.execute("""
    SELECT COUNT(*) AS total_donors
    FROM donations
""")
    total_donors = cursor.fetchone()["total_donors"]

    # Donation List
    cursor.execute("""
        SELECT
            id,
            name,
            mobile,
            donation,
            'paid' AS status
        FROM donations
        ORDER BY id ASC
    """)
    members = cursor.fetchall()

    # Expense List
    cursor.execute("""
        SELECT
            id,
            expense_name,
            amount,
            spent_by
        FROM expenses
        ORDER BY id ASC
    """)
    expenses = cursor.fetchall()
    print("EXPENSE DATA:", expenses)

    cursor.close()
    conn.close()
    return render_template(
        "dashboard.html",
    total_collection=total_collection,
    total_expenses=total_expenses,
    balance=balance,
    total_donors=total_donors,
    members=members,
    expenses=expenses,
    name=session.get("name")
    )

@app.route("/add_expense", methods=["POST"])
def add_expense():

    conn, cursor = get_db()

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
        conn.rollback()
        return f"<h2>Error</h2><pre>{e}</pre>"

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)