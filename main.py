""" Upload audio to Memrise courses using Google Text-To-Speech API """
import getpass
import os
import json
from pathlib import Path
from typing import Tuple, List

# current pylint version does not recognize dataclasses as standard library import
import requests  # pylint: disable=C0411
from lxml import html  # pylint: disable=C0411

from libs import synthesize_text, create_client
from api.memrise import MemriseAPI

BASE_URL = "https://www.memrise.com/"


def get_credentials() -> Tuple[str, str]:
    """ Prompt for username and password """
    username = input("Username: ")
    password = getpass.getpass()
    return username, password


def deleteFile(path: Path) -> None:
    """ Delete a file """
    if path.is_file():
        os.remove(path)


def retrieveCourses(client: requests.sessions.Session) -> List[Course]:
    """ Retrieve users listing from Memrise """
    print("Retrieving courses.")
    r = client.get(BASE_URL + "ajax/courses/dashboard/" +
                   "?courses_filter=teaching&get_review_count=false", timeout=60)

    if r.status_code != 200:
        print("Failed to retrieve course list. Exiting...")
        exit(1)

    data = dict()
    courses: List[Course] = list()

    try:
        data = r.json()
    except json.decoder.JSONDecodeError as e:
        print("Invalid response from server when retrieving course list.")
        print(e)
        exit(1)

    try:
        for course in data["courses"]:
            courses.append(Course(id=course['id'], name=course['name'], url=course['url'][1:]))
    except KeyError as e:
        print("Invalid course list returned from server.")
        print("Missing key:", e)
        exit(1)

    return courses


def retrieveLevels(client: requests.sessions.Session, course: Course) -> List[Level]:
    """ Retrieve courses level ids from Memrise """
    print("Retrieving levels for course id:", course.id)
    r = client.get(BASE_URL + course.url + "edit/", timeout=60)
    course_html = html.fromstring(r.content)
    level_html = course_html.xpath("//div[@data-level-id]")
    levels = list()
    for level in level_html:
        levels.append(Level(int(level.attrib['data-level-id'])))
    return levels


def retrieveWords(client: requests.sessions.Session, level_id: int) -> List[Word]:
    """Retrieve level words from Memrise"""
    print("Retrieving words for level id:", level_id)
    r = client.get(BASE_URL + "ajax/level/editing_html/?level_id=" + str(level_id), timeout=60)
    data = r.json()
    tree = html.fromstring(data["rendered"])
    words_html = tree.xpath("//tr[contains(@class, 'thing')]")
    words = list()
    for word in words_html:
        word_id = word.attrib['data-thing-id']
        try:
            word_text = word.xpath("td[2]/div/div/text()")[0]
        except IndexError:
            print("Failed to get the word of item with id {}".format(str(word_id)))
            continue
        column_number = word.xpath("td[contains(@class, 'audio')]/@data-key")[0]
        has_audio = len(word.xpath(
            "td[contains(@class, 'audio')]/div/div[contains(@class, 'dropdown-menu')]/div")) > 0

        if not has_audio:
            words.append(Word(id=word_id, text=word_text, column_number=column_number))

    return words


def upload_audio(client: requests.sessions.Session,
                 word: Word, course_url: str, filename: str):
    """Upload audio file to Memrise server"""
    print("Uploading audio for word id:", word.id)
    referer = BASE_URL + course_url
    file = open(filename, 'rb')
    files = {'f': (filename, file, 'audio/mp3')}

    payload = {
        "thing_id": word.id,
        "cell_id": word.column_number,
        "cell_type": "column",
        "csrfmiddlewaretoken": client.cookies['csrftoken']}

    url = BASE_URL + "ajax/thing/cell/upload_file/"

    r = client.post(url, files=files, headers=dict(Referer=referer), data=payload, timeout=60)

    file.close()
    deleteFile(Path(filename))

    if r.status_code == 200:
        print("Audio created for word {}.".format(word.text))
        return True
    print("Audio creation failed for word {}.".format(word.text))
    return False


def main() -> None:
    """ Main program """

    mapi = MemriseAPI()
    username, password = get_credentials()
    mapi.login(username, password)
    courses = mapi.retrieve_courses()

    client = requests.session()

    gapi_client = create_client()

    for course in courses:
        counter = 0
        print(course.name)
        course.levels = retrieveLevels(client, course)
        for level in course.levels:
            level.words = retrieveWords(client, level.id)
            for word in level.words:
                filename = synthesize_text(word.text, gapi_client)
                if filename:
                    upload_audio(client, word, course.url, filename)
                    counter += 1
        print("{} audio files uploaded for course '{}'\n".format(counter, course.name))


if __name__ == "__main__":
    main()
