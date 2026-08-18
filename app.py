
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session
from urllib.parse import quote
import mysql.connector
from datetime import timedelta
import re

load_dotenv()
app = Flask(__name__)
app.secret_key = "vinayaka123"
app.permanent_session_lifetime = timedelta(minutes=5)

# Sleep Mode

@app.before_request
def check_session():

    if request.endpoint not in ["login","public_dashboard","static"]:

        if "username" not in session:
            return redirect(url_for("login"))
        
# Sleep Mode End

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

    msg = ""   # Initialize message first

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in USERS and USERS[username]["password"] == password:

            session.permanent = True
            session["username"] = username
            session["name"] = USERS[username]["name"]

            return redirect(url_for("dashboard"))

        msg = "❌ Invalid Username or Password"

    return render_template("login.html", msg=msg)

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
            mobile = request.form["mobile"].strip()

            # Mobile validation
            if not re.fullmatch(r"[6-9][0-9]{9}", mobile):
                return "Invalid mobile number. Please enter a valid 10-digit mobile number.", 400

            area = request.form["area"]
            house = request.form["house"]
            donation = float(request.form["donation"])
            payment = request.form["payment"]
            date = request.form["date"]
            collector = request.form["collector"]
            remarks = request.form["remarks"]

            sql = """
                INSERT INTO donations
                (name, mobile, area, house, donation, payment,
                 collector, remarks, donation_date)
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

        finally:
            cursor.close()
            conn.close()

    # Total Collection
    cursor.execute("""
        SELECT IFNULL(SUM(donation), 0) AS total
        FROM donations
    """)
    total_collection = cursor.fetchone()["total"]

    # Total Expenses
    cursor.execute("""
        SELECT IFNULL(SUM(amount), 0) AS total
        FROM expenses
    """)
    total_expenses = cursor.fetchone()["total"]

    # Balance
    balance = total_collection - total_expenses

    # Total Donors
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

# ================= ANNADHANAM =================

@app.route("/admin/annadhanam")
def admin_annadhanam():

    conn, cursor = get_db()

    try:

        cursor.execute("""
            SELECT
                id,
                name,
                gothram,
                mobile_number,
                donation_date,
                slot,
                image_url,
                status
            FROM annadhanam_donors
            ORDER BY id DESC
        """)

        donors = cursor.fetchall()

        cursor.execute("""
            SELECT status, COUNT(*) AS total
            FROM annadhanam_donors
            GROUP BY status
        """)

        counts = {
            "pending": 0,
            "approved": 0,
            "rejected": 0
        }

        for row in cursor.fetchall():

            if row["status"] in counts:
                counts[row["status"]] = row["total"]

        return render_template(
            "admin_annadhanam.html",
            donors=donors,
            counts=counts
        )

    except Exception as e:

        return f"""
        <h2>Annadhanam Error</h2>
        <pre>{e}</pre>
        """

    finally:

        cursor.close()
        conn.close()


# ================= ADD ANNADHANAM =================

@app.route("/admin/annadhanam/add", methods=["GET", "POST"])
def add_annadhanam():

    if request.method == "GET":

        return render_template(
            "annadhanam.html"
        )

    conn, cursor = get_db()

    try:

        name = request.form.get("name", "").strip()

        gothram = request.form.get(
            "gothram", ""
        ).strip()

        mobile = request.form.get(
            "mobile", ""
        ).strip()

        donation_date = request.form.get(
            "donation_date", ""
        ).strip()

        slot = request.form.get(
            "slot", ""
        ).strip()

        if not name or not mobile or not donation_date or not slot:

            return "Please fill all required fields.", 400

        cursor.execute("""
            INSERT INTO annadhanam_donors
            (
                name,
                gothram,
                mobile_number,
                donation_date,
                slot,
                image_url,
                status
            )
            VALUES
            (%s, %s, %s, %s, %s, %s, 'pending')
        """, (
            name,
            gothram,
            mobile,
            donation_date,
            slot,
            None
        ))

        conn.commit()

        return redirect(
            url_for("admin_annadhanam")
        )

    except Exception as e:

        conn.rollback()

        return f"""
        <h2>Error</h2>
        <pre>{e}</pre>
        """

    finally:

        cursor.close()
        conn.close()


# ================= APPROVE / REJECT =================

@app.route(
    "/admin/annadhanam/<int:id>/status",
    methods=["POST"]
)
def update_annadhanam_status(id):

    status = request.form.get("status")

    if status not in [
        "pending",
        "approved",
        "rejected"
    ]:

        return "Invalid status", 400

    conn, cursor = get_db()

    try:

        cursor.execute("""
            UPDATE annadhanam_donors
            SET status = %s
            WHERE id = %s
        """, (
            status,
            id
        ))

        conn.commit()

        return redirect(
            url_for("admin_annadhanam")
        )

    except Exception as e:

        conn.rollback()

        return f"""
        <h2>Error</h2>
        <pre>{e}</pre>
        """

    finally:

        cursor.close()
        conn.close()


# ================= DELETE =================

@app.route(
    "/admin/annadhanam/<int:id>/delete",
    methods=["POST"]
)
def delete_annadhanam(id):

    conn, cursor = get_db()

    try:

        cursor.execute("""
            DELETE FROM annadhanam_donors
            WHERE id = %s
        """, (id,))

        conn.commit()

        return redirect(
            url_for("admin_annadhanam")
        )

    except Exception as e:

        conn.rollback()

        return f"""
        <h2>Error</h2>
        <pre>{e}</pre>
        """

    finally:

        cursor.close()
        conn.close()

# ------------------ Public Dashboard ------------------

@app.route("/public", methods=["GET", "POST"])
def public_dashboard():

    conn, cursor = get_db()

    try:

        # ================= PUBLIC ANNADHANAM SUBMISSION =================

        if request.method == "POST":

            name = request.form.get("name", "").strip()
            gothram = request.form.get("gothram", "").strip()
            mobile = request.form.get("mobile", "").strip()
            donation_date = request.form.get("donation_date", "").strip()
            slot = request.form.get("slot", "").strip()

            # Validate required fields
            if not name or not mobile or not donation_date or not slot:
                return "Please fill all required fields.", 400

            # Validate mobile
            if not re.fullmatch(r"[6-9][0-9]{9}", mobile):
                return "Invalid mobile number.", 400

            # ---------------- Image ----------------

            image_url = None

            image = request.files.get("image")

            if image and image.filename:

                import base64

                image_bytes = image.read()

                # Maximum 5 MB
                if len(image_bytes) > 5 * 1024 * 1024:
                    return "Image must be less than 5 MB.", 400

                extension = image.filename.rsplit(".", 1)[-1].lower()

                mime_types = {
                    "jpg": "image/jpeg",
                    "jpeg": "image/jpeg",
                    "png": "image/png",
                    "gif": "image/gif",
                    "webp": "image/webp"
                }

                if extension not in mime_types:
                    return "Invalid image format.", 400

                encoded = base64.b64encode(
                    image_bytes
                ).decode("utf-8")

                image_url = (
                    f"data:{mime_types[extension]};base64,{encoded}"
                )

            # ---------------- Save ----------------

            cursor.execute("""
                INSERT INTO annadhanam_donors
                (
                    name,
                    gothram,
                    mobile_number,
                    donation_date,
                    slot,
                    image_url,
                    status
                )
                VALUES
                (%s, %s, %s, %s, %s, %s, 'pending')
            """, (
                name,
                gothram,
                mobile,
                donation_date,
                slot,
                image_url
            ))

            conn.commit()

            return redirect(
                url_for("public_dashboard")
            )

        # ================= FINANCIAL DATA =================

        cursor.execute("""
            SELECT IFNULL(SUM(donation), 0) AS total
            FROM donations
        """)

        total_collection = cursor.fetchone()["total"]


        cursor.execute("""
            SELECT IFNULL(SUM(amount), 0) AS total
            FROM expenses
        """)

        total_expenses = cursor.fetchone()["total"]


        balance = total_collection - total_expenses


        # ================= APPROVED ANNADHANAM =================

        cursor.execute("""
            SELECT
                id,
                name,
                gothram,
                donation_date,
                slot,
                image_url
            FROM annadhanam_donors
            WHERE status = 'approved'
            ORDER BY donation_date ASC, id ASC
        """)

        annadhanam_donors = cursor.fetchall()


        return render_template(
            "public_dashboard.html",
            total_collection=total_collection,
            total_expenses=total_expenses,
            balance=balance,
            annadhanam_donors=annadhanam_donors
        )

    except Exception as e:

        conn.rollback()

        return f"Error: {e}"

    finally:

        cursor.close()
        conn.close()

# ----------edit---------------

@app.route("/edit_donation/<int:id>", methods=["GET", "POST"])
def edit_donation(id):

    conn, cursor = get_db()

    try:
        cursor.execute(
            "SELECT * FROM donations WHERE id = %s",
            (id,)
        )

        donation = cursor.fetchone()

        if not donation:
            return "Donation not found", 404

        if request.method == "POST":

            name = request.form["name"]
            mobile = request.form["mobile"].replace("+91", "").replace(" ", "")
            area = request.form["area"]
            house = request.form["house"]
            payment = request.form["payment"]
            collector = request.form["collector"]
            remarks = request.form["remarks"]
            donation_date = request.form["donation_date"]

            cursor.execute("""
                UPDATE donations
                SET
                    name = %s,
                    mobile = %s,
                    area = %s,
                    house = %s,
                    payment = %s,
                    collector = %s,
                    remarks = %s,
                    donation_date = %s
                WHERE id = %s
            """, (
                name,
                mobile,
                area,
                house,
                payment,
                collector,
                remarks,
                donation_date,
                id
            ))

            conn.commit()

            return redirect(url_for("dashboard"))

        return render_template(
            "edit_donation.html",
            donation=donation
        )

    except Exception as e:
        conn.rollback()
        return f"Error: {e}"

    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)