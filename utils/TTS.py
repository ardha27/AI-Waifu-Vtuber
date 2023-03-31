import os
import torch
import requests
import urllib.parse
from utils.katakana import *

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
