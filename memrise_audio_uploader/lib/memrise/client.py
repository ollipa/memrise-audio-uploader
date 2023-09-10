"""Memrise SDK client."""
# pylint: disable=protected-access
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Final, List, Optional, Tuple

import requests
from lxml import html

from . import exceptions, models

log = logging.getLogger(__name__)

_CLIENT_ID: Final[str] = "1e739f5e77704b57a703"
_BASE_URL: Final[str] = "https://app.memrise.com"


class Learnable:
    """Memrise learnable (ie. word)."""

    def __init__(
        self,
        client: MemriseClient,
        id: int,  # pylint: disable=redefined-builtin,invalid-name
        text: str,
        column_number: int,
        audio_count: int,
    ) -> None:
        self._client = client
        self._referer = f"{_BASE_URL}/course"
        self.id = id
        self.text = text
        self.column_number = column_number
        self.audio_count = audio_count

    def remove_audio(self) -> int:
        """Remove all audio from a learnable."""
        for file_id in range(1, self.audio_count + 1):
            payload = {
                "thing_id": self.id,
                "column_key": self.column_number,
                "cell_type": "column",
                "file_id": file_id,
            }
            try:
                self._client._send_post_request(
                    "/ajax/thing/column/delete_from/",
                    referer=self._referer,
                    payload=payload,
                )
            except exceptions.MemriseConnectionError as exc:
                logging.error(f"Failed to remove audio audio file ID {file_id}: {exc}")
                continue

            self.audio_count -= 1
        return self.audio_count

    def upload_audio(self, audio: bytes) -> None:
        """Upload audio file to for a learnable. Audio should be in mp3 format."""
        files = {"f": ("audio.mp3", audio, "audio/mp3")}
        payload = {
            "thing_id": self.id,
            "cell_id": self.column_number,
            "cell_type": "column",
        }
        self._client._send_post_request(
            "/ajax/thing/cell/upload_file/",
            files=files,
            referer=self._referer,
            payload=payload,
        )


class Level:
    """Memrise course level."""

    def __init__(self, client: MemriseClient, schema: models.LevelSchema) -> None:
        self._client = client
        self._schema = schema

    @property
    def id(self) -> int:
        """Level ID."""
        return self._schema.id

    @property
    def name(self) -> str:
        """Level name."""
        return self._schema.title

    def learnables(self) -> List[Learnable]:
        """Retrieve learnables in a level."""
        data = self._client._send_get_request(f"/ajax/level/editing_html/?level_id={self.id}")
        return self._parse_learnables(data)

    def _parse_learnables(self, data: Dict[str, Any]) -> List[Learnable]:
        """Parse learnables (words) from Memrise API response."""
        learnables: List[Learnable] = []
        tree = html.fromstring(data["rendered"])
        learnables_html: list[Any] = tree.xpath("//tr[contains(@class, 'thing')]")  # type: ignore
        for learnable in learnables_html:
            learnable_id: int = learnable.attrib["data-thing-id"]
            try:
                learnable_text: str = learnable.xpath("td[2]/div/div/text()")[0]
                column_number: int = learnable.xpath("td[contains(@class, 'audio')]/@data-key")[0]
            except IndexError:
                logging.warning("Failed to parse learnable id %s", learnable_id)
                continue
            audio_count: int = len(
                learnable.xpath(
                    "td[contains(@class, 'audio')]/div/div[contains(@class, 'dropdown-menu')]/div"
                )
            )
            learnables.append(
                Learnable(
                    client=self._client,
                    id=learnable_id,
                    text=learnable_text,
                    column_number=column_number,
                    audio_count=audio_count,
                )
            )

        return learnables


class Course:
    """Memrise course."""

    def __init__(self, client: MemriseClient, schema: models.DashboardCourseSchema) -> None:
        self._client = client
        self._dashboard_schema = schema
        self._schema: Optional[models.CourseSchema] = None

    @property
    def id(self) -> str:
        """Course ID."""
        return self._dashboard_schema.id

    @property
    def name(self) -> str:
        """Course name."""
        return self._dashboard_schema.name

    @property
    def target_lang(self) -> str:
        """Target language."""
        if self._schema is None:
            data = self._client._send_get_request(f"/v1.21/courses/{self.id}/")
            self._schema = models.CourseSchema(**data["courses"][0])
        return self._schema.target_language_code

    def levels(self) -> List[Level]:
        """Retrieve course's levels."""
        data = self._client._send_get_request(f"/v1.21/courses/{self.id}/levels/")
        level_list = models.LevelListing(**data)
        return [Level(self._client, schema) for schema in level_list.levels]


