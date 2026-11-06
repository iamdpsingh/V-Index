"""Detection and factories for implemented providers only."""

import re
from urllib.parse import parse_qs, urlsplit

import httpx
from vindex.connectors.applicantpro import ApplicantProConnector
from vindex.connectors.bamboohr import BambooHRConnector
from vindex.connectors.breezy import BreezyConnector
from vindex.connectors.careerplug import CareerPlugConnector
from vindex.connectors.freshteam import FreshteamConnector
from vindex.connectors.gohire import SLUG as GOHIRE_SLUG
from vindex.connectors.gohire import GoHireConnector
from vindex.connectors.hirebridge import HireBridgeConnector
from vindex.connectors.hirehive import HireHiveConnector
from vindex.connectors.hiringthing import HiringThingConnector
from vindex.connectors.jazzhr import JazzHRConnector
from vindex.connectors.jobboardly import JobboardlyConnector
from vindex.connectors.jobvite import JobviteConnector
from vindex.connectors.join import JoinConnector
from vindex.connectors.kula import KulaConnector
from vindex.connectors.manatal import ManatalConnector
from vindex.connectors.personio import PersonioConnector
from vindex.connectors.pinpoint import PinpointConnector
from vindex.connectors.polymer import SLUG as POLYMER_SLUG
from vindex.connectors.polymer import PolymerConnector
from vindex.connectors.public import Connector, PublicConnector
from vindex.connectors.public import detect as detect_original
from vindex.connectors.recooty import RecootyConnector
from vindex.connectors.recruitee import RecruiteeConnector
from vindex.connectors.rippling import RipplingConnector
from vindex.connectors.smartrecruiters import SmartRecruitersConnector
from vindex.connectors.teamtailor import TENANT, TeamtailorConnector
from vindex.connectors.trakstar import TrakstarConnector
from vindex.connectors.trinet import SLUG as TRINET_SLUG
from vindex.connectors.trinet import TriNetConnector
from vindex.connectors.workable import WorkableConnector
from vindex.connectors.workday import HOST_PATTERN, SITE_PATTERN, WorkdayConnector

PERSONIO_HOST = re.compile(r"([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.jobs\.personio\.(de|com)")


def detect(url: str) -> tuple[str, str]:
    p = urlsplit(url)
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
        raise ValueError("Use an HTTPS hosted career board URL without credentials or custom ports")
    for suffix, provider in (
        ("hire.trakstar.com", "trakstar"),
        ("freshteam.com", "freshteam"),
        ("hiringthing.com", "hiringthing"),
        ("applicantpro.com", "applicantpro"),
        ("isolvedhire.com", "isolvedhire"),
        ("teamtailor.com", "teamtailor"),
        ("breezy.hr", "breezy"),
        ("bamboohr.com", "bamboohr"),
        ("pinpointhq.com", "pinpoint"),
        ("jobboardly.com", "jobboardly"),
        ("applytojob.com", "jazzhr"),
        ("hirehive.com", "hirehive"),
    ):
        match = re.fullmatch(rf"({TENANT})\.{re.escape(suffix)}", p.hostname or "")
        if match:
            return provider, match[1]
    if p.hostname == "join.com":
        matched = re.fullmatch(rf"/companies/({TENANT})/?", p.path)
        if not matched or p.query or p.fragment:
            raise ValueError("Expected an unfiltered native JOIN company URL")
        return "join", matched[1]
    if p.hostname == "recruit.hirebridge.com":
        query = parse_qs(p.query, keep_blank_values=True)
        if (
            p.path.lower() != "/v3/jobs/list.aspx"
            or set(query) != {"cid"}
            or len(query["cid"]) != 1
            or not re.fullmatch(r"[1-9][0-9]{0,14}", query["cid"][0])
            or p.fragment
        ):
            raise ValueError("Expected an unfiltered native HireBridge list URL with customer ID")
        return "hirebridge", query["cid"][0]
    if p.hostname == "app.trinethire.com":
        matched = re.fullmatch(rf"/companies/({TRINET_SLUG})/jobs/?", p.path)
        if not matched or len(matched[1]) > 100 or p.query or p.fragment:
            raise ValueError("Expected an unfiltered TriNet Hire company jobs URL")
        return "trinet", matched[1]
    if p.hostname == "app.careerplug.com":
        matched = re.fullmatch(r"/accounts/([1-9][0-9]{0,14})/?", p.path)
        if not matched or p.query or p.fragment:
            raise ValueError("Expected an unfiltered native CareerPlug account URL")
        return "careerplug", matched[1]
    if p.hostname == "careers.kula.ai":
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(TENANT, slug):
            raise ValueError("Expected a Kula employer career URL")
        return "kula", slug
    if p.hostname == "ats.rippling.com":
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(TENANT, slug):
            raise ValueError("Expected a Rippling hosted employer career URL")
        return "rippling", slug
    if p.hostname == "jobs.jobvite.com":
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(TENANT, slug):
            raise ValueError("Expected a Jobvite hosted employer career URL")
        return "jobvite", slug
    if p.hostname == "careerspage.io":
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(TENANT, slug):
            raise ValueError("Expected a Recooty hosted team career URL")
        return "recooty", slug
    if p.hostname == "www.careers-page.com":
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(TENANT, slug):
            raise ValueError("Expected a Manatal hosted career-board URL")
        return "manatal", slug
    if p.hostname == "jobs.polymer.co":
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(POLYMER_SLUG, slug):
            raise ValueError("Expected a Polymer organization career URL")
        return "polymer", slug
    if p.hostname == "jobs.gohire.io":
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(GOHIRE_SLUG, slug) or len(slug) > 100:
            raise ValueError("Expected a GoHire hosted career-board URL")
        return "gohire", slug
    if p.hostname == "apply.workable.com":
        slug = p.path.strip("/").split("/")[0]
        if not re.fullmatch(TENANT, slug) or slug in {"j", "api"}:
            raise ValueError("Expected a Workable account career URL, not a bare job URL")
        return "workable", slug
    workday = HOST_PATTERN.fullmatch(p.hostname or "")
    if workday:
        parts = p.path.strip("/").split("/")
        if re.fullmatch(r"[a-z]{2,3}-[A-Z]{2}", parts[0]):
            parts = parts[1:]
        if not parts or not SITE_PATTERN.fullmatch(parts[0]):
            raise ValueError("Expected a Workday external career-site identifier")
        slug = f"{workday[1]}~{workday[2]}~{parts[0]}"
        if len(slug) > 100:
            raise ValueError("Workday configuration exceeds storage limit")
        return "workday", slug
    recruitee = re.fullmatch(
        r"([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)\.recruitee\.com", p.hostname or ""
    )
    if recruitee:
        return "recruitee", recruitee[1]
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
            "Supported hosted boards: Greenhouse, Lever, Ashby, SmartRecruiters, Personio, Recruitee, Workday, Teamtailor, Breezy HR, Workable, BambooHR, Pinpoint, Jobboardly, JazzHR, HireHive, GoHire, Polymer, Manatal, Recooty, Jobvite, ApplicantPro, iSolvedHire, HiringThing, Freshteam, Trakstar, Rippling, Kula.ai, CareerPlug, TriNet, HireBridge and JOIN.com"
        ) from error


