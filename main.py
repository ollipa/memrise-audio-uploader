""" Upload audio to Memrise courses using Google Text-To-Speech API """
import getpass
import os
from pathlib import Path
from typing import Tuple

from api.memrise import MemriseAPI
from libs import synthesizator as sn


def get_credentials() -> Tuple[str, str]:
    """ Prompt for username and password """
    username = input("Username: ")
    password = getpass.getpass()
    return username, password


def delete_file(path: Path) -> None:
    """ Delete a file """
    if path.is_file():
        os.remove(path)


def main() -> None:
    """ Main program """

    mapi = MemriseAPI(store_session=True)
    if not mapi.load_session():
        username, password = get_credentials()
        mapi.login(username, password)
    courses = mapi.get_courses()

    gapi_client = sn.create_client()

    for course in courses:
        print("\n" + course.name)
        levels = course.get_levels()

        for level in levels:
            print("  " + level.name)
            words = level.get_words()
            for word in words:
                if word.audio_count > 0:
                    print("Deleting audio in word", word.text)
                    if not word.remove_audio():
                        continue
                print("Uploading audio for word", word.text)
                audio = sn.synthesize_text(word.text, gapi_client)
                if audio:
                    word.upload_audio(audio)


if __name__ == "__main__":
    main()
