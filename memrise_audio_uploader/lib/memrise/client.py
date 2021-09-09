"""Memrise SDK client."""
# pylint: disable=protected-access
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Final, List, Optional, Tuple

import requests
from lxml import html

from . import exceptions, models

logger = logging.getLogger(__name__)

_BASE_URL: Final[str] = "https://app.memrise.com"


class Learnable:
    """Memrise learnable (ie. word)."""

    def __init__(
        self,
        client: MemriseClient,
        id: int,  # pylint: disable=redefined-builtin
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
        learnables_html = tree.xpath("//tr[contains(@class, 'thing')]")
        for learnable in learnables_html:
            learnable_id = learnable.attrib["data-thing-id"]
            try:
                learnable_text = learnable.xpath("td[2]/div/div/text()")[0]
                column_number = learnable.xpath("td[contains(@class, 'audio')]/@data-key")[0]
            except IndexError:
                logging.warning("Failed to parse learnable id %s", learnable_id)
                continue
            audio_count = len(
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

    def __init__(self, client: MemriseClient, schema: models.CourseSchema) -> None:
        self._client = client
        self._schema = schema

    @property
    def id(self) -> int:
        """Course ID."""
        return self._schema.id

    @property
    def name(self) -> str:
        """Course name."""
        return self._schema.name

    @property
    def source_lang(self) -> str:
        """Source language."""
        return self._schema.source.language_code

    @property
    def target_lang(self) -> str:
        """Target language."""
        return self._schema.target.language_code

    def levels(self) -> List[Level]:
        """Retrieve course's levels."""
        data = self._client._send_get_request(f"/v1.17/courses/{self.id}/levels/")
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
        has_more_courses = True
        offset = 0
        while has_more_courses:
            data = self._send_get_request(
                "/ajax/courses/dashboard/",
                params={
                    "courses_filter": "teaching",
                    "get_review_count": "false",
                    "offset": offset,
                    "limit": 8,
                },
            )
            course_list = models.CourseListing(**data)
            has_more_courses = course_list.has_more_courses
            offset += 9
            all_courses.extend(Course(self, schema) for schema in course_list.courses)
        return all_courses

    def _login(self, username: str, password: str) -> None:
        """Login to Memrise to get session cookie."""
        login_url = f"{_BASE_URL}/login/"
        try:
            response = self._session.get(login_url, timeout=self._timeout)
        except requests.RequestException as exc:
            raise exceptions.MemriseConnectionError(
                f"Connection failed to Memrise login page: {exc}"
            )

        payload = {
            "username": username,
            "password": password,
            "csrfmiddlewaretoken": response.cookies["csrftoken"],
        }
        try:
            response = self._session.post(
                login_url, data=payload, headers={"Referer": login_url}, timeout=self._timeout
            )
        except requests.RequestException as exc:
            raise exceptions.MemriseConnectionError(f"Connection failed during login: {exc}")

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
                f"{_BASE_URL}{path}",
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
                f"{_BASE_URL}{path}",
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
