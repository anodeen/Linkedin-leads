from dataclasses import dataclass

from .models import InboundLead


@dataclass(slots=True)
class ICPRuleConfig:
    title_keywords: tuple[str, ...] = ("head of sales", "vp sales", "sales director")
    company_keywords: tuple[str, ...] = ("b2b", "saas")
    min_score: int = 0
    max_score: int = 100
    title_match_points: int = 35
    company_match_points: int = 25
    linkedin_profile_points: int = 15
    completeness_points: int = 25


@dataclass(slots=True)
class ScoreBreakdownItem:
    rule: str
    points: int
    matched: bool
    reason: str


@dataclass(slots=True)
class LeadScoreResult:
    score: int
    breakdown: list[ScoreBreakdownItem]


class RuleBasedScorer:
    """Deterministic ICP scorer for PRD Step 2."""

    def __init__(self, config: ICPRuleConfig | None = None) -> None:
        self.config = config or ICPRuleConfig()

    def score_lead(self, lead: InboundLead) -> LeadScoreResult:
        breakdown: list[ScoreBreakdownItem] = []

        title = lead.title.lower()
        title_match = any(keyword in title for keyword in self.config.title_keywords)
        breakdown.append(
            ScoreBreakdownItem(
                rule="title_keyword_match",
                points=self.config.title_match_points if title_match else 0,
                matched=title_match,
                reason=(
                    "Title matched ICP seniority/function keywords"
                    if title_match
                    else "No ICP title keywords matched"
                ),
            )
        )

        company = lead.company.lower()
        company_match = any(keyword in company for keyword in self.config.company_keywords)
        breakdown.append(
            ScoreBreakdownItem(
                rule="company_keyword_match",
                points=self.config.company_match_points if company_match else 0,
                matched=company_match,
                reason=(
                    "Company matched ICP industry keywords"
                    if company_match
                    else "No ICP company keywords matched"
                ),
            )
        )

        linkedin_match = "linkedin.com" in lead.profile_url.lower()
        breakdown.append(
            ScoreBreakdownItem(
                rule="linkedin_profile_detected",
                points=self.config.linkedin_profile_points if linkedin_match else 0,
                matched=linkedin_match,
                reason=(
                    "LinkedIn profile URL is present"
                    if linkedin_match
                    else "LinkedIn profile URL not detected"
                ),
            )
        )

        complete = all(
            [
                bool(lead.full_name.strip()),
                bool(lead.title.strip()),
                bool(lead.company.strip()),
                bool(lead.profile_url.strip()),
            ]
        )
        breakdown.append(
            ScoreBreakdownItem(
                rule="record_completeness",
                points=self.config.completeness_points if complete else 0,
                matched=complete,
                reason="Lead record has complete core fields"
                if complete
                else "Lead record missing one or more core fields",
            )
        )

        raw_score = sum(item.points for item in breakdown)
        capped_score = max(self.config.min_score, min(raw_score, self.config.max_score))
        return LeadScoreResult(score=capped_score, breakdown=breakdown)
