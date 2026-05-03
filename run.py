import os
import openai
import winsound
import sys
import pytchat
import time
import re
import pyaudio
import keyboard
import wave
import threading
import json
import socket
from emoji import demojize
from lm_studio import apply_openai_module, assert_lm_studio_reachable, load_lm_settings, pick_owner_name
from utils.translate import *
from utils.TTS import *
from utils.subtitle import *
from utils.promptMaker import *
from utils.twitch_config import *
from faster_whisper import WhisperModel

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY, LM_STUDIO_MODEL = load_lm_settings()
apply_openai_module(openai, LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY)
assert_lm_studio_reachable(LM_STUDIO_BASE_URL, LM_STUDIO_API_KEY)
print(f'LLM backend: LM Studio at {LM_STUDIO_BASE_URL} (model: {LM_STUDIO_MODEL})')

model_size = 'base'


def _make_whisper(device, compute_type):
    return WhisperModel(model_size, device=device, compute_type=compute_type)


def _init_whisper():
    pref = os.environ.get('WHISPER_DEVICE', 'auto').lower()
    if pref == 'cpu':
        print('Loading Whisper (CPU, WHISPER_DEVICE=cpu)...')
        return _make_whisper('cpu', 'int8')
    if pref == 'cuda':
        print('Loading Whisper (CUDA, WHISPER_DEVICE=cuda)...')
        return _make_whisper('cuda', 'float16')
    print('Loading Whisper (auto: CUDA if available)...')
    try:
        return _make_whisper('cuda', 'float16')
    except Exception as e:
        print('Whisper CUDA init failed ({0}); using CPU.'.format(e))
        return _make_whisper('cpu', 'int8')


print('Loading local Whisper model...')
whisper_model = _init_whisper()
print('Whisper model loaded.')

conversation = []
history = {'history': conversation}

mode = 0
total_characters = 0
chat = ''
chat_now = ''
chat_prev = ''
is_Speaking = False
owner_name = pick_owner_name()
blacklist = ['Nightbot', 'streamelements']

def record_audio():
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    WAVE_OUTPUT_FILENAME = 'input.wav'
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    print('Recording...')
    while keyboard.is_pressed('RIGHT_SHIFT'):
        data = stream.read(CHUNK)
        frames.append(data)
    print('Stopped recording.')
    stream.stop_stream()
    stream.close()
    p.terminate()
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    transcribe_audio('input.wav')

def _transcribe_to_text(path):
    segments, info = whisper_model.transcribe(path, beam_size=5)
    text = ''
    for segment in segments:
        text += segment.text
    return text


def transcribe_audio(file):
    global chat_now, whisper_model
    try:
        chat_now = _transcribe_to_text(file)
    except Exception as e:
        msg = str(e).lower()
        force_cuda = os.environ.get('WHISPER_DEVICE', 'auto').lower() == 'cuda'
        gpu_runtime_issue = any(
            k in msg for k in ('cublas', 'cudnn', 'nvrtc', 'cuda', 'cudart')
        )
        if not force_cuda and gpu_runtime_issue:
            print(
                'Whisper failed on GPU ({0}). Reloading on CPU (install CUDA/cuBLAS for GPU).'.format(
                    e
                )
            )
            whisper_model = _make_whisper('cpu', 'int8')
            try:
                chat_now = _transcribe_to_text(file)
            except Exception as e2:
                print('Error transcribing audio locally: {0}'.format(e2))
                return
        else:
            print('Error transcribing audio locally: {0}'.format(e))
            return
    print('Question: ' + chat_now)
    result = owner_name + ' said ' + chat_now
    conversation.append({'role': 'user', 'content': result})
    openai_answer()

def openai_answer():
    global total_characters, conversation
    total_characters = sum(len(d['content']) for d in conversation)
    while total_characters > 4000:
        try:
            conversation.pop(2)
            total_characters = sum(len(d['content']) for d in conversation)
        except Exception as e:
            print('Error removing old messages: {0}'.format(e))
    with open('conversation.json', 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4)
    prompt = getPrompt()
    response = openai.ChatCompletion.create(model=LM_STUDIO_MODEL, messages=prompt, max_tokens=128, temperature=1, top_p=0.9)
    message = response['choices'][0]['message']['content']
    conversation.append({'role': 'assistant', 'content': message})
    translate_text(message)

def yt_livechat(video_id):
        global chat
        live = pytchat.create(video_id=video_id)
        while live.is_alive():
            try:
                for c in live.get().sync_items():
                    if c.author.name in blacklist: continue
                    if not c.message.startswith('!'):
                        chat_raw = re.sub(r':[^\s]+:', '', c.message)
                        chat_raw = chat_raw.replace('#', '')
                        chat = c.author.name + ' berkata ' + chat_raw
                        print(chat)
                    time.sleep(1)
            except Exception as e:
                print('Error receiving chat: {0}'.format(e))

def twitch_livechat():
    global chat
    sock = socket.socket()
    sock.connect((server, port))
    sock.send(f'PASS {token}\n'.encode('utf-8'))
    sock.send(f'NICK {nickname}\n'.encode('utf-8'))
    sock.send(f'JOIN {channel}\n'.encode('utf-8'))
    regex = r':(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :(.+)'
    while True:
        try:
            resp = sock.recv(2048).decode('utf-8')
            if resp.startswith('PING'): sock.send('PONG\n'.encode('utf-8'))
            elif not user in resp:
                resp = demojize(resp)
                match = re.match(regex, resp)
                username = match.group(1)
                message = match.group(2)
                if username in blacklist: continue
                chat = username + ' said ' + message
                print(chat)
        except Exception as e:
            print('Error receiving chat: {0}'.format(e))

def translate_text(text):
    global is_Speaking
    detect = detect_google(text)
    tts = translate_google(text, f'{detect}', 'JA')
    tts_en = translate_google(text, f'{detect}', 'EN')
    try:
        print('JP Answer: ' + tts)
        print('EN Answer: ' + tts_en)
    except Exception as e: print('Error printing text: {0}'.format(e)); return
    silero_tts(tts_en, 'en', 'v3_en', 'en_21')
    generate_subtitle(chat_now, text)
    time.sleep(1)
    is_Speaking = True
    winsound.PlaySound('test.wav', winsound.SND_FILENAME)
    is_Speaking = False
    time.sleep(1)
    with open ('output.txt', 'w') as f: f.truncate(0)
    with open ('chat.txt', 'w') as f: f.truncate(0)

def preparation():
    global conversation, chat_now, chat, chat_prev
    while True:
        chat_now = chat
        if is_Speaking == False and chat_now != chat_prev:
            conversation.append({'role': 'user', 'content': chat_now})
            chat_prev = chat_now
            openai_answer()
        time.sleep(1)

if __name__ == '__main__':
    try:
        mode = input('Mode (1-Mic, 2-Youtube Live, 3-Twitch Live): ')
        if mode == '1':
            print('Press and Hold Right Shift to record audio')
            while True:
                if keyboard.is_pressed('RIGHT_SHIFT'): record_audio()
        elif mode == '2':
            live_id = input('Livestream ID: ')
            t = threading.Thread(target=preparation)
            t.start()
            yt_livechat(live_id)
        elif mode == '3':
            print('To use this mode, make sure to change utils/twitch_config.py to your own config')
            t = threading.Thread(target=preparation)
            t.start()
            twitch_livechat()
    except KeyboardInterrupt:
        if 't' in locals(): t.join()
        print('Stopped')