def create_connector(
    provider: str, slug: str, company: str, client: httpx.AsyncClient
) -> Connector:
    if provider == "join":
        return JoinConnector(provider, slug, company, client)
    if provider == "hirebridge":
        return HireBridgeConnector(provider, slug, company, client)
    if provider == "trinet":
        return TriNetConnector(provider, slug, company, client)
    if provider == "careerplug":
        return CareerPlugConnector(provider, slug, company, client)
    if provider == "kula":
        return KulaConnector(provider, slug, company, client)
    if provider == "rippling":
        return RipplingConnector(provider, slug, company, client)
    if provider == "trakstar":
        return TrakstarConnector(provider, slug, company, client)
    if provider == "freshteam":
        return FreshteamConnector(provider, slug, company, client)
    if provider == "hiringthing":
        return HiringThingConnector(provider, slug, company, client)
    if provider in {"applicantpro", "isolvedhire"}:
        return ApplicantProConnector(provider, slug, company, client)
    if provider == "jobvite":
        return JobviteConnector(provider, slug, company, client)
    if provider == "recooty":
        return RecootyConnector(provider, slug, company, client)
    if provider == "manatal":
        return ManatalConnector(provider, slug, company, client)
    if provider == "polymer":
        return PolymerConnector(provider, slug, company, client)
    if provider == "gohire":
        return GoHireConnector(provider, slug, company, client)
    if provider == "hirehive":
        return HireHiveConnector(provider, slug, company, client)
    if provider == "jazzhr":
        return JazzHRConnector(provider, slug, company, client)
    if provider == "jobboardly":
        return JobboardlyConnector(provider, slug, company, client)
    if provider == "pinpoint":
        return PinpointConnector(provider, slug, company, client)
    if provider == "bamboohr":
        return BambooHRConnector(provider, slug, company, client)
    if provider == "workable":
        return WorkableConnector(provider, slug, company, client)
    if provider == "teamtailor":
        return TeamtailorConnector(provider, slug, company, client)
    if provider == "breezy":
        return BreezyConnector(provider, slug, company, client)
    if provider == "workday":
        return WorkdayConnector(provider, slug, company, client)
    if provider == "recruitee":
        return RecruiteeConnector(provider, slug, company, client)
    if provider == "smartrecruiters":
        return SmartRecruitersConnector(provider, slug, company, client)
    if provider in {"personio-de", "personio-com"}:
        return PersonioConnector(provider, slug, company, client)
    return PublicConnector(provider, slug, company, client)
