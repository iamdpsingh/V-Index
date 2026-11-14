import pytest
from sqlalchemy import select
from test_accounts import register
from test_lifecycle import posting
from test_resumes import private_client, upload  # noqa: F401
from vindex.accounts import recommendations
from vindex.db import Observation
from vindex.ingest import ingest
from vindex.schemas import Enumeration


@pytest.fixture
def recommendation_client(request, database, monkeypatch):
    client = request.getfixturevalue("private_client")
    monkeypatch.setattr(recommendations, "Session", database)
    return client


def test_recommendations_use_only_professional_terms_and_open_jobs(
    recommendation_client, database, source
):
    register(recommendation_client)
    with database() as session:
        ingest(
            session,
            source,
            Enumeration(
                jobs=[
                    posting(
                        external_id="1",
                        title="Backend Engineer",
                        description="Python SQL services",
                        remote_status="Remote",
                    ),
                    posting(
                        external_id="2",
                        title="Sales Manager",
                        description="Sell products",
                        application_url="https://example.com/2",
                    ),
                    posting(
                        external_id="4",
                        title="Closed Python Engineer",
                        description="Python SQL",
                        application_url="https://example.com/4",
                    ),
                    posting(
                        external_id="3",
                        title="JavaScript Engineer",
                        description="Browser products",
                        application_url="https://example.com/3",
                    ),
                ],
                complete=True,
            ),
        )
        closed = session.scalar(select(Observation).where(Observation.external_id == "4"))
        closed.status = "closed"
        session.commit()
    recommendation_client.put(
        "/api/v1/me/profile", json={"bio": "Python engineer SQL", "full_name": "Python Person"}
    )
    assert (
        recommendation_client.get("/api/v1/me/recommendations").json()["needs_preferences"] is True
    )
    assert upload(recommendation_client).status_code == 200
    assert recommendation_client.get("/api/v1/me/recommendations").json()["needs_preferences"]
    assert (
        recommendation_client.put("/api/v1/me/profile", json={"skills": ["Python"]}).status_code
        == 200
    )
    response = recommendation_client.get("/api/v1/me/recommendations")
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) == 1 and rows[0]["job"]["title"] == "Backend Engineer"
    assert any("saved skill: Python" in reason for reason in rows[0]["reasons"])
    assert rows[0]["job"]["sources"][0]["source_id"] == source.id
    recommendation_client.put(
        "/api/v1/me/profile", json={"skills": ["Java"], "use_resume_skills": False}
    )
    assert recommendation_client.get("/api/v1/me/recommendations").json()["items"] == []
    recommendation_client.put(
        "/api/v1/me/profile",
        json={
            "desired_titles": ["Backend Engineer"],
            "remote_only": True,
            "preferred_locations": ["London"],
            "use_resume_skills": False,
        },
    )
    selected = recommendation_client.get("/api/v1/me/recommendations").json()["items"]
    assert len(selected) == 1 and selected[0]["job"]["remote_status"] == "Remote"
    assert selected[0]["rank_score"] == 7
    assert recommendation_client.get("/api/v1/me/recommendations?limit=0").status_code == 422


def test_recommendation_candidate_bound_and_pagination_are_explicit(
    recommendation_client, database, source, monkeypatch
):
    register(recommendation_client)
    recommendation_client.put("/api/v1/me/profile", json={"skills": ["Python"]})
    with database() as session:
        ingest(
            session,
            source,
            Enumeration(
                jobs=[
                    posting(
                        external_id=str(i),
                        title=f"Python Engineer {i}",
                        application_url=f"https://example.com/{i}",
                    )
                    for i in range(3)
                ],
                complete=True,
            ),
        )
        session.commit()
    monkeypatch.setattr(recommendations, "CANDIDATE_LIMIT", 2)
    result = recommendation_client.get("/api/v1/me/recommendations?limit=1&offset=1").json()
    assert (
        result["total_candidates"] == 3
        and result["candidates_ranked"] == 2
        and result["truncated"] is True
    )
    assert len(result["items"]) == 1 and result["items"][0]["job"]["title"] == "Python Engineer 1"
