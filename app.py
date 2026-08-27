
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from urllib.parse import quote
import mysql.connector
from datetime import timedelta, datetime
import re
from werkzeug.utils import secure_filename

import secrets
import json

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
    base64url_to_bytes,
)

from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)

load_dotenv()
app = Flask(__name__)
UPI_ID = "6305777042@axl"
PAYMENT_ACTION_OTP = "123456"
# =========================
# EVENT GALLERY
# =========================

GALLERY_FOLDER = os.path.join(
    app.static_folder,
    "gallery"
)

os.makedirs(
    GALLERY_FOLDER,
    exist_ok=True
)


ALLOWED_GALLERY_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}


def allowed_gallery_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_GALLERY_EXTENSIONS
    )
app.secret_key = "vinayaka123"
app.permanent_session_lifetime = timedelta(minutes=5)


# =========================
# WEBAUTHN CONFIGURATION
# =========================

RP_ID = "vinayaka-chandha.onrender.com"
RP_NAME = "Lakshmi Ganapathi Youth"
ORIGIN = "https://vinayaka-chandha.onrender.com"

# Sleep Mode

@app.before_request
def check_session():

   if request.endpoint not in [
    "login",
    "public_dashboard",
    "annadhanam_slot_availability",
    "donate",
    "submit_payment",
    "static"
    "passkey_login_options",
    "passkey_login_verify"
    ]:
        if "username" not in session:
            return redirect(url_for("login"))
        
# Sleep Mode End

USERS = {

    "Sai": {
        "password": "6281085945",
        "name": "Sai",
        "mobile": "6281085945",
        "email": ""
    },

    "Deepak": {
        "password": "7090430530",
        "name": "Deepak",
        "mobile": "7090430530",
        "email": ""
    },

    "Pardhu": {
        "password": "6305777042",
        "name": "Pardhu",
        "mobile": "6305777042",
        "email": ""
    },

    "Gopal": {
        "password": "9177981391",
        "name": "Gopal",
        "mobile": "9177981391",
        "email": ""
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

            # Store last login
            session["last_login"] = datetime.now().strftime(
                "%d-%m-%Y %I:%M:%S %p"
            )

            return redirect(url_for("dashboard"))
        msg = "❌ Invalid Username or Password"

    return render_template("login.html", msg=msg)


# =========================
# PASSKEY REGISTRATION OPTIONS
# =========================

@app.route("/passkey/register/options", methods=["POST"])
def passkey_register_options():

    if "username" not in session:
        return jsonify({
            "error": "Please login first."
        }), 401

    username = session["username"]

    conn, cursor = get_db()

    try:
        cursor.execute("""
            SELECT credential_id
            FROM webauthn_credentials
            WHERE username = %s
        """, (username,))

        rows = cursor.fetchall()

        exclude_credentials = [
            PublicKeyCredentialDescriptor(
                id=bytes(row["credential_id"])
            )
            for row in rows
        ]

        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_name=username,
            user_display_name=USERS[username]["name"],
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            exclude_credentials=exclude_credentials,
        )

        # Save challenge temporarily
        session["webauthn_register_challenge"] = options.challenge

        return jsonify(
            json.loads(options_to_json(options))
        )

    finally:
        cursor.close()
        conn.close()

# =========================
# PASSKEY LOGIN OPTIONS
# =========================

@app.route("/passkey/login/options", methods=["POST"])
def passkey_login_options():

    data = request.get_json() or {}
    username = data.get("username", "").strip()

    if username not in USERS:
        return jsonify({
            "error": "Invalid username."
        }), 401

    conn, cursor = get_db()

    try:
        cursor.execute("""
            SELECT credential_id
            FROM webauthn_credentials
            WHERE username = %s
        """, (username,))

        rows = cursor.fetchall()

        if not rows:
            return jsonify({
                "error": "No fingerprint is registered for this user."
            }), 404

        allow_credentials = [
            PublicKeyCredentialDescriptor(
                id=bytes(row["credential_id"])
            )
            for row in rows
        ]

        options = generate_authentication_options(
            rp_id=RP_ID,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.REQUIRED,
        )

        session["webauthn_login_challenge"] = options.challenge
        session["webauthn_login_username"] = username

        return jsonify(
            json.loads(options_to_json(options))
        )

    finally:
        cursor.close()
        conn.close()

# =========================
# PASSKEY LOGIN VERIFY
# =========================

@app.route("/passkey/login/verify", methods=["POST"])
def passkey_login_verify():

    data = request.get_json() or {}
    credential = data.get("credential")

    username = session.get(
        "webauthn_login_username"
    )

    challenge = session.get(
        "webauthn_login_challenge"
    )

    if not username or not challenge:
        return jsonify({
            "error": "Login session expired. Please try again."
        }), 400

    if not credential:
        return jsonify({
            "error": "Credential is missing."
        }), 400

    try:

        credential_id = base64url_to_bytes(
            credential["rawId"]
        )

        conn, cursor = get_db()

        try:

            cursor.execute("""
                SELECT
                    credential_id,
                    public_key,
                    sign_count
                FROM webauthn_credentials
                WHERE username = %s
                  AND credential_id = %s
            """, (
                username,
                credential_id
            ))

            stored = cursor.fetchone()

            if not stored:
                return jsonify({
                    "error": "Fingerprint credential not found."
                }), 401

            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=challenge,
                expected_rp_id=RP_ID,
                expected_origin=ORIGIN,
                credential_public_key=bytes(
                    stored["public_key"]
                ),
                credential_current_sign_count=int(
                    stored["sign_count"]
                ),
                require_user_verification=True,
            )

            cursor.execute("""
                UPDATE webauthn_credentials
                SET sign_count = %s
                WHERE username = %s
                  AND credential_id = %s
            """, (
                verification.new_sign_count,
                username,
                credential_id
            ))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

        # Create normal Flask login session
        session.permanent = True

        session["username"] = username
        session["name"] = USERS[username]["name"]

        session["last_login"] = datetime.now().strftime(
            "%d-%m-%Y %I:%M:%S %p"
        )

        session.pop(
            "webauthn_login_challenge",
            None
        )

        session.pop(
            "webauthn_login_username",
            None
        )

        return jsonify({
            "success": True,
            "redirect": url_for("dashboard")
        })

    except Exception as e:

        print(
            "WebAuthn login error:",
            str(e)
        )

        return jsonify({
            "success": False,
            "error": str(e)
        }), 401


