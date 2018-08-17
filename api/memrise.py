"""Python SDK for Memrise API"""
import logging
import os
import pickle
from pathlib import Path

import requests
from requests.cookies import RequestsCookieJar


class MemriseAPI:
    """Contains the implementation for Memrise API calls"""

    _BASE_URL = "https://www.memrise.com/"

    def __init__(self, store_session: bool = False):
        self._client = requests.session()
        self._logged_in = False
        self._session_file = Path("session.p")
        self._store_session = store_session

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
        """Load session from a file if it exists"""
        if self._session_file.is_file():
            cookies = self._load_session_file()
            if cookies is not None:
                if self._check_cookies(cookies):
                    self._client.cookies = cookies
                    self._logged_in = True
                    return self._logged_in
            logging.info("%s: Stored session data was invalid or expired.", self.__qualname__)
        return self._logged_in

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
