from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Dict

app = FastAPI(
    title="AI Subsidy Assistant",
    description="Gate 1 MVP for subsidy eligibility and explainable scoring",
    version="0.1.0"
)


# -----------------------------
# MODELS
# -----------------------------
class EvaluateRequest(BaseModel):
    farm_name: str = Field(..., example="AgroFarm KZ")
    direction: str = Field(..., example="meat")  # meat | milk
    origin: str = Field(..., example="domestic")  # domestic | cis | far_abroad
    animal_category: str = Field(..., example="heifer")  # heifer | pregnant_heifer
    age_months: int = Field(..., ge=0, le=60, example=15)
    quantity: int = Field(..., ge=1, example=20)
    months_since_purchase: int = Field(..., ge=0, le=36, example=3)

    has_accounting_number: bool = True
    has_agri_land: bool = True
    registered_in_iszh_ibspr: bool = True
    agrees_two_year_commitment: bool = True

    requested_amount: int = Field(0, ge=0, example=5200000)


class ChatRequest(BaseModel):
    applicant_name: str
    total_score: float
    recommendation: str
    reasons: List[str]
    question: str


# -----------------------------
# LOGIC
# -----------------------------
def clamp_score(x: float) -> float:
    return max(0.0, min(10.0, x))


def get_subsidy_rate(direction: str, origin: str) -> int:
    rates = {
        "meat": {
            "domestic": 260000,
            "cis": 390000,
            "far_abroad": 525000,
        },
        "milk": {
            "domestic": 350000,
            "cis": 390000,
            "far_abroad": 700000,
        },
    }
    return rates[direction][origin]


def check_age_valid(category: str, age_months: int) -> bool:
    # Ð¢ÐµÐ»ÐºÐ¸: 6-18 Ð¼ÐµÑ
    # ÐÐµÑÐµÐ»Ð¸: 13-26 Ð¼ÐµÑ
    if category == "heifer":
        return 6 <= age_months <= 18
    if category == "pregnant_heifer":
        return 13 <= age_months <= 26
    return False


def evaluate_application(data: EvaluateRequest) -> Dict:
    reasons = []
    warnings = []
    score = 10.0
    eligible = True

    if not data.has_accounting_number:
        eligible = False
        score -= 3
        reasons.append("ÐÐµÑ ÑÑÐµÑÐ½Ð¾Ð³Ð¾ Ð½Ð¾Ð¼ÐµÑÐ° ÑÐ¾Ð·ÑÐ¹ÑÑÐ²Ð°.")

    if not data.has_agri_land:
        eligible = False
        score -= 2
        reasons.append("ÐÐµÑ Ð¿Ð¾Ð´ÑÐ²ÐµÑÐ¶Ð´ÐµÐ½Ð¸Ñ Ð½Ð°Ð»Ð¸ÑÐ¸Ñ Ð·ÐµÐ¼ÐµÐ»Ñ ÑÐµÐ»ÑÑÐ¾Ð·Ð½Ð°Ð·Ð½Ð°ÑÐµÐ½Ð¸Ñ.")

    if not data.registered_in_iszh_ibspr:
        eligible = False
        score -= 3
        reasons.append("ÐÑÐ¸Ð¾Ð±ÑÐµÑÐµÐ½Ð½Ð¾Ðµ Ð¿Ð¾Ð³Ð¾Ð»Ð¾Ð²ÑÐµ Ð½Ðµ Ð·Ð°ÑÐµÐ³Ð¸ÑÑÑÐ¸ÑÐ¾Ð²Ð°Ð½Ð¾ Ð² ÐÐ¡Ð Ð¸ ÐÐÐ¡ÐÐ .")

    if not check_age_valid(data.animal_category, data.age_months):
        eligible = False
        score -= 3
        reasons.append("ÐÐ¾Ð·ÑÐ°ÑÑ Ð¶Ð¸Ð²Ð¾ÑÐ½ÑÑ Ð½Ðµ ÑÐ¾Ð¾ÑÐ²ÐµÑÑÑÐ²ÑÐµÑ ÐºÑÐ¸ÑÐµÑÐ¸ÑÐ¼ Ð½Ð°Ð¿ÑÐ°Ð²Ð»ÐµÐ½Ð¸Ñ.")

    if data.months_since_purchase > 12:
        eligible = False
        score -= 2
        reasons.append("Ð¡ÑÐ¾Ðº Ð¿Ð¾Ð´Ð°ÑÐ¸ Ð¿ÑÐµÐ²ÑÑÐ°ÐµÑ 12 Ð¼ÐµÑÑÑÐµÐ² Ñ Ð¼Ð¾Ð¼ÐµÐ½ÑÐ° Ð¿ÑÐ¸Ð¾Ð±ÑÐµÑÐµÐ½Ð¸Ñ.")

    if not data.agrees_two_year_commitment:
        eligible = False
        score -= 2
        reasons.append("ÐÐµÑ Ð¾Ð±ÑÐ·Ð°ÑÐµÐ»ÑÑÑÐ²Ð° ÑÐµÐ»ÐµÐ²Ð¾Ð³Ð¾ Ð¸ÑÐ¿Ð¾Ð»ÑÐ·Ð¾Ð²Ð°Ð½Ð¸Ñ Ð½Ðµ Ð¼ÐµÐ½ÐµÐµ Ð´Ð²ÑÑ Ð»ÐµÑ.")

    if data.quantity > 300:
        warnings.append("ÐÑÐµÐ½Ñ ÐºÑÑÐ¿Ð½Ð°Ñ Ð·Ð°ÑÐ²ÐºÐ° â ÑÐµÐºÐ¾Ð¼ÐµÐ½Ð´ÑÐµÑÑÑ ÑÑÑÐ½Ð°Ñ Ð¿ÑÐ¾Ð²ÐµÑÐºÐ°.")
        score -= 0.5

    rate_per_head = get_subsidy_rate(data.direction, data.origin)
    estimated_subsidy = rate_per_head * data.quantity

    if data.requested_amount > estimated_subsidy:
        warnings.append("ÐÐ°Ð¿ÑÐ¾ÑÐµÐ½Ð½Ð°Ñ ÑÑÐ¼Ð¼Ð° Ð²ÑÑÐµ ÑÐ°ÑÑÐµÑÐ½Ð¾Ð³Ð¾ Ð½Ð¾ÑÐ¼Ð°ÑÐ¸Ð²Ð°.")
        score -= 0.5

    score = clamp_score(score)

    if eligible and score >= 8:
        recommendation = "eligible"
    elif eligible:
        recommendation = "needs_review"
    else:
        recommendation = "not_eligible"

    if not reasons:
        reasons.append("ÐÐ°Ð·Ð¾Ð²ÑÐµ ÐºÑÐ¸ÑÐµÑÐ¸Ð¸ Ð¿Ð¾ Ð²Ð²ÐµÐ´ÐµÐ½Ð½ÑÐ¼ Ð´Ð°Ð½Ð½ÑÐ¼ ÑÐ¾Ð±Ð»ÑÐ´ÐµÐ½Ñ.")

    explanation = [
        f"ÐÐ¾ÑÐ¼Ð°ÑÐ¸Ð² Ð½Ð° 1 Ð³Ð¾Ð»Ð¾Ð²Ñ: {rate_per_head} ÑÐµÐ½Ð³Ðµ.",
        f"ÐÑÐµÐ½Ð¾ÑÐ½Ð°Ñ ÑÑÐ¼Ð¼Ð° ÑÑÐ±ÑÐ¸Ð´Ð¸Ð¸: {estimated_subsidy} ÑÐµÐ½Ð³Ðµ.",
        f"Recommendation: {recommendation}.",
    ] + reasons

    return {
        "farm_name": data.farm_name,
        "total_score": round(score, 2),
        "recommendation": recommendation,
        "rate_per_head": rate_per_head,
        "estimated_subsidy": estimated_subsidy,
        "reasons": reasons,
        "warnings": warnings,
        "explanation": explanation,
    }