# ------------------ Logout ------------------

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ================= MY PROFILE =================

@app.route("/my-profile")
def my_profile():

    username = session.get("username")

    if not username:
        return redirect(url_for("login"))

    user = USERS.get(username)

    if not user:
        return redirect(url_for("logout"))

    return render_template(
        "my_profile.html",
        username=username,
        user=user,
        last_login=session.get(
            "last_login",
            "Not available"
        )
    )

@app.route("/security", methods=["GET", "POST"])
def security():

    username = session.get("username")

    if not username:
        return redirect(url_for("login"))

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )


        # Check current password

        if USERS[username]["password"] != current_password:

            flash(
                "❌ Current password is incorrect."
            )

            return redirect(
                url_for("security")
            )


        # Check password match

        if new_password != confirm_password:

            flash(
                "❌ New passwords do not match."
            )

            return redirect(
                url_for("security")
            )


        # Minimum length

        if len(new_password) < 6:

            flash(
                "❌ Password must contain at least 6 characters."
            )

            return redirect(
                url_for("security")
            )


        # Change password

        USERS[username]["password"] = new_password


        flash(
            "✅ Password changed successfully."
        )


        return redirect(
            url_for("security")
        )


    return render_template(
        "security.html"
    )


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

 # ================= PAYMENT HISTORY =================

    cursor.execute("""
        SELECT
            id,
            donor_name,
            mobile,
            amount,
            transaction_id,
            payment_method,
            payment_date,
            status,
            remarks,
            created_at
        FROM payment_history
        ORDER BY created_at DESC
    """)

    payments = cursor.fetchall()

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
        payments=payments,
        name=session.get("name")
    )

