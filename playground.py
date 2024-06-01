import requests
import json
import tempfile
import winsound
import os

speaker = "292ea286-3d5f-f1cc-157c-66462a6a9d08"

def tts(text):
    print("tts")
    # 音声合成
    synthesis = requests.post(
        f'http://127.0.0.1:50032/synthesis',
        headers = {"Content-Type": "application/json"},
        data=(('text', text),('speakerUuid', speaker),('styleId,','1'))
    )
    # 一時ファイルを作成し、音声データを保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_file.write(synthesis.content)
        temp_file_path = temp_file.name
    return temp_file_path

def play_audio(file_path):
    print("play_audio")
    winsound.PlaySound(file_path, winsound.SND_FILENAME)
    print(file_path)
    os.remove(file_path)

def tts_and_play(text):
    print("tts_and_play")
    audio_file_path = tts(text)
    play_audio(audio_file_path)
  
tts_and_play("こんにちは")