from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import sqlite3
import random
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "supersecretkey"

def delete_image(image_path):
    if image_path:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], image_path)
        if os.path.exists(file_path):
            os.remove(file_path)

# ==============================
# IMAGE UPLOAD CONFIG
# ==============================

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ==============================
# EMAIL CONFIGURATION
# ==============================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'smartlostandfoundsystem@gmail.com'
app.config['MAIL_PASSWORD'] = 'biuvuenu pgdtyzlo'
app.config['MAIL_DEFAULT_SENDER'] = 'smartlostandfoundsystem@gmail.com'

mail = Mail(app)

# ==============================
# DATABASE INITIALIZATION
# ==============================

def init_db():
    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    with open("database.sql", "r") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()

init_db()

# ==============================
# SERVE IMAGES
# ==============================

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==============================
# BASIC PAGES
# ==============================

@app.route("/")
def signup_page():
    return render_template("index.html")

@app.route("/login_page")
def login_page():
    return render_template("login.html")

@app.route("/home")
def home():
    if "user" in session:
        return render_template("home.html")
    return redirect(url_for("login_page"))

# ==============================
# SIGNUP
# ==============================

@app.route("/signup", methods=["POST"])
def signup():

    fullname = request.form["fullname"]
    email = request.form["email"]
    phone = request.form["phone"]
    username = request.form["username"]

    password = generate_password_hash(
        request.form["password"],
        method="pbkdf2:sha256"
    )

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    try:

        cursor.execute(
            "INSERT INTO USER (FullName, Email, Phone) VALUES (?, ?, ?)",
            (fullname, email, phone)
        )

        user_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO ACCOUNT_CREDENTIALS (UserID, Username, PasswordHash) VALUES (?, ?, ?)",
            (user_id, username, password)
        )

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return render_template("index.html", error="Username already exists!")

    conn.close()

    return redirect(url_for("login_page"))

# ==============================
# LOGIN
# ==============================

@app.route("/login", methods=["POST"])
def login():

    username = request.form["username"]
    password = request.form["password"]

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT PasswordHash, UserID FROM ACCOUNT_CREDENTIALS WHERE Username=?",
        (username,)
    )

    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[0], password):

        session["user"] = username
        session["user_id"] = user[1]

        return redirect(url_for("home"))

    return render_template("login.html", error="Invalid Credentials")

# ==============================
# ADMIN LOGIN
# ==============================

@app.route("/admin_login")
def admin_login():
    return render_template("admin_login.html")

@app.route("/admin_login_verify", methods=["POST"])
def admin_login_verify():

    username = request.form["username"]
    password = request.form["password"]

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM ADMIN WHERE Username=? AND PasswordHash=?",
        (username, password)
    )

    admin = cursor.fetchone()
    conn.close()

    if admin:
        session["admin"] = username
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html", error="Invalid admin credentials")

# ==============================
# ADMIN DASHBOARD
# ==============================

@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM LOST_ITEMS WHERE Status NOT IN ('Returned','Expired')")
    total_lost = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM FOUND_ITEMS")
    total_found = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM LOST_ITEMS WHERE Status='Returned'")
    returned_items = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM CLAIMS WHERE Status='Pending'")
    pending_claims = cursor.fetchone()[0]

    # =============================
    # FETCH LOST ITEMS
    # =============================

    cursor.execute("""
    SELECT LostID, ItemName, Category, Brand, Color, Status
    FROM LOST_ITEMS
    WHERE Status NOT IN ('Returned','Expired')
    """)

    lost_items = cursor.fetchall()

    # =============================
    # FETCH CLAIMS
    # =============================

    cursor.execute("""
    SELECT CLAIMS.ClaimID,
    FOUND_ITEMS.ItemName,
    CLAIMS.ClaimantName,
    CLAIMS.ClaimantEmail,
    CLAIMS.ClaimantPhone,
    CLAIMS.Status

    FROM CLAIMS
    JOIN FOUND_ITEMS
    ON CLAIMS.FoundID = FOUND_ITEMS.FoundID

    WHERE CLAIMS.Status='Pending'
    """)

    claims = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        claims=claims,
        lost_items=lost_items,
        total_lost=total_lost,
        total_found=total_found,
        returned_items=returned_items,
        pending_claims=pending_claims
    )

