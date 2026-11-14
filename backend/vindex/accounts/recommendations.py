from fastapi import APIRouter, Query, Request
from sqlalchemy import func, or_, select

from vindex.accounts.matching import contains, unique
from vindex.accounts.models import Profile
from vindex.accounts.schemas import ProfileInput, RecommendationsOut
from vindex.accounts.security import principal, rate_limit
from vindex.db import Job, Observation, Session

router = APIRouter(prefix="/api/v1/me", tags=["Private recommendations"])
CANDIDATE_LIMIT = 1000


@router.get("/recommendations", response_model=RecommendationsOut)
def recommendations(
    request: Request, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)
):
    with Session() as session:
        user = principal(request, session)
        rate_limit(f"recommendations:{user.id}", 30)
        saved = session.get(Profile, user.id)
        profile = ProfileInput.model_validate(saved.data if saved else {})
        titles = unique(profile.desired_titles)
        skills = unique(profile.skills)
        output = {
            "items": [],
            "total_candidates": 0,
            "candidates_ranked": 0,
            "candidate_limit": CANDIDATE_LIMIT,
            "truncated": False,
            "limit": limit,
            "offset": offset,
            "needs_preferences": not bool(titles or skills),
        }
        if not titles and not skills:
            return output
        # Only professionally relevant terms are used. Names, email, bio, age and other
        # personal details never influence ranking or external service requests.
        terms = unique(titles + skills)
        conditions = [
            or_(
                Job.data["title"].as_string().icontains(term, autoescape=True),
                Job.data["description"].as_string().icontains(term, autoescape=True),
            )
            for term in terms
        ]
        active = select(Observation.job_id).where(Observation.status == "open")
        stmt = select(Job).where(Job.id.in_(active), or_(*conditions))
        if profile.preferred_locations:
            stmt = stmt.where(
                or_(
                    *(
                        Job.data["location"].as_string().icontains(location, autoescape=True)
                        for location in unique(profile.preferred_locations)
                    )
                )
            )
        if profile.remote_only:
            stmt = stmt.where(func.lower(Job.data["remote_status"].as_string()) == "remote")
        total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        candidates = list(session.scalars(stmt.order_by(Job.id.desc()).limit(CANDIDATE_LIMIT)))
        ranked = []
        for job in candidates:
            title = job.data["title"]
            body = title + "\n" + job.data["description"]
            matched_titles = [term for term in titles if contains(title, term)]
            matched_skills = [term for term in skills if contains(body, term)]
            # SQL contains narrows candidates; token checks prevent Java matching JavaScript.
            if not matched_titles and not matched_skills:
                continue
            reasons = [f"Matches your desired role: {term}" for term in matched_titles]
            reasons += [f"Matches your saved skill: {term}" for term in matched_skills]
            if profile.preferred_locations:
                reasons.append("Matches a saved location preference")
            if profile.remote_only:
                reasons.append("Source explicitly labels this role remote")
            score = 7 * len(matched_titles) + 3 * len(matched_skills)
            ranked.append((score, job, reasons))
        ranked.sort(key=lambda item: (-item[0], -item[1].id))
        chosen = ranked[offset : offset + limit]
        provenance = (
            list(
                session.scalars(
                    select(Observation).where(
                        Observation.job_id.in_([job.id for _, job, _ in chosen])
                    )
                )
            )
            if chosen
            else []
        )
        items = []
        for score, job, reasons in chosen:
            sources = [
                {
                    "source_id": o.source_id,
                    "source_url": o.data["source_url"],
                    "application_url": o.data["application_url"],
                    "status": o.status,
                    "last_checked_at": o.last_checked,
                }
                for o in provenance
                if o.job_id == job.id
            ]
            items.append(
                {
                    "job": {
                        "id": job.id,
                        **{k: v for k, v in job.data.items() if k != "raw"},
                        "first_seen_at": job.first_seen,
                        "last_changed_at": job.last_changed,
                        "sources": sources,
                    },
                    "rank_score": score,
                    "reasons": reasons,
                }
            )
        return {
            **output,
            "items": items,
            "total_candidates": total,
            "candidates_ranked": len(candidates),
            "truncated": total > CANDIDATE_LIMIT,
        }
