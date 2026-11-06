"""Job Boardly's documented public XML job feed, cross-checked by the caller."""

import re
from datetime import datetime
from urllib.parse import urlsplit

from defusedxml import ElementTree as ET
from email_validator import validate_email
from vindex.connectors.public import text
from vindex.schemas import JobInput

MAX_FEED_JOBS = 5000
JOB_PATH = re.compile(r"/jobs/[a-z0-9-]+-[a-f0-9]{8}")


def parse_feed(body: bytes, origin: str) -> list[JobInput]:
    root = ET.fromstring(body, forbid_dtd=True, forbid_entities=True)
    if root.tag != "jobs" or not 0 < len(root) <= MAX_FEED_JOBS:
        raise ValueError("JobBoardly XML root, empty feed or job budget invalid")
    jobs = []
    seen_ids = set()
    seen_links = set()
    for node in root:
        if node.tag != "job" or len({child.tag for child in node}) != len(node):
            raise ValueError("Invalid JobBoardly XML job or repeated field")
        fields = {child.tag: (child.text or "").strip() for child in node}
        identifier = fields["id"]
        if (
            not identifier.isascii()
            or not identifier.isdigit()
            or int(identifier) <= 0
            or identifier in seen_ids
        ):
            raise ValueError("Invalid or duplicate JobBoardly XML ID")
        url = fields["url"]
        parsed = urlsplit(url)

        if (
            parsed.scheme != "https"
            or parsed.netloc != urlsplit(origin).netloc
            or parsed.query
            or parsed.fragment
            or not JOB_PATH.fullmatch(parsed.path)
            or fields["guid"] != identifier + "-" + parsed.path.removeprefix("/jobs/")
            or url in seen_links
        ):
            raise ValueError("Invalid JobBoardly XML canonical job identity")
        application = fields["application_link"]
        destination = urlsplit(application)
        flags = []
        if destination.scheme == "mailto" and destination.path:
            application = url
            flags.append("application_by_email")
        elif not destination.scheme and not destination.netloc:
            # Some published feed entries use a bare email rather than a mailto URL.
            # Validate syntax only; do not contact mail servers or invent an HTTPS target.
            validate_email(application, check_deliverability=False)
            application = url
            flags.append("application_by_email")
        elif (
            destination.scheme != "https"
            or not destination.hostname
            or destination.username
            or destination.password
            or destination.port not in (None, 443)
        ):
            raise ValueError("Invalid JobBoardly XML application destination")
        description = text(fields["html_description"])
        if not description:
            flags.append("description_missing")
        if not fields["published_at"]:
            raise ValueError("Missing JobBoardly XML publication date")
        salary = {
            key: fields["salary_" + source]
            for key, source in (
                ("minimum", "minimum"),
                ("maximum", "maximum"),
                ("currency", "currency"),
                ("schedule", "schedule"),
            )
        }
        jobs.append(
            JobInput(
                external_id=identifier,
                title=fields["title"],
                company=fields["company_name"],
                description=description,
                quality_flags=flags,
                location=fields["location"],
                source_url=url,
                application_url=application,
                employment_type=fields["arrangement"] or None,
                remote_status=fields["location_type"] or None,
                salary=salary if any(salary.values()) else None,
                published_at=datetime.fromisoformat(fields["published_at"]),
                raw={
                    "metadata_origin": "source_xml",
                    "xml": ET.tostring(node, encoding="unicode"),
                    "application_url": fields["application_link"],
                },
            )
        )
        seen_ids.add(identifier)
        seen_links.add(url)
    return jobs
