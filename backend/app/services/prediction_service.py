from app.models.application import Application


def run_baseline_prediction(application: Application) -> dict:
    """
    Stable baseline prediction engine.

    This is not the final advanced ML model.
    It is a deployable baseline model so the project prediction workflow works now.
    Later, we can replace this with scikit-learn model loading/training.
    """

    monthly_income = application.monthly_income or 0
    age = application.age or 0

    score = 0
    reasons = []

    if monthly_income >= 80000:
        score += 45
        reasons.append("Monthly income is very strong.")
    elif monthly_income >= 50000:
        score += 35
        reasons.append("Monthly income is strong.")
    elif monthly_income >= 30000:
        score += 25
        reasons.append("Monthly income is moderate.")
    elif monthly_income >= 15000:
        score += 12
        reasons.append("Monthly income is low.")
    else:
        score += 5
        reasons.append("Monthly income is very low.")

    if 25 <= age <= 55:
        score += 25
        reasons.append("Applicant age is within stable working range.")
    elif 18 <= age < 25:
        score += 12
        reasons.append("Applicant is young; manual review recommended.")
    elif 55 < age <= 70:
        score += 10
        reasons.append("Applicant age is higher; manual review recommended.")
    else:
        score += 5
        reasons.append("Applicant age needs careful review.")

    if application.occupation:
        score += 15
        reasons.append("Occupation information is provided.")
    else:
        reasons.append("Occupation information is missing.")

    if application.phone and application.email and application.address:
        score += 15
        reasons.append("Contact information is complete.")
    else:
        reasons.append("Some contact information is missing.")

    if score >= 75:
        prediction_result = "recommended_approval"
        risk_level = "low"
        confidence_score = min(0.95, score / 100)

    elif score >= 50:
        prediction_result = "manual_review"
        risk_level = "medium"
        confidence_score = min(0.85, score / 100)

    else:
        prediction_result = "not_recommended"
        risk_level = "high"
        confidence_score = max(0.50, score / 100)

    return {
        "prediction_result": prediction_result,
        "risk_level": risk_level,
        "confidence_score": round(confidence_score, 2),
        "reason": " ".join(reasons),
    }
