"""Google Text-To-Speech voice synthesizator"""
from google.cloud import texttospeech

def synthesize_text(text, client):
    """Synthesizes speech from the input string of text."""
    input_text = texttospeech.types.SynthesisInput(text=text)

    voice = texttospeech.types.VoiceSelectionParams(
        language_code='ko-KR',
        ssml_gender=texttospeech.enums.SsmlVoiceGender.FEMALE)

    audio_config = texttospeech.types.AudioConfig(
        audio_encoding=texttospeech.enums.AudioEncoding.MP3,
        speaking_rate=0.75)

    response = client.synthesize_speech(input_text, voice, audio_config)

    filename = 'output.mp3'

    # The response's audio_content is binary.
    with open(filename, 'wb') as out:
        out.write(response.audio_content)
        return filename

    return False

def create_client():
    """Create client  to cache authentication."""
    client = texttospeech.TextToSpeechClient()
    return client
