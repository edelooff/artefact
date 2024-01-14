from __future__ import annotations

import logging
import time
from importlib.metadata import version
from itertools import count
from typing import Any, Iterator
from urllib.parse import urljoin

from lxml import html
from requests import Response, Session

log = logging.getLogger(__name__)


class ArchiveApi:
    """Wrapper for searching and fetching pages from the Archive."""

    def __init__(
        self,
        root: str = "https://archiveofourown.org",
        username: str | None = None,
        password: str | None = None,
        fetch_interval: float = 1.5,
    ):
        self.root = root
        self.session = Session()
        self.session.headers["User-Agent"] = self.user_agent
        self.session.cookies["view_adult"] = "true"
        self.delay = Delay(fetch_interval)
        if username is not None and password is not None:
            self._login(username, password)
        elif username is not None or password is not None:
            raise ValueError("Provide both username and password, or neither.")

    @property
    def user_agent(self) -> str:
        return f"bot artefact/{version('artefact')} requests/{version('requests')}"

    def fetch_page(self, path: str, **kwargs: Any) -> Html:
        """Fetches a page from the Archive, returned as a parsed html tree.

        Provides an automated retry with in case of rate limiting by the remote.
        """
        for attempt in count(1):
            with self.delay:
                response = self._get(path, **kwargs)
            if response.text.startswith("Retry later"):
                log.info(f"Rate limited, remorseful pause ({attempt})")
                time.sleep(20)
                continue
            return Html.from_response(response)
        raise SystemExit("Persistent rate limit :(")

    def _get(self, path, **kwargs) -> Response:
        """Executes GET request using session and base path."""
        return self.session.get(urljoin(self.root, path), **kwargs)

    def _post(self, path, **kwargs) -> Response:
        """Executes POST request using session and base path."""
        return self.session.post(urljoin(self.root, path), **kwargs)

    def _login(self, username: str, password: str) -> None:
        """Log in to AO3 using username and password, storing cookie in the session."""
        # Grab the CSRF token and in the process acquire a session token
        session_token_response = self._get("/token_dispenser.json")
        login_response = self._post(
            "/users/login",
            data={
                "authenticity_token": session_token_response.json()["token"],
                "user[login]": username,
                "user[password]": password,
            },
        )
        if login_response.url == urljoin(self.root, f"/users/{username}"):
            return  # Success!
        elif login_response.url == urljoin(self.root, "/users/login"):
            html = Html.from_response(login_response)
            alert = html.first(".flash.alert")
            reason = "[unspecified]" if alert is None else alert.text
            raise Exception(f"Bad username or password: {reason}")
        elif login_response.url == urljoin(self.root, "/auth_error"):
            html = Html.from_response(login_response)
            error = html.first(".error-auth_error p")
            reason = "[unspecified]" if error is None else error.text
            raise Exception(f"Credential or session failure: {reason}")


class Delay:
    """A simple delay provider, for performing actions with a minimum interval.

    This is used to perform HTTP crawling at a more responsible rate.
    """

    def __init__(self, interval: float):
        self._last_event = 0.0
        self.interval = interval

    @property
    def _next_call_at(self) -> float:
        return self._last_event + self.interval

    def __enter__(self) -> None:
        """Sleeps until the next permitted event and updates the last event time."""
        time.sleep(max(0, self._next_call_at - time.time()))
        self._last_event = time.time()

    def __exit__(self, *exc_info) -> None:
        pass


class Html:
    """Utility wrapper around lxml HtmlElement, with easier CSS selections."""

    def __init__(self, element: html.HtmlElement):
        self.element = element

    def attr(self, attribute) -> str | None:
        """Return value of named attribute, or None if none exists"""
        return self.element.get(attribute)

    def first(self, path) -> Html | None:
        return next(self.all(path), None)

    def all(self, path) -> Iterator[Html]:
        return map(Html, self.element.cssselect(path))

    @property
    def text(self) -> str:
        return " ".join(map(str.strip, self.element.xpath(".//text()")))
        return self.element.text

    @classmethod
    def from_response(cls, response: Response) -> Html:
        return Html(html.fromstring(response.text))
