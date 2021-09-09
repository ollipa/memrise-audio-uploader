"""Memrise audio uploader command-line functionality."""
import getpass
import signal
import sys
from types import FrameType
from typing import Dict, List, Optional

from pydantic import BaseSettings

from memrise_audio_uploader.lib import memrise
from memrise_audio_uploader.lib.synthesizator import Synthesizator, Voice


class Settings(BaseSettings):
    """Application settings."""

    memrise_username: Optional[str]
    memrise_password: Optional[str]

    class Config:
        env_file = ".env"


def memrise_login() -> memrise.MemriseClient:
    """Login to Memrise and initialize client."""
    settings = Settings()
    if not settings.memrise_username:
        settings.memrise_username = input("Username: ")
    else:
        print(f"Using username '{settings.memrise_username}'")
    if not settings.memrise_password:
        settings.memrise_password = getpass.getpass()
    else:
        print("Using stored password")

    try:
        memrise_client = memrise.MemriseClient(settings.memrise_username, settings.memrise_password)
    except memrise.AuthenticationError:
        print("Invalid username or password. Exiting...")
        sys.exit(1)
    return memrise_client


def select_course(client: memrise.MemriseClient) -> memrise.Course:
    """Print available courses and prompt the user to select a course."""
    courses = dict(enumerate(client.courses(), 1))
    if not courses:
        print("Could not find any courses with edit permissions. Exiting...")
        sys.exit(1)

    print("\nAvailable courses:\n")
    for idx, course in courses.items():
        print(f"{idx}. {course.name}")

    course_selection: Optional[memrise.Course] = None
    while not course_selection:
        try:
            num = int(input("Select a course: "))
        except ValueError:
            continue
        course_selection = courses.get(num, None)

    print(f"Selected course '{course_selection.name}'")
    return course_selection


def select_voice(synthesizator: Synthesizator, language_code: str) -> Voice:
    """Print available voices and prompt the user to choose a voice."""
    voices: Dict[int, Voice] = {}
    while not voices:
        voices = dict(enumerate(synthesizator.list_voices(language_code), 1))
        if not voices:
            print(
                f"No voices found for language code '{language_code}'. "
                f"Try another language code."
            )
            language_code = input("Language code: ")

    print(f"\nAvailable voices for language code '{language_code}':\n")
    for idx, voice in voices.items():
        print(f"{idx}. {voice.name} ({voice.gender.name})")

    voice_selection: Optional[Voice] = None
    while not voice_selection:
        try:
            num = int(input("Select a voice: "))
        except ValueError:
            continue
        voice_selection = voices.get(num, None)

    print(f"Selected voice '{voice_selection.name}'")
    return voice_selection


def select_levels(course: memrise.Course) -> List[memrise.Level]:
    """Print available levels and prompt the user to select a course."""
    levels = dict(enumerate(course.levels(), 1))
    if not levels:
        print("Course does not have any levels. Exiting...")
        sys.exit(1)

    print("\nAvailable levels:\n")
    print("0. Select all levels")
    for idx, level in levels.items():
        print(f"{idx}. {level.name}")
    level_selection: List[memrise.Level] = []
    while not level_selection:
        try:
            num = int(input("Select a level: "))
        except ValueError:
            continue
        if num == 0:
            level_selection = list(levels.values())
        else:
            if (selection := levels.get(num, None)) is not None:
                level_selection.append(selection)
    return level_selection


def upload_audio(levels: List[memrise.Level], synthesizator: Synthesizator, voice: Voice) -> None:
    """Upload new audio to given levels."""
    replace_existing = input("\nReplace existing audio? (y/N): ").lower()
    for level in levels:
        words = level.learnables()
        for word in words:
            if word.audio_count > 0:
                if replace_existing == "y":
                    print(f"Deleting audio in word '{word.text}'")
                    word.remove_audio()
                else:
                    print(f"Word already has audio. Skipping word '{word.text}'")
                    continue
            print(f"Uploading audio for word '{word.text}'")
            audio = synthesizator.synthesize(word.text, voice)
            word.upload_audio(audio)


def main() -> None:
    """Main program."""
    signal.signal(signal.SIGINT, signal_handler)  # CTRL+C handler
    memrise_client = memrise_login()
    course = select_course(memrise_client)
    levels = select_levels(course)
    synthesizator = Synthesizator()
    voice = select_voice(synthesizator, course.target_lang)
    upload_audio(levels, synthesizator, voice)


def signal_handler(_sig: int, _frame: Optional[FrameType]) -> None:
    """Signal handler to exit program."""
    print("\nAborting...")
    sys.exit(0)