@app.route("/payment-history")
def payment_history():

    conn, cursor = get_db()

    try:
        cursor.execute("""
            SELECT
                id,
                donor_name,
                mobile,
                amount,
                transaction_id,
                payment_method,
                payment_date,
                status,
                remarks,
                created_at
            FROM payment_history
            ORDER BY created_at DESC
        """)

        payments = cursor.fetchall()

        return render_template(
            "payment_history.html",
            payments=payments
        )

    finally:
        cursor.close()
        conn.close()


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
# ================= ANNADHANAM SLOT CONFIG =================

ANNADHANAM_SLOT_CAPACITY = 2

ANNADHANAM_SLOTS = {
    "2026-09-14": ["Morning"],
    "2026-09-15": ["Afternoon", "Evening"],
    "2026-09-16": ["Afternoon"]
}


def get_slot_availability(cursor, donation_date):

    slots = ANNADHANAM_SLOTS.get(
        donation_date,
        []
    )

    result = []

    for slot in slots:

        cursor.execute("""
            SELECT COUNT(*) AS booked
            FROM annadhanam_donors
            WHERE donation_date = %s
              AND slot = %s
              AND status IN ('pending', 'approved')
        """, (
            donation_date,
            slot
        ))

        row = cursor.fetchone()

        booked = row["booked"]

        remaining = max(
            ANNADHANAM_SLOT_CAPACITY - booked,
            0
        )

        result.append({
            "slot": slot,
            "capacity": ANNADHANAM_SLOT_CAPACITY,
            "booked": booked,
            "remaining": remaining
        })

    return result
@app.route("/annadhanam/slot-availability")
def annadhanam_slot_availability():

    donation_date = request.args.get(
        "date",
        ""
    ).strip()

    conn, cursor = get_db()

    try:

        slots = get_slot_availability(
            cursor,
            donation_date
        )

        return {
            "date": donation_date,
            "slots": slots
        }

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

# =========================
# ADMIN EVENT GALLERY
# =========================

@app.route("/admin/gallery", methods=["GET", "POST"])
def admin_gallery():

    if request.method == "POST":

        if "image" not in request.files:
            flash("Please select an image.", "error")
            return redirect(url_for("admin_gallery"))

        image = request.files["image"]

        if image.filename == "":
            flash("Please select an image.", "error")
            return redirect(url_for("admin_gallery"))

        if not allowed_gallery_file(image.filename):
            flash(
                "Only JPG, JPEG, PNG and WEBP images are allowed.",
                "error"
            )
            return redirect(url_for("admin_gallery"))

        filename = secure_filename(image.filename)

        image_path = os.path.join(
            GALLERY_FOLDER,
            filename
        )

        image.save(image_path)

        flash(
            "Event image uploaded successfully.",
            "success"
        )

        return redirect(
            url_for("admin_gallery")
        )

    # Get all gallery images
    gallery_images = []

    for filename in os.listdir(GALLERY_FOLDER):

        if allowed_gallery_file(filename):
            gallery_images.append(filename)

    gallery_images.sort()

    return render_template(
        "admin_gallery.html",
        gallery_images=gallery_images
    )


# =========================
# DELETE GALLERY IMAGE
# =========================