@app.route("/mark_returned/<int:lost_id>")
def mark_returned(lost_id):

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE LOST_ITEMS SET Status='Returned' WHERE LostID=?",
        (lost_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/mark_expired/<int:lost_id>")
def mark_expired(lost_id):

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE LOST_ITEMS SET Status='Expired' WHERE LostID=?",
        (lost_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/approve_claim/<int:claim_id>")
def approve_claim(claim_id):

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    # Get claim details
    cursor.execute("""
        SELECT FoundID, ClaimantEmail
        FROM CLAIMS
        WHERE ClaimID=?
    """, (claim_id,))

    result = cursor.fetchone()

    if result:

        found_id = result[0]
        claimant_email = result[1]

        # Approve claim
        cursor.execute(
            "UPDATE CLAIMS SET Status='Approved' WHERE ClaimID=?",
            (claim_id,)
        )

        # Delete the item (item returned)
        cursor.execute("SELECT ImagePath FROM FOUND_ITEMS WHERE FoundID=?", (found_id,))
        image = cursor.fetchone()

        if image:
            delete_image(image[0])

        cursor.execute("DELETE FROM FOUND_ITEMS WHERE FoundID=?", (found_id,))

        # Remove all claims for this item
        cursor.execute(
            "DELETE FROM CLAIMS WHERE FoundID=?",
            (found_id,)
        )

        # Send approval email
        msg = Message(
            "Claim Approved - Lost & Found System",
            recipients=[claimant_email]
        )

        msg.body = """
Good news!

Your claim for the lost item has been APPROVED by the administrator.

You may now collect the item from the location where it was kept.

Thank you for using the Smart Lost & Found System.
"""

        mail.send(msg)

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/reject_claim/<int:claim_id>")
def reject_claim(claim_id):

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    # Get claimant email
    cursor.execute("""
        SELECT ClaimantEmail
        FROM CLAIMS
        WHERE ClaimID=?
    """, (claim_id,))

    result = cursor.fetchone()

    if result:

        claimant_email = result[0]

        # Update status
        cursor.execute(
            "UPDATE CLAIMS SET Status='Rejected' WHERE ClaimID=?",
            (claim_id,)
        )

        # Send rejection email
        msg = Message(
            "Claim Rejected - Lost & Found System",
            recipients=[claimant_email]
        )

        msg.body = """
Hello,

We are sorry to inform you that your claim for the lost item has been REJECTED by the administrator.

This may happen if the provided details did not match the item.

If you believe this is a mistake, please contact the Lost & Found office.

Thank you.
"""

        mail.send(msg)

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin_logout")
def admin_logout():

    session.pop("admin", None)

    return redirect(url_for("admin_login"))

# ==============================
# CLAIM ITEM
# ==============================

@app.route("/claim_item/<int:found_id>", methods=["GET","POST"])
def claim_item(found_id):

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        message = request.form["message"]

        conn = sqlite3.connect("lost_found.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO CLAIMS
            (FoundID, ClaimantName, ClaimantEmail, ClaimantPhone, ClaimMessage)
            VALUES (?, ?, ?, ?, ?)
        """,(found_id,name,email,phone,message))

        conn.commit()
        conn.close()

        return render_template("claim_item.html", success="Claim submitted successfully!")

    return render_template("claim_item.html", found_id=found_id)

# ==============================
# FORGOT PASSWORD
# ==============================

@app.route("/forgot_password")
def forgot_password():
    return render_template("forgot_password.html")

@app.route("/send_otp", methods=["POST"])
def send_otp():

    username = request.form["username"]

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT USER.Email
        FROM USER
        JOIN ACCOUNT_CREDENTIALS
        ON USER.UserID = ACCOUNT_CREDENTIALS.UserID
        WHERE ACCOUNT_CREDENTIALS.Username=?
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return render_template("forgot_password.html", error="Username not found!")

    email = user[0]
    otp = str(random.randint(100000, 999999))

    session["reset_otp"] = otp
    session["reset_user"] = username

    msg = Message("Password Reset OTP", recipients=[email])
    msg.body = f"Your OTP for password reset is: {otp}"

    mail.send(msg)

    return render_template("verify_otp.html")

# ==============================
# VERIFY OTP
# ==============================

@app.route("/verify_otp", methods=["POST"])
def verify_otp():

    entered_otp = request.form["otp"]
    new_password = request.form["new_password"]
    confirm_password = request.form["confirm_password"]

    if entered_otp != session.get("reset_otp"):
        return render_template("verify_otp.html", error="Invalid OTP!")

    if new_password != confirm_password:
        return render_template("verify_otp.html", error="Passwords do not match!")

    username = session.get("reset_user")

    hashed_password = generate_password_hash(new_password, method="pbkdf2:sha256")

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE ACCOUNT_CREDENTIALS SET PasswordHash=? WHERE Username=?",
        (hashed_password, username)
    )

    conn.commit()
    conn.close()

    session.pop("reset_otp", None)
    session.pop("reset_user", None)

    return render_template("login.html", success="Password reset successfully!")

# ==============================
# LOST ITEM
# ==============================

@app.route("/lost_form", methods=["GET", "POST"])
def lost_form():

    if "user" not in session:
        return redirect(url_for("login_page"))

    if request.method == "POST":

        image = request.files.get("image")
        image_path = None

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image_path = filename

        conn = sqlite3.connect("lost_found.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO LOST_ITEMS
            (UserID, ItemName, Category, Brand, Color,
            IdentificationMarks, LostDate, LostTime,
            LastSeenLocation, ImagePath, AdditionalDetails)

            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

            session["user_id"],
            request.form["item_name"],
            request.form["category"],
            request.form["brand"],
            request.form["color"],
            request.form["identification_marks"],
            request.form["lost_date"],
            request.form["lost_time"],
            request.form["last_seen_location"],
            image_path,
            request.form["additional_details"]
        ))

        conn.commit()
        conn.close()

        return render_template("lost_form.html", success="Lost item reported successfully!")

    return render_template("lost_form.html")

# ==============================
# FOUND ITEM + MATCHING
# ==============================

@app.route("/found_form", methods=["GET", "POST"])
def found_form():

    if "user" not in session:
        return redirect(url_for("login_page"))

    if request.method == "POST":

        image = request.files.get("image")
        image_path = None

        if image and image.filename != "":
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            image_path = filename

        item_name = request.form["item_name"]
        category = request.form["category"]
        brand = request.form["brand"]
        color = request.form["color"]

        conn = sqlite3.connect("lost_found.db")
        cursor = conn.cursor()

        # Insert Found Item
        cursor.execute("""
        INSERT INTO FOUND_ITEMS
        (UserID, ItemName, Category, Brand, Color,
        IdentificationMarks, FoundDate, FoundTime,
        FoundLocation, KeptLocation, ImagePath, AdditionalNotes)

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (

        session["user_id"],
        item_name,
        category,
        brand,
        color,
        request.form["identification_marks"],
        request.form["found_date"],
        request.form["found_time"],
        request.form["found_location"],
        request.form["kept_at"],
        image_path,
        request.form["additional_notes"]

        ))

        found_id = cursor.lastrowid

        # ======================
        # MATCHING LOGIC
        # ======================

        cursor.execute("""
        SELECT LostID, USER.Email
        FROM LOST_ITEMS
        JOIN USER ON LOST_ITEMS.UserID = USER.UserID
        WHERE ItemName=? 
        AND Category=? 
        AND Brand=? 
        AND Color=? 
        AND Status='Pending'
        """,(item_name, category, brand, color))

        matches = cursor.fetchall()

        for lost_id, email in matches:

            # Insert match record
            cursor.execute("""
            INSERT INTO MATCHED_ITEMS (LostID, FoundID, MatchDate)
            VALUES (?, ?, DATE('now'))
            """,(lost_id, found_id))

            # Update statuses
            cursor.execute(
            "UPDATE LOST_ITEMS SET Status='Matched' WHERE LostID=?",
            (lost_id,)
            )

            cursor.execute(
            "UPDATE FOUND_ITEMS SET Status='Matched' WHERE FoundID=?",
            (found_id,)
            )

            # Email notification
            msg = Message(
            "Lost Item Match Found!",
            recipients=[email]
            )

            msg.body = f"""
Good news!

A found item matching your lost item has been reported.

Item: {item_name}

Please login to the system.
"""

            mail.send(msg)

        conn.commit()
        conn.close()

        return render_template(
            "found_form.html",
            success="Found item reported successfully!"
        )

    return render_template("found_form.html")

# ==============================
# VIEW ITEMS
# ==============================

@app.route("/view_items")
def view_items():

    if "user" not in session:
        return redirect(url_for("login_page"))

    conn = sqlite3.connect("lost_found.db")
    cursor = conn.cursor()

    # FETCH MATCHED ITEMS
    cursor.execute("""
        SELECT 
            LOST_ITEMS.ItemName,
            LOST_ITEMS.Category,
            FOUND_ITEMS.FoundLocation,
            FOUND_ITEMS.FoundDate,
            FOUND_ITEMS.ImagePath
        FROM MATCHED_ITEMS
        JOIN LOST_ITEMS ON MATCHED_ITEMS.LostID = LOST_ITEMS.LostID
        JOIN FOUND_ITEMS ON MATCHED_ITEMS.FoundID = FOUND_ITEMS.FoundID
        ORDER BY MATCHED_ITEMS.MatchDate DESC
    """)
    matched_items = cursor.fetchall()

    # FETCH FOUND ITEMS
    cursor.execute("""
        SELECT 
            FoundID,
            ItemName,
            Category,
            FoundLocation,
            FoundDate,
            Status,
            ImagePath
        FROM FOUND_ITEMS
        ORDER BY FoundDate DESC
    """)
    found_items = cursor.fetchall()

    conn.close()

    return render_template(
        "view_items.html",
        matched_items=matched_items,
        found_items=found_items
    )

# ==============================
# LOGOUT
# ==============================

@app.route("/logout")
def logout():

    session.pop("user", None)
    session.pop("user_id", None)

    return redirect(url_for("login_page"))

# ==============================
# RUN
# ==============================

if __name__ == "__main__":
    app.run(debug=True)