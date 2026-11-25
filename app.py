
import os
import csv
import uuid
import json
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename

from recommender import calculate_match


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "internmatch-development-secret-key"
)

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

os.makedirs(app.instance_path, exist_ok=True)

CERTIFICATE_FOLDER = os.path.join(
    app.instance_path, "certificates"
)

RESUME_FOLDER = os.path.join(
    app.instance_path, "applications"
)

DATABASE = os.path.join(
    app.instance_path, "internmatch.db"
)

os.makedirs(CERTIFICATE_FOLDER, exist_ok=True)
os.makedirs(RESUME_FOLDER, exist_ok=True)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS student_profiles (
            user_id INTEGER PRIMARY KEY,
            profile_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            internship_id TEXT,
            internship_title TEXT NOT NULL,
            company TEXT NOT NULL,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL,
            linkedin TEXT NOT NULL,
            phone TEXT,
            resume_filename TEXT NOT NULL,
            application_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


init_db()


# --------------------------------------------------
# LOGIN PROTECTION
# --------------------------------------------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


def get_current_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    connection = get_db_connection()

    user = connection.execute(
        "SELECT id, full_name, email FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    connection.close()

    return dict(user) if user else None


# --------------------------------------------------
# STUDENT PROFILE STORAGE
# --------------------------------------------------

def save_student_profile(user_id, student):
    connection = get_db_connection()

    connection.execute("""
        INSERT INTO student_profiles
        (user_id, profile_json, updated_at)
        VALUES (?, ?, ?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            profile_json = excluded.profile_json,
            updated_at = excluded.updated_at
    """, (
        user_id,
        json.dumps(student),
        datetime.now().strftime("%d-%m-%Y %H:%M")
    ))

    connection.commit()
    connection.close()


def get_student_profile(user_id):
    connection = get_db_connection()

    profile = connection.execute(
        "SELECT profile_json FROM student_profiles WHERE user_id = ?",
        (user_id,)
    ).fetchone()

    connection.close()

    if profile:
        return json.loads(profile["profile_json"])

    return None


# --------------------------------------------------
# INTERNSHIP CSV
# --------------------------------------------------

def load_internships():
    internships = []

    csv_path = os.path.join(
        app.root_path, "internships.csv"
    )

    with open(
        csv_path, "r", newline="", encoding="utf-8-sig"
    ) as file:

        reader = csv.DictReader(file)

        if reader.fieldnames:
            reader.fieldnames = [
                name.strip() for name in reader.fieldnames
            ]

        for row in reader:
            cleaned_row = {
                key.strip(): value.strip() if value else ""
                for key, value in row.items()
                if key is not None
            }

            internships.append(cleaned_row)

    return internships


# --------------------------------------------------
# FILE UPLOAD HELPERS
# --------------------------------------------------

def allowed_file(filename, allowed_extensions):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in allowed_extensions
    )


def save_uploaded_file(file, folder):
    original_name = secure_filename(file.filename)
    extension = original_name.rsplit(".", 1)[1].lower()

    unique_name = f"{uuid.uuid4().hex}.{extension}"

    file.save(os.path.join(folder, unique_name))

    return unique_name


# --------------------------------------------------
# REGISTER
# --------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not full_name or not email or not password:
            flash("Please fill in all the fields.", "danger")
            return redirect(url_for("register"))

        if len(full_name) > 100 or len(email) > 254:
            flash("One or more fields are too long.", "danger")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        password_hash = generate_password_hash(password)

        connection = get_db_connection()

        try:
            connection.execute("""
                INSERT INTO users
                (full_name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                full_name,
                email,
                password_hash,
                datetime.now().strftime("%d-%m-%Y %H:%M")
            ))

            connection.commit()

            user = connection.execute(
                "SELECT id FROM users WHERE email = ?",
                (email,)
            ).fetchone()

            session.clear()
            session["user_id"] = user["id"]

            flash(
                "Account created successfully! Welcome to InternMatch.",
                "success"
            )

            return redirect(url_for("dashboard"))

        except sqlite3.IntegrityError:
            flash(
                "An account with this email already exists.",
                "danger"
            )

        finally:
            connection.close()

    return render_template("register.html")


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password_hash"], password
        ):

            session.clear()
            session["user_id"] = user["id"]

            flash("Login successful!", "success")

            return redirect(url_for("dashboard"))

        flash(
            "Invalid email or password. Please try again.",
            "danger"
        )

    return render_template("login.html")


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@app.route("/logout")
@login_required
def logout():

    session.clear()

    flash("You have been logged out.", "success")

    return redirect(url_for("login"))


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():

    user = get_current_user()

    if not user:
        session.clear()
        return redirect(url_for("login"))

    student = get_student_profile(user["id"])

    connection = get_db_connection()

    applications = connection.execute("""
        SELECT
            internship_title,
            company,
            application_date
        FROM applications
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user["id"],)).fetchall()

    connection.close()

    internships = load_internships()

    return render_template(
        "dashboard.html",
        user=user,
        student=student,
        applications=applications,
        total_applications=len(applications),
        total_internships=len(internships)
    )


# --------------------------------------------------
# HOME / STUDENT PROFILE FORM
# --------------------------------------------------

