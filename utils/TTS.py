import os
import torch
import requests
import urllib.parse
from utils.katakana import *


# MiniMax TTS voice IDs
MINIMAX_VOICES = [
    "English_Graceful_Lady",
    "English_Insightful_Speaker",
    "English_radiant_girl",
    "English_Persuasive_Man",
    "English_Lucky_Robot",
    "Wise_Woman",
    "cute_boy",
    "lovely_girl",
    "Friendly_Person",
    "Inspirational_girl",
    "Deep_Voice_Man",
    "sweet_girl",
]


def minimax_tts(text, voice_id="lovely_girl", model="speech-2.8-hd", output_file="test.wav"):
    """
    Generate speech using MiniMax Cloud TTS (T2A v2 API).

    Requires MINIMAX_API_KEY env var or api_key in config.py.

    Args:
        text: Text to convert to speech.
        voice_id: One of MINIMAX_VOICES (default: "lovely_girl").
        model: "speech-2.8-hd" (high quality) or "speech-2.8-turbo" (fast).
        output_file: Output audio file path.
    """
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        try:
            from config import api_key as config_key
            api_key = config_key
        except ImportError:
            pass

    if not api_key:
        raise ValueError("MINIMAX_API_KEY env var or api_key in config.py required for MiniMax TTS")

    url = "https://api.minimax.io/v1/t2a_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "text": text,
        "voice_setting": {
            "voice_id": voice_id,
        },
        "audio_setting": {
            "format": "mp3",
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    audio_hex = data.get("data", {}).get("audio", "")
    if not audio_hex:
        raise RuntimeError(f"MiniMax TTS returned no audio data: {data}")

    audio_bytes = bytes.fromhex(audio_hex)
    with open(output_file, "wb") as f:
        f.write(audio_bytes)

# https://github.com/snakers4/silero-models#text-to-speech
def silero_tts(tts, language, model, speaker):
    device = torch.device('cpu')
    torch.set_num_threads(4)
    local_file = 'model.pt'

    if not os.path.isfile(local_file):
        torch.hub.download_url_to_file(f'https://models.silero.ai/models/tts/{language}/{model}.pt',
                                    local_file)  

    model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
    model.to(device)

    example_text = "i'm fine thank you and you?"
    sample_rate = 48000

    audio_paths = model.save_wav(text=tts,
                                speaker=speaker,
                                sample_rate=sample_rate)
    
def voicevox_tts(tts):
    # You need to run VoicevoxEngine.exe first before running this script
    
    voicevox_url = 'http://localhost:50021'
    # Convert the text to katakana. Example: ORANGE -> オレンジ, so the voice will sound more natural
    katakana_text = katakana_converter(tts)
    # You can change the voice to your liking. You can find the list of voices on speaker.json
    # or check the website https://voicevox.hiroshiba.jp
    params_encoded = urllib.parse.urlencode({'text': katakana_text, 'speaker': 46})
    request = requests.post(f'{voicevox_url}/audio_query?{params_encoded}')
    params_encoded = urllib.parse.urlencode({'speaker': 46, 'enable_interrogative_upspeak': True})
    request = requests.post(f'{voicevox_url}/synthesis?{params_encoded}', json=request.json())

    with open("test.wav", "wb") as outfile:
        outfile.write(request.content)

if __name__ == "__main__":
    silero_tts()
