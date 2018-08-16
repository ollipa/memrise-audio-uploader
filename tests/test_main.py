"""Test main."""
# pylint: disable=missing-docstring,no-self-use
import io
import os

import pytest
from flexmock import flexmock

from memrise_audio_uploader.cli import main
from memrise_audio_uploader.lib import memrise, synthesizator


@pytest.fixture(autouse=True, scope="module")
def set_envs():
    os.environ["MEMRISE_USERNAME"] = "foo"
    os.environ["MEMRISE_PASSWORD"] = "bar"


class TestMain:
    @pytest.fixture
    def mock_learnables(self):
        learnable = flexmock(text="foo")
        learnable.should_receive("upload_audio").once()
        return [learnable]

    @pytest.fixture
    def mock_levels(self, mock_learnables):
        level = flexmock(name="level 1")
        level.should_receive("learnables").and_return(mock_learnables).once()
        return [level]

    @pytest.fixture
    def mock_courses(self, mock_levels):
        course = flexmock(name="course 1", target_lang="en")
        course.should_receive("levels").and_return(mock_levels).once()
        return [course]

    @pytest.fixture(autouse=True)
    def mock_memrise_client(self, mock_courses):
        mocked = flexmock()
        flexmock(memrise.MemriseClient).new_instances(mocked)
        mocked.should_receive("courses").and_return(mock_courses)

    @pytest.fixture
    def mock_voices(self):
        voice = flexmock(name="voice 1", gender=flexmock(name="female"))
        return [voice]

    @pytest.fixture(autouse=True)
    def mock_synth_client(self, mock_voices, mock_learnables):
        mocked = flexmock()
        flexmock(synthesizator.Synthesizator).new_instances(mocked)
        mocked.should_receive("list_voices").and_return(mock_voices).once()
        mocked.should_receive("synthesize").times(len(mock_learnables))

    @pytest.fixture(autouse=True)
    def mock_input(self, monkeypatch):
        inputs = io.StringIO("1\n1\n1\nn\n")
        monkeypatch.setattr("sys.stdin", inputs)

    def test_it_works(self):
        main()