def chat_answer(payload: ChatRequest) -> str:
    q = payload.question.lower()

    if "Ð¿Ð¾ÑÐµÐ¼Ñ" in q or "why" in q:
        joined = " ".join(payload.reasons)
        return (
            f"ÐÐ°ÑÐ²ÐºÐ° {payload.applicant_name} Ð¿Ð¾Ð»ÑÑÐ¸Ð»Ð° recommendation "
            f"'{payload.recommendation}', Ð¿Ð¾ÑÐ¾Ð¼Ñ ÑÑÐ¾: {joined}"
        )

    if "score" in q or "Ð±Ð°Ð»Ð»" in q:
        return (
            f"ÐÑÐ¾Ð³Ð¾Ð²ÑÐ¹ score Ð´Ð»Ñ {payload.applicant_name}: {payload.total_score} Ð¸Ð· 10. "
            f"Recommendation: {payload.recommendation}."
        )

    if "ÑÑÐ¾ ÑÐ»ÑÑÑÐ¸ÑÑ" in q or "improve" in q:
        return (
            "ÐÐ»Ñ ÑÐ»ÑÑÑÐµÐ½Ð¸Ñ Ð¾ÑÐµÐ½ÐºÐ¸ ÑÑÐ¾Ð¸Ñ Ð¿ÑÐ¾Ð²ÐµÑÐ¸ÑÑ Ð²ÑÐ¿Ð¾Ð»Ð½ÐµÐ½Ð¸Ðµ ÑÐ¾ÑÐ¼Ð°Ð»ÑÐ½ÑÑ ÐºÑÐ¸ÑÐµÑÐ¸ÐµÐ², "
            "ÐºÐ¾ÑÑÐµÐºÑÐ½Ð¾ÑÑÑ ÑÐµÐ³Ð¸ÑÑÑÐ°ÑÐ¸Ð¸ Ð² ÐÐ¡Ð/ÐÐÐ¡ÐÐ , Ð´Ð¾Ð¿ÑÑÑÐ¸Ð¼ÑÐ¹ Ð²Ð¾Ð·ÑÐ°ÑÑ Ð¶Ð¸Ð²Ð¾ÑÐ½ÑÑ "
            "Ð¸ ÑÐ¾Ð¾ÑÐ²ÐµÑÑÑÐ²Ð¸Ðµ Ð·Ð°Ð¿ÑÐ¾ÑÐµÐ½Ð½Ð¾Ð¹ ÑÑÐ¼Ð¼Ñ Ð½Ð¾ÑÐ¼Ð°ÑÐ¸Ð²Ñ."
        )

    return (
        "Ð¯ Ð¼Ð¾Ð³Ñ Ð¾Ð±ÑÑÑÐ½Ð¸ÑÑ ÑÐµÐ·ÑÐ»ÑÑÐ°Ñ, Ð½Ð°Ð·Ð²Ð°ÑÑ score, recommendation "
        "Ð¸Ð»Ð¸ Ð¿Ð¾Ð´ÑÐºÐ°Ð·Ð°ÑÑ, ÑÑÐ¾ ÑÐ»ÑÑÑÐ¸ÑÑ Ð² Ð·Ð°ÑÐ²ÐºÐµ."
    )


# -----------------------------
# ROUTES
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/evaluate")
def evaluate(req: EvaluateRequest):
    return evaluate_application(req)


@app.post("/chat")
def chat(req: ChatRequest):
    return {"answer": chat_answer(req)}