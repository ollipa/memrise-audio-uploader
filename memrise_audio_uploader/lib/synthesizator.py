"""Google Text-To-Speech voice synthesizator."""
from typing import List

import pydantic
from google.cloud import texttospeech


class Voice(pydantic.BaseModel):
    """Synthesizator voice."""

    language_code: str
    name: str
    gender: texttospeech.SsmlVoiceGender


class Synthesizator:
    """Google Text-To-Speech voice synthesizator client."""

    def __init__(self) -> None:
        self._client = texttospeech.TextToSpeechClient()

    def list_voices(self, language_code: str) -> List[Voice]:
        """List available voices for given language code."""
        response = self._client.list_voices(language_code=language_code, timeout=30.0)
        voices = [
            Voice(
                language_code=voice.language_codes.pop(),
                name=voice.name,
                gender=voice.ssml_gender,
            )
            for voice in response.voices
        ]
        return voices

    def synthesize(self, text: str, voice: Voice) -> bytes:
        """Synthesizes text and returns the voice as an mp3 file."""
        input_text = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=voice.language_code,
            name=voice.name,
            ssml_gender=voice.gender,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=0.75
        )

        request = texttospeech.SynthesizeSpeechRequest(
            input=input_text, voice=voice, audio_config=audio_config
        )
        response = self._client.synthesize_speech(request=request)
        return bytes(response.audio_content)
