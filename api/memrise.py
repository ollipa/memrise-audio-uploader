"""Python SDK for Memrise API"""
import logging
import os
import pickle
import json
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, field

# current pylint version does not recognize dataclasses as standard library import
import requests  # pylint: disable=C0411
from requests.cookies import RequestsCookieJar  # pylint: disable=C0411
from lxml import html  # pylint: disable=C0411

# TODO: Return exceptions on errors instead of empty lists

_BASE_URL = "https://www.memrise.com/"


@dataclass
class Word:
    """ Stores word related data """
    id: int
    text: str
    column_number: int
    _client: requests.Session


@dataclass
class Level:
    """ Stores level related data """
    id: int
    name: str
    _client: requests.Session
    words: List[Word] = field(default_factory=list)


@dataclass
class Course:
    """ Stores course related data """
    id: int
    name: str
    url: str
    _client: requests.Session
    levels: Dict[int, Level] = field(default_factory=list)

    @staticmethod
    def _parse_level_name(level: html.HtmlElement) -> str:
        name = str(level.xpath(
            "div[contains(@class,'level-header')]/h3[contains(@class, 'level-name')]/text()").pop())
        return name.replace('\\n', '').strip()

    def _parse_level_list(self, response: requests.Response) -> Dict[int, Level]:
        """Parses the level listing response from Memrise."""
        course_html = html.fromstring(response.content)
        level_html = course_html.xpath("//div[@data-level-id]")
        levels = dict()
        for level in level_html:
            level_id = int(level.attrib['data-level-id'])
            level_name = self._parse_level_name(level)
            levels[level_id] = Level(id=level_id, name=level_name, _client=self._client)
        return levels

    def get_levels(self) -> List[Level]:
        """ Retrieve course's levels from Memrise """
        try:
            response = self._client.get(_BASE_URL + self.url + "edit/", timeout=60)
        except requests.exceptions.RequestException as exc:
            logging.error("%s: Failed to connect to Memrise server (%s).",
                          self.get_levels.__qualname__, exc)
            return []

        levels = dict()
        if response.status_code == 200:
            levels = self._parse_level_list(response)
            if levels:
                self.levels = levels
        else:
            logging.error("%s: Unable to retrieve levels (HTTP=%s).",
                          self.get_levels.__qualname__, response.status_code)
            return []
        return list(levels.values())


class MemriseAPI:
    """Contains the implementation for Memrise API calls"""

    def __init__(self, store_session: bool = False):
        self._client = requests.session()
        self._logged_in = False
        self._session_file = Path("session.p")
        self._store_session = store_session
        self._courses: Dict[int, Course] = dict()

    def _check_cookies(self, cookies: RequestsCookieJar) -> None:
        """Check if session and csrf cookies exist"""
        cookies.clear_expired_cookies()
        if "sessionid_2" not in cookies or "csrftoken" not in cookies:
            self._delete_session_file()
            return False
        return True

    def _delete_session_file(self) -> None:
        """ Delete a session file """
        if self._session_file.is_file():
            try:
                os.remove(self._session_file)
            except EnvironmentError as exc:
                logging.warning("%s: Unable to delete session information file (%s).",
                                self._delete_session_file.__qualname__, exc)

    def _save_session_file(self) -> None:
        """ Save session cookies to a file """
        try:
            with open(self._session_file, 'wb') as file:
                pickle.dump(self._client.cookies, file)
        except EnvironmentError as exc:
            logging.warning("%s: Unable to save session information to a file (%s).",
                            self._save_session_file.__qualname__, exc)

    def _load_session_file(self) -> RequestsCookieJar:
        """ Load session cookies from a file """
        try:
            with open(self._session_file, 'rb') as file:
                cookies = pickle.load(file)
                if isinstance(cookies, RequestsCookieJar):
                    return cookies
                raise TypeError("Session file must contain 'RequestsCookieJar'")
        except EnvironmentError as exc:
            logging.warning("%s: Unable to read session information from a file (%s).",
                            self._load_session_file.__qualname__, exc)
        except TypeError as exc:
            logging.warning("%s: %s.", self._load_session_file.__qualname__, exc)
        return None

    def _parse_course_list(self, response: requests.Response) -> Dict[int, Course]:
        """Parses the course listing response from Memrise."""
        data = None
        try:
            data = response.json()
        except json.decoder.JSONDecodeError as exp:
            logging.error("%s: Invalid JSON response from server. (%s)",
                          self._parse_course_list.__qualname__, exp)
            return dict()

        courses = dict()
        try:
            for course in data["courses"]:
                courses[course['id']] = Course(
                    id=course['id'], name=course['name'],
                    url=course['url'][1:], _client=self._client)
        except KeyError as exp:
            logging.error("%s: Invalid course listing returned from server. (key=%s)",
                          self._parse_course_list.__qualname__, exp)
            return dict()

        return courses

    def get_courses(self) -> List[Course]:
        """Retrieve the courses where the logged in user has edit permissions."""
        try:
            response = self._client.get(_BASE_URL + "ajax/courses/dashboard/" +
                                        "?courses_filter=teaching&get_review_count=false",
                                        timeout=60)
        except requests.exceptions.RequestException as exc:
            logging.error("%s: Failed to connect to Memrise server (%s).",
                          self.get_courses.__qualname__, exc)
            return []

        courses = dict()
        if response.status_code == 200:
            courses = self._parse_course_list(response)
            if courses:
                self._courses = courses
        else:
            logging.error("%s: Unable to retrieve courses (HTTP=%s).",
                          self.get_courses.__qualname__, response.status_code)
            return []

        return list(courses.values())

    def load_session(self) -> bool:
        """Load session from a file if it exists."""
        if self._session_file.is_file():
            cookies = self._load_session_file()
            if cookies is not None and self._check_cookies(cookies):
                self._client.cookies = cookies
                self._logged_in = True
                return self._logged_in
            logging.info("%s: Stored session data was invalid or expired.",
                         self.load_session.__qualname__)
        return self._logged_in

    def login(self, username: str, password: str) -> bool:
        """Login to Memrise to get session cookie"""
        login_url = _BASE_URL + "login/"

        response = self._client.get(login_url, timeout=60)

        payload = {'username': username, 'password': password,
                   'csrfmiddlewaretoken': response.cookies['csrftoken']}

        try:
            # Referer is needed for the request to succeed
            response = self._client.post(login_url, data=payload,
                                         headers=dict(Referer=login_url), timeout=30)
        except requests.exceptions.RequestException as exc:
            logging.error("%s: Failed to connect to Memrise server (%s).",
                          self.login.__qualname__, exc)
            return False

        if response.status_code == 200:
            # Login succeeded
            self._logged_in = True
            self._save_session_file()
        else:
            # Login Failed
            self._logged_in = False
            self._client = requests.session()
            logging.error("%s: Login failed. Invalid username or password (HTTP=%s).",
                          self.login.__qualname__, response.status_code)

        return self._logged_in
