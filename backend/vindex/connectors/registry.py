"""Detection and factories for implemented providers only."""

import re
from urllib.parse import urlsplit

import httpx
from vindex.connectors.personio import PersonioConnector
from vindex.connectors.public import Connector, PublicConnector
from vindex.connectors.public import detect as detect_original
from vindex.connectors.smartrecruiters import SmartRecruitersConnector

PERSONIO_HOST = re.compile(r"([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.jobs\.personio\.(de|com)")


def detect(url: str) -> tuple[str, str]:
    p = urlsplit(url)
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
        raise ValueError("Use an HTTPS hosted career board URL without credentials or custom ports")
    personio = PERSONIO_HOST.fullmatch(p.hostname or "")
    if personio:
        return f"personio-{personio[2]}", personio[1]
    if p.hostname in {"careers.smartrecruiters.com", "jobs.smartrecruiters.com"}:
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", slug):
            raise ValueError("Expected a SmartRecruiters company identifier")
        return "smartrecruiters", slug
    try:
        return detect_original(url)
    except ValueError as error:
        raise ValueError(
            "Supported hosted boards: Greenhouse, Lever, Ashby, SmartRecruiters and Personio"
        ) from error


def create_connector(
    provider: str, slug: str, company: str, client: httpx.AsyncClient
) -> Connector:
    if provider == "smartrecruiters":
        return SmartRecruitersConnector(provider, slug, company, client)
    if provider in {"personio-de", "personio-com"}:
        return PersonioConnector(provider, slug, company, client)
    return PublicConnector(provider, slug, company, client)
