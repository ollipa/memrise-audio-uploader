"""Test main."""
# pylint: disable=missing-docstring,no-self-use
import io
import os

import pytest
from chainmock import mocker


@pytest.fixture(autouse=True, scope="module")
def set_envs():
    os.environ["MEMRISE_USERNAME"] = "foo"
    os.environ["MEMRISE_PASSWORD"] = "bar"


class TestMain:
    @pytest.fixture
    def mock_learnables(self):
        learnable = mocker(text="foo", audio_count=0)
        learnable.mock("upload_audio").called_once()
        return [learnable]

    @pytest.fixture
    def mock_levels(self, mock_learnables):
        level = mocker(name="level 1")
        level.mock("learnables").return_value(mock_learnables).called_once()
        return [level]

    @pytest.fixture
    def mock_courses(self, mock_levels):
        course = mocker(name="course 1", target_lang="en")
        course.mock("levels").return_value(mock_levels).called_once()
        return [course]

    @pytest.fixture(autouse=True)
    def mock_memrise_client(self, mock_courses):
        mocked = mocker("memrise_audio_uploader.lib.memrise.MemriseClient")
        mocked.mock("courses").return_value(mock_courses)

    @pytest.fixture
    def mock_voices(self):
        voice = mocker(name="voice 1", gender=mocker(name="female"))
        return [voice]

    @pytest.fixture(autouse=True)
    def mock_synth_client(self, mock_voices, mock_learnables):
        mocked = mocker("memrise_audio_uploader.lib.synthesizator.Synthesizator")
        mocked.mock("list_voices").return_value(mock_voices).called_once()
        mocked.mock("synthesize").call_count(len(mock_learnables))

    @pytest.fixture(autouse=True)
    def mock_input(self, monkeypatch):
        inputs = io.StringIO("1\n1\n1\nn\n")
        monkeypatch.setattr("sys.stdin", inputs)

    def test_it_works(self):
        from memrise_audio_uploader.cli import main  # pylint: disable=import-outside-toplevel

        main()
