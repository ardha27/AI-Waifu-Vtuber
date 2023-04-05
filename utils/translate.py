import requests
import json
import sys
import googletrans

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

# You can use DeepL or Google Translate to translate the text
# DeepL can translate more casual text in Japanese
# DeepLx is a free and open-source DeepL API, i use this because DeepL Pro is not available in my country
# but sometimes i'm facing request limit, so i use Google Translate as a backup
def translate_deeplx(text, source, target):
    url = "http://localhost:1188/translate"
    headers = {"Content-Type": "application/json"}

    # define the parameters for the translation request
    params = {
        "text": text,
        "source_lang": source,
        "target_lang": target
    }

    # convert the parameters to a JSON string
    payload = json.dumps(params)

    # send the POST request with the JSON payload
    response = requests.post(url, headers=headers, data=payload)

    # get the response data as a JSON object
    data = response.json()

    # extract the translated text from the response
    translated_text = data['data']

    return translated_text

def translate_google(text, source, target):
    try:
        translator = googletrans.Translator()
        result = translator.translate(text, src=source, dest=target)
        return result.text
    except:
        print("Error translate")
        return
    
def detect_google(text):
    try:
        translator = googletrans.Translator()
        result = translator.detect(text)
        return result.lang.upper()
    except:
        print("Error detect")
        return

if __name__ == "__main__":
    text = "aku tidak menyukaimu"
    source = translate_deeplx(text, "ID", "JA")
    print(source)
