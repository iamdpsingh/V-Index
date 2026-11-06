"""Robots policy for public career-page extraction; fail closed on fetch errors."""

from urllib.robotparser import RobotFileParser

from vindex.connectors.http import PublicHTTP, UpstreamStatusError

USER_AGENT = "V-Index"


class RobotsPolicy:
    def __init__(self, parser: RobotFileParser):
        self.parser = parser

    @classmethod
    async def load(cls, http: PublicHTTP, origin: str) -> "RobotsPolicy":
        parser = RobotFileParser()
        try:
            content = await http.read(f"{origin}/robots.txt", accept="text/plain,*/*;q=0.5")
        except UpstreamStatusError as error:
            if error.status_code != 404:
                raise
            content = b""  # A genuinely absent robots file imposes no directives.
        parser.parse(content.decode("utf-8", errors="replace").splitlines())
        return cls(parser)

    def check(self, url: str) -> None:
        if not self.parser.can_fetch(USER_AGENT, url):
            raise ValueError("Career page robots policy disallows this request")

    def delay(self, baseline: float = 0.3) -> float:
        delay = self.parser.crawl_delay(USER_AGENT)
        rate = self.parser.request_rate(USER_AGENT)
        seconds = max(
            baseline,
            float(delay or 0),
            rate.seconds / rate.requests if rate and rate.requests else 0,
        )
        if seconds > 30:
            raise ValueError("Robots crawl pacing exceeds inline budget")
        return seconds
