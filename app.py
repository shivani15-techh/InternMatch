
from flask import Flask, render_template, request
from recommender import calculate_match
import csv

app = Flask(__name__)


# Read internship data from CSV
def load_internships():

    internships = []

    with open("internships.csv", "r", newline="", encoding="utf-8") as file:

        reader = csv.DictReader(file)

        for row in reader:
            internships.append(row)

    return internships


@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        # Collect candidate preferences
        skills = request.form.get("skills", "")
        interest = request.form.get("interest", "")
        city = request.form.get("city", "")
        mode = request.form.get("mode", "")

        # Convert skills into a list
        student_skills = [
            skill.strip().lower()
            for skill in skills.split(",")
            if skill.strip()
        ]

        # Load internships from CSV
        internships = load_internships()

        # Calculate match scores
        for internship in internships:

            score = calculate_match(
                student_skills,
                interest,
                city,
                mode,
                internship
            )

            internship["match_score"] = score

        # Sort internships from highest to lowest score
        internships.sort(
            key=lambda x: x["match_score"],
            reverse=True
        )

        # Display results
        return render_template(
            "results.html",
            skills=skills,
            interest=interest,
            city=city,
            internships=internships
        )

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
