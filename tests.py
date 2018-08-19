"""Unit tests"""
import unittest
from unittest import mock

import requests

from api.memrise import MemriseAPI


class TestMemriseAPI(unittest.TestCase):
    """Unit tests for MemriseAPI"""

    @mock.patch.object(requests.Session, 'post', autospec=True)
    @mock.patch.object(requests.Session, 'get', autospec=True)
    def test_login_success(self, mock_get, mock_post):
        """Test login method on succesful login."""
        mapi = MemriseAPI()

        mock_post.return_value.status_code = 200

        result = mapi.login('foo', 'bar')
        mock_get.assert_called_once()
        mock_post.assert_called_once()
        assert result is True


if __name__ == '__main__':
    unittest.main()
