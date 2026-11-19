def calculate_match(
    student_skills,
    student_interest,
    student_city,
    student_mode,
    internship
):

    score = 0

    # -------------------------
    # 1. Skill Match - 50 points
    # -------------------------

    required_skills = [
        skill.strip().lower()
        for skill in internship["skills"].split(",")
    ]

    if required_skills:

        matched_skills = 0

        for skill in student_skills:
            if skill in required_skills:
                matched_skills += 1

        skill_score = (
            matched_skills / len(required_skills)
        ) * 50

        score += skill_score

    # -------------------------
    # 2. Interest Match - 30 points
    # -------------------------

    if (
        student_interest.lower()
        == internship["interest"].lower()
    ):
        score += 30

    # -------------------------
    # 3. City Match - 10 points
    # -------------------------

    if (
        student_city.lower()
        == internship["city"].lower()
    ):
        score += 10

    # -------------------------
    # 4. Work Mode Match - 10 points
    # -------------------------

    if (
        student_mode.lower()
        == internship["mode"].lower()
    ):
        score += 10

    return round(score)