@app.route(
    "/admin/gallery/delete/<filename>",
    methods=["POST"]
)
def delete_gallery_image(filename):

    filename = secure_filename(filename)

    image_path = os.path.join(
        GALLERY_FOLDER,
        filename
    )

    if os.path.exists(image_path):

        os.remove(image_path)

        flash(
            "Event image deleted successfully.",
            "success"
        )

    else:

        flash(
            "Image not found.",
            "error"
        )

    return redirect(
        url_for("admin_gallery")
    )




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

                extension = image.filename.rsplit(
                    ".", 1
                )[-1].lower()

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

            flash(
                "✅ Annadhanam registration submitted successfully! "
                "🙏 Your request is pending admin approval."
            )

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


        balance = (
            total_collection
            - total_expenses
        )


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


        # =========================
        # EVENT GALLERY IMAGES
        # =========================

        gallery_images = []

        for filename in os.listdir(
            GALLERY_FOLDER
        ):

            if allowed_gallery_file(filename):

                gallery_images.append(
                    filename
                )

        gallery_images.sort()


        # =========================
        # PUBLIC DASHBOARD
        # =========================

        return render_template(
            "public_dashboard.html",
            total_collection=total_collection,
            total_expenses=total_expenses,
            balance=balance,
            annadhanam_donors=annadhanam_donors,
            gallery_images=gallery_images
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

@app.route("/submit_payment", methods=["POST"])
def submit_payment():

    conn, cursor = get_db()

    try:
        donor_name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        amount = request.form.get("amount", "").strip()
        transaction_id = request.form.get("utr", "").strip()

        if not donor_name or not mobile or not amount or not transaction_id:
            return "All payment details are required.", 400

        # Check duplicate transaction ID
        cursor.execute("""
            SELECT id
            FROM payment_history
            WHERE transaction_id = %s
        """, (transaction_id,))

        existing = cursor.fetchone()

        if existing:
            return """
            <script>
                alert("❌ This transaction ID has already been submitted.");
                window.location.href = "/public";
            </script>
            """

        cursor.execute("""
            INSERT INTO payment_history
            (
                donor_name,
                mobile,
                amount,
                transaction_id,
                payment_method,
                payment_date,
                status,
                remarks
            )
            VALUES
            (
                %s, %s, %s, %s, %s, NOW(), %s, %s
            )
        """, (
            donor_name,
            mobile,
            float(amount),
            transaction_id,
            "PhonePe",
            "Pending",
            "Payment submitted by donor"
        ))

        conn.commit()

        return """
        <script>
            alert("✅ Payment details submitted successfully!\\n\\nAdmin will verify your transaction.");
            window.location.href = "/public";
        </script>
        """

    except Exception as e:

        conn.rollback()

        return f"<h2>Error</h2><pre>{e}</pre>"

    finally:

        cursor.close()
        conn.close()

@app.route("/admin/payment/<int:id>/status", methods=["POST"])
def update_payment_status(id):

    if "username" not in session:
        return redirect(url_for("login"))

    status = request.form.get("status")
    otp = request.form.get("otp", "").strip()

    if status not in ["Pending", "Verified", "Rejected"]:
        return "Invalid status", 400

    # OTP required only for Reject
    if status == "Rejected":
        correct_otp = PAYMENT_ACTION_OTP

        if not otp or otp != correct_otp:
            flash("❌ Invalid OTP. Payment was not rejected.")
            return redirect(url_for("payment_history"))

    conn, cursor = get_db()

    try:

        cursor.execute("""
            UPDATE payment_history
            SET status = %s
            WHERE id = %s
        """, (
            status,
            id
        ))

        conn.commit()

        if status == "Rejected":
            flash("✅ Payment rejected successfully.")
        else:
            flash("✅ Payment status updated successfully.")

        return redirect(url_for("payment_history"))

    except Exception as e:

        conn.rollback()
        return f"<h2>Error</h2><pre>{e}</pre>"

    finally:
        cursor.close()
        conn.close()

        # ================= DELETE PAYMENT =================

@app.route("/delete_payment/<int:id>", methods=["POST"])
def delete_payment(id):

    if "username" not in session:
        return redirect(url_for("login"))

    otp = request.form.get("otp", "").strip()
    correct_otp = os.getenv("PAYMENT_ACTION_OTP", "")

    if not otp or otp != correct_otp:
        flash("❌ Invalid OTP. Payment was NOT deleted.")
        return redirect(url_for("payment_history"))

    conn, cursor = get_db()

    try:

        cursor.execute("""
            DELETE FROM payment_history
            WHERE id = %s
        """, (id,))

        conn.commit()

        flash("✅ Payment deleted successfully.")

        return redirect(url_for("payment_history"))

    except Exception as e:

        conn.rollback()
        return f"<h2>Error</h2><pre>{e}</pre>"

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)