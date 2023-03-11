import deepl
import urllib
import urllib.parse
import urllib.request
import requests
import openai
import winsound
import sys
import pytchat
import time
import re
import pyaudio
import keyboard
import wave
from config import *

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

openai.api_key = api_key #API From OpenAI
translator = deepl.Translator(auth_key) #API from DeepL

conversation = [{"role": "system", "content": "you are an AI Waifu Vtuber called Pina. You reply with brief, to-the-point answers with no elaboration."}]
total_characters = 0
chat_raw = ""

def record_audio():
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    RECORD_SECONDS = 5
    WAVE_OUTPUT_FILENAME = "input.wav"
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    frames = []
    print("Recording...")
    while keyboard.is_pressed('RIGHT_SHIFT'):
        data = stream.read(CHUNK)
        frames.append(data)
    print("Stopped recording.")
    stream.stop_stream()
    stream.close()
    p.terminate()
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    transcribe_audio("input.wav")

def transcribe_audio(file):
    try:
        audio_file= open(file, "rb")
        transcript = openai.Audio.translate("whisper-1", audio_file)
    except:
        print("Error transcribing audio")
    chat_raw = transcript.text
    openai_answer(chat_raw)
    # translate_text(transcript.text)

def openai_answer(chat):
    result = translator.translate_text(chat, target_lang="EN-US")
    print ("Question: " + result.text)
    conversation.append({"role": "user", "content": result.text})
    total_characters = sum(len(d['content']) for d in conversation)

    while total_characters > 4000 and len(conversation) > 1:
        # remove the second dictionary from the list
        conversation.pop(1)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation,
        max_tokens=500,
        temperature=1,
        top_p=0.9
    )
    conversation.append({"role": "assistant", "content": response['choices'][0]['message']['content']})
    message = response['choices'][0]['message']['content']
    translate_text(message)

def translate_text(text):
    result_id = translator.translate_text(text, target_lang="ID")
    print("ID Answer: " + result_id.text)
    result_jp = translator.translate_text(text, target_lang="JA")
    print("JP Answer: " + result_jp.text)
    speech_text(result_jp.text, result_id.text)

def speech_text(result_jp, result_id):
    # Install and run 
    # http://127.0.0.1:50021/docs API Docs
    params_encoded = urllib.parse.urlencode({'text': result_jp, 'speaker': 46})
    request = requests.post(f'http://127.0.0.1:50021/audio_query?{params_encoded}')
    params_encoded = urllib.parse.urlencode({'speaker': 46, 'enable_interrogative_upspeak': True})
    request = requests.post(f'http://127.0.0.1:50021/synthesis?{params_encoded}', json=request.json())

    with open("output.wav", "wb") as outfile:
        outfile.write(request.content)

    with open("output.txt", "w") as outfile:
        text = result_id
        text = text.replace("?", "?\n")
        text = text.replace("!", "!\n")
        text = text.replace(".", ".\n")
        outfile.write(text)

    with open("chat.txt", "w") as outfile:
        outfile.write(chat_raw)

    winsound.PlaySound("output.wav", winsound.SND_FILENAME)

    time.sleep(1)
    with open ("output.txt", "w") as f:
        f.truncate(0)
    with open ("chat.txt", "w") as f:
        f.truncate(0)

if __name__ == "__main__":

    mode = input("Mode (1-Mic, 2-Youtube Live): ")

    if mode == "1":
        print("Press Right Shift to record audio")
        while True:
            if keyboard.is_pressed('RIGHT_SHIFT'):
                record_audio()
        
    elif mode == "2":
        live_id = input("Livestream ID: ")
        live = pytchat.create(video_id=live_id)
        while live.is_alive():
            for c in live.get().sync_items():
                if c.author.isChatOwner or c.author.name == 'Nightbot':
                    continue
                chat_raw = c.author.name + ': ' + c.message
                chat = re.sub(r':[^\s]+:', '', c.message)
                if len(chat) > 5:
                    chat = c.author.name + ' berkata: ' + chat
                    print(chat)
                    openai_answer(chat)
            

