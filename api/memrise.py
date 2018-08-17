"""Python SDK for Memrise API"""
import logging
import os
import pickle
import json
from pathlib import Path
from typing import List
from dataclasses import dataclass, field

# current pylint version does not recognize dataclasses as standard library import
import requests  # pylint: disable=C0411
from requests.cookies import RequestsCookieJar  # pylint: disable=C0411


@dataclass
class Word:
    """ Stores word related data """
    id: int
    text: str
    column_number: int


@dataclass
class Level:
    """ Stores level related data """
    id: int
    words: List[Word] = field(default_factory=list)


@dataclass
class Course:
    """ Stores course related data """
    id: int
    name: str
    url: str
    levels: List[Level] = field(default_factory=list)


class MemriseAPI:
    """Contains the implementation for Memrise API calls"""

    _BASE_URL = "https://www.memrise.com/"

    def __init__(self, store_session: bool = False):
        self._client = requests.session()
        self._logged_in = False
        self._session_file = Path("session.p")
        self._store_session = store_session
        self.courses: List[Course] = list()

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
                                self.__qualname__, exc)

    def _save_session_file(self) -> None:
        """ Save session cookies to a file """
        try:
            with open(self._session_file, 'wb') as file:
                pickle.dump(self._client.cookies, file)
        except EnvironmentError as exc:
            logging.warning("%s: Unable to save session information to a file (%s).",
                            self.__qualname__, exc)

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
                            self.__qualname__, exc)
        except TypeError as exc:
            logging.warning("%s: %s.", self.__qualname__, exc)
        return None

    def load_session(self) -> bool:
        """Load session from a file if it exists."""
        if self._session_file.is_file():
            cookies = self._load_session_file()
            if cookies is not None:
                if self._check_cookies(cookies):
                    self._client.cookies = cookies
                    self._logged_in = True
                    return self._logged_in
            logging.info("%s: Stored session data was invalid or expired.", self.__qualname__)
        return self._logged_in

    def _parse_course_list(self, response: requests.Response) -> List[Course]:
        """Parses the course listing response from Memrise."""
        data = None
        try:
            data = response.json()
        except json.decoder.JSONDecodeError as exp:
            logging.error("%s: Invalid JSON response from server. (%s)", self.__qualname__, exp)
            return []

        courses = []
        try:
            for course in data["courses"]:
                courses.append(Course(id=course['id'], name=course['name'], url=course['url'][1:]))
        except KeyError as exp:
            logging.error("%s: Invalid course listing returned from server. (key=%s)",
                          self.__qualname__, exp)
            return []

        return courses

    def retrieve_courses(self) -> List[Course]:
        """Retrieve the courses where the logged in user has edit permissions."""
        try:
            response = self._client.get(self._BASE_URL + "ajax/courses/dashboard/" +
                                        "?courses_filter=teaching&get_review_count=false",
                                        timeout=60)
        except requests.exceptions.RequestException as exc:
            logging.error("%s: Failed to connect to Memrise server (%s).", self.__qualname__, exc)
            return []

        if response.status_code == 200:
            courses = self._parse_course_list(response)
            if courses:
                self.courses = courses
        else:
            logging.error("%s: Login failed. Invalid username or password (HTTP=%s).",
                          self.__qualname__, response.status_code)
            return []

        return courses

    def login(self, username: str, password: str) -> bool:
        """Login to Memrise to get session cookie"""
        login_url = self._BASE_URL + "login/"

        response = self._client.get(login_url, timeout=60)

        payload = {'username': username, 'password': password,
                   'csrfmiddlewaretoken': response.cookies['csrftoken']}

        try:
            # Referer is needed for the request to succeed
            response = self._client.post(login_url, data=payload,
                                         headers=dict(Referer=login_url), timeout=30)
        except requests.exceptions.RequestException as exc:
            logging.error("%s: Failed to connect to Memrise server (%s).", self.__qualname__, exc)
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
                          self.__qualname__, response.status_code)

        return self._logged_in