@app.route("/", methods=["GET", "POST"])
@login_required
def home():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        skills_text = request.form.get(
            "skills", ""
        ).strip()

        interest = request.form.get("interest", "")
        city = request.form.get("city", "")
        mode = request.form.get("mode", "")
        employment_type = request.form.get(
            "employment_type", ""
        )

        phone = request.form.get("phone", "").strip()
        languages = request.form.get(
            "languages", ""
        ).strip()

        degree_status = request.form.get(
            "degree_status", ""
        )

        experience_status = request.form.get(
            "experience_status", ""
        )

        experience_details = request.form.get(
            "experience_details", ""
        ).strip()

        expected_stipend_text = request.form.get(
            "expected_stipend", ""
        ).strip()

        duration_text = request.form.get(
            "duration_months", ""
        ).strip()

        if not full_name or not skills_text or not interest:
            flash(
                "Please complete the required profile fields.",
                "danger"
            )
            return redirect(url_for("home"))

        try:
            expected_stipend = (
                float(expected_stipend_text)
                if expected_stipend_text else None
            )

            duration_months = (
                int(duration_text)
                if duration_text else None
            )

            if expected_stipend is not None and expected_stipend < 0:
                raise ValueError

            if duration_months is not None and duration_months < 1:
                raise ValueError

        except ValueError:
            flash(
                "Please enter a valid stipend and duration.",
                "danger"
            )
            return redirect(url_for("home"))

        skills = [
            skill.strip()
            for skill in skills_text.split(",")
            if skill.strip()
        ]

        certificate = request.files.get("certificate")
        certificate_filename = ""

        if certificate and certificate.filename:

            if not allowed_file(
                certificate.filename,
                {"pdf", "png", "jpg", "jpeg"}
            ):
                flash(
                    "Certificate must be a PDF, PNG or JPG file.",
                    "danger"
                )
                return redirect(url_for("home"))

            certificate_filename = save_uploaded_file(
                certificate, CERTIFICATE_FOLDER
            )

        student = {
            "full_name": full_name,
            "skills": skills,
            "interest": interest,
            "city": city,
            "mode": mode,
            "employment_type": employment_type,
            "expected_stipend": expected_stipend,
            "duration_months": duration_months,
            "phone": phone,
            "languages": languages,
            "degree_status": degree_status,
            "experience_status": experience_status,
            "experience_details": experience_details,
            "certificate_filename": certificate_filename,
            "certificate_status": (
                "Pending Verification"
                if certificate_filename
                else "Not Uploaded"
            )
        }

        save_student_profile(session["user_id"], student)

        session["recommendation_profile"] = student

        internships = load_internships()

        for internship in internships:
            internship["match_score"] = calculate_match(
                student, internship
            )

        internships.sort(
            key=lambda item: item["match_score"],
            reverse=True
        )

        return render_template(
            "results.html",
            internships=internships,
            student=student,
            skills=skills,
            interest=interest,
            city=city
        )

    student = get_student_profile(session["user_id"])

    return render_template(
        "index.html",
        student=student
    )


# --------------------------------------------------
# RECOMMENDATIONS
# --------------------------------------------------

@app.route("/recommendations")
@login_required
def recommendations():

    student = get_student_profile(session["user_id"])

    if not student:
        flash(
            "Please complete your student profile first.",
            "info"
        )
        return redirect(url_for("home"))

    internships = load_internships()

    for internship in internships:
        internship["match_score"] = calculate_match(
            student, internship
        )

    internships.sort(
        key=lambda item: item["match_score"],
        reverse=True
    )

    return render_template(
        "results.html",
        internships=internships,
        student=student,
        skills=student["skills"],
        interest=student["interest"],
        city=student["city"]
    )


# --------------------------------------------------
# APPLY FOR AN INTERNSHIP
# --------------------------------------------------

@app.route("/apply/<internship_id>", methods=["GET", "POST"])
@login_required
def apply(internship_id):

    internships = load_internships()

    internship = next(
        (
            item for item in internships
            if item.get("id") == internship_id
        ),
        None
    )

    if not internship:
        flash("Internship not found.", "danger")
        return redirect(url_for("recommendations"))

    if request.method == "POST":

        full_name = request.form.get(
            "full_name", ""
        ).strip()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        phone = request.form.get("phone", "").strip()

        linkedin = request.form.get(
            "linkedin", ""
        ).strip()

        resume = request.files.get("resume")

        if not full_name or not email or not linkedin:
            flash(
                "Please complete all required application fields.",
                "danger"
            )
            return render_template(
                "application.html",
                internship=internship
            )

        if not resume or not resume.filename:
            flash("Please upload your resume.", "danger")
            return render_template(
                "application.html",
                internship=internship
            )

        if not allowed_file(
            resume.filename,
            {"pdf", "doc", "docx"}
        ):
            flash(
                "Resume must be a PDF, DOC or DOCX file.",
                "danger"
            )
            return render_template(
                "application.html",
                internship=internship
            )

        resume_filename = save_uploaded_file(
            resume, RESUME_FOLDER
        )

        connection = get_db_connection()

        connection.execute("""
            INSERT INTO applications (
                user_id,
                internship_id,
                internship_title,
                company,
                full_name,
                email,
                linkedin,
                phone,
                resume_filename,
                application_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            internship.get("id", ""),
            internship.get("title", ""),
            internship.get("company", ""),
            full_name,
            email,
            linkedin,
            phone,
            resume_filename,
            datetime.now().strftime("%d-%m-%Y %H:%M")
        ))

        connection.commit()
        connection.close()

        return render_template(
            "confirmation.html",
            internship=internship,
            full_name=full_name
        )

    student = get_student_profile(session["user_id"])

    return render_template(
        "application.html",
        internship=internship,
        student=student,
        user=get_current_user()
    )


# --------------------------------------------------
# RUN THE APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
