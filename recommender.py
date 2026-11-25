
def clean(value):
    """Convert text into a consistent lowercase format."""
    return str(value or "").strip().lower()


def calculate_match(student, internship):
    """
    Calculate how well a student matches an internship.

    Matching factors:
    Skills          - 40%
    Area of interest - 20%
    City            - 10%
    Work mode       - 5%
    Employment type - 10%
    Expected stipend - 10%
    Duration        - 5%
    """

    score = 0
    total_weight = 0

    # ---------------------------------------------
    # 1. SKILLS MATCH (40%)
    # ---------------------------------------------

    required_skills = {
        clean(skill)
        for skill in internship.get("skills", "").split(",")
        if clean(skill)
    }

    student_skills = {
        clean(skill)
        for skill in student.get("skills", [])
        if clean(skill)
    }

    if required_skills:

        matched_skills = student_skills.intersection(
            required_skills
        )

        skill_score = (
            len(matched_skills) / len(required_skills)
        ) * 40

        score += skill_score
        total_weight += 40

    # ---------------------------------------------
    # 2. AREA OF INTEREST MATCH (20%)
    # ---------------------------------------------

    internship_interest = clean(
        internship.get("interest", "")
    )

    student_interest = clean(
        student.get("interest", "")
    )

    if internship_interest:

        total_weight += 20

        if student_interest == internship_interest:
            score += 20

    # ---------------------------------------------
    # 3. CITY MATCH (10%)
    # ---------------------------------------------

    internship_city = clean(
        internship.get("city", "")
    )

    student_city = clean(
        student.get("city", "")
    )

    if internship_city:

        total_weight += 10

        if student_city == internship_city:
            score += 10

    # ---------------------------------------------
    # 4. WORK MODE MATCH (5%)
    # ---------------------------------------------

    internship_mode = clean(
        internship.get("mode", "")
    )

    student_mode = clean(
        student.get("mode", "")
    )

    if internship_mode:

        total_weight += 5

        if student_mode == internship_mode:
            score += 5

    # ---------------------------------------------
    # 5. EMPLOYMENT TYPE MATCH (10%)
    # ---------------------------------------------

    internship_type = clean(
        internship.get("employment_type", "")
    )

    student_type = clean(
        student.get("employment_type", "")
    )

    if internship_type:

        total_weight += 10

        if student_type == internship_type:
            score += 10

    # ---------------------------------------------
    # 6. STIPEND MATCH (10%)
    # ---------------------------------------------

    stipend_min = internship.get("stipend_min", "")
    stipend_max = internship.get("stipend_max", "")

    expected_stipend = student.get("expected_stipend")

    if expected_stipend is not None and stipend_max:

        try:

            minimum = float(stipend_min or 0)
            maximum = float(stipend_max)

            total_weight += 10

            if minimum <= float(expected_stipend) <= maximum:
                score += 10

        except (ValueError, TypeError):
            pass

    # ---------------------------------------------
    # 7. DURATION MATCH (5%)
    # ---------------------------------------------

    internship_duration = internship.get(
        "duration_months", ""
    )

    student_duration = student.get("duration_months")

    if student_duration is not None and internship_duration:

        try:

            available_duration = int(internship_duration)

            total_weight += 5

            if available_duration >= int(student_duration):
                score += 5

        except (ValueError, TypeError):
            pass

    # ---------------------------------------------
    # FINAL MATCH SCORE
    # ---------------------------------------------

    if total_weight == 0:
        return 0

    final_score = (score / total_weight) * 100

    return round(final_score)
