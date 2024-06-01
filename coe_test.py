import json
import requests
import tempfile
import winsound
import os
import wave
import pyaudio


# スピーカーIDを指定(0:つくよみちゃん)
styleId = 0
engine_api = "http://127.0.0.1:50032"
speaker = "3c37646f-3881-5374-2a83-149267990abc"

# 引数にセリフを指定
def speech_synthesis(text):
    # 音声合成
    response = requests.post(
        engine_api + '/v1/predict',
        json={
            'text': text,
            'speakerUuid': speaker,
            'styleId': styleId,
            'prosodyDetail': None,
            'speedScale': 1
        })

    # 一時ファイルを作成し、音声データを保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_file.write(response.content)
        temp_file_path = temp_file.name
    return temp_file_path

def play_audio(file_path):
    winsound.PlaySound(file_path, winsound.SND_FILENAME)
    os.remove(file_path)

def tts_and_play(text):
    print("tts_and_play")
    audio_file_path = speech_synthesis(text)
    play_audio(audio_file_path)

tts_and_play("こんにちは")