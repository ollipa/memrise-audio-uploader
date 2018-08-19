"""Google Text-To-Speech voice synthesizator"""
import logging

from google.cloud import texttospeech
import google


def synthesize_text(text, client):
    """Synthesizes speech from the input string of text."""
    input_text = texttospeech.types.SynthesisInput(text=text)

    voice = texttospeech.types.VoiceSelectionParams(
        language_code='ko-KR',
        name="ko-KR-Wavenet-A",
        ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)

    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3,
        speaking_rate=0.75)

    try:
        response = client.synthesize_speech(input_text, voice, audio_config)
    except google.api_core.exceptions.GoogleAPIError as exc:
        logging.error("Google API Error: %s", exc)
        return False

    return response.audio_content


def create_client():
    """Create client  to cache authentication."""
    client = texttospeech.TextToSpeechClient()
    return client