class MemriseClient:
    """Contains the implementation for Memrise API calls"""

    def __init__(
        self,
        username: str,
        password: str,
        session: Optional[requests.Session] = None,
        timeout: int = 30,
    ):
        if session is None:
            session = requests.Session()
        self._timeout = timeout
        self._session = session
        self._login(username, password)

    def courses(self) -> List[Course]:
        """Retrieve the courses to which the logged in user has edit permissions."""
        all_courses: List[Course] = []
        has_more_pages = True
        offset = 0
        while has_more_pages:
            data = self._send_get_request(
                "/v1.21/dashboard/courses/",
                params={
                    "filter": "teaching",
                    "offset": offset,
                    "limit": 8,
                },
            )
            course_list = models.DashboardCourses(**data)
            has_more_pages = course_list.has_more_pages
            offset += 9
            all_courses.extend(Course(self, schema) for schema in course_list.courses)
        return all_courses

    def _login(self, username: str, password: str) -> None:
        """Login to Memrise to get session cookie."""
        try:
            response = self._session.get(
                self._get_url("/v1.21/web/ensure_csrf"), timeout=self._timeout
            )
        except requests.RequestException as exc:
            raise exceptions.MemriseConnectionError(
                f"Connection failed to Memrise ensure_csrf endpoint: {exc}"
            )

        payload = {
            "client_id": _CLIENT_ID,
            "grant_type": "password",
            "username": username,
            "password": password,
        }
        try:
            response = self._session.post(
                self._get_url("/v1.21/auth/access_token/"),
                data=payload,
                headers={"Referer": self._get_url("/signin")},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise exceptions.MemriseConnectionError(
                f"Connection failed to Memrise access_token endpoint: {exc}"
            )

        try:
            data = response.json()
        except json.decoder.JSONDecodeError as exc:
            raise exceptions.ParseError(f"Invalid JSON response for a GET request: {exc}")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            if response.status_code == 403:
                raise exceptions.AuthenticationError(f"Authentication failed: {exc}")
            raise exceptions.MemriseConnectionError(f"Unexpected response during login: {exc}")

        try:
            response = self._session.get(
                self._get_url("/v1.21/auth/web/"),
                timeout=self._timeout,
                params={
                    "invalidate_token_after": True,
                    "token": data["access_token"]["access_token"],
                },
            )
        except requests.RequestException as exc:
            raise exceptions.MemriseConnectionError(
                f"Connection failed to Memrise web auth endpoint: {exc}"
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            if response.status_code == 403:
                raise exceptions.AuthenticationError(f"Authentication failed: {exc}")
            raise exceptions.MemriseConnectionError(f"Unexpected response during login: {exc}")

    def _send_get_request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Send GET request and parse JSON response."""
        try:
            response = self._session.get(
                self._get_url(path),
                params=params,
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise exceptions.MemriseConnectionError(f"Get request failed: {exc}")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise exceptions.MemriseConnectionError(f"Unexpected response for a GET request: {exc}")

        try:
            data = response.json()
        except json.decoder.JSONDecodeError as exc:
            raise exceptions.ParseError(f"Invalid JSON response for a GET request: {exc}")

        return data

    def _send_post_request(
        self,
        path: str,
        payload: Dict[str, Any],
        referer: str,
        files: Optional[Dict[str, Tuple[str, bytes, str]]] = None,
    ) -> requests.Response:
        """Send POST request."""
        payload["csrfmiddlewaretoken"] = self._session.cookies["csrftoken"]
        try:
            response = self._session.post(
                self._get_url(path),
                files=files,
                headers={"Referer": referer},
                data=payload,
                timeout=self._timeout,
            )
        except requests.exceptions.RequestException as exc:
            raise exceptions.MemriseConnectionError(f"POST request failed': {exc}")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise exceptions.MemriseConnectionError(
                f"Unexpected response to a POST request': {exc}"
            )

        return response

    def _get_url(self, path: str) -> str:
        return f"{_BASE_URL}{path}"
