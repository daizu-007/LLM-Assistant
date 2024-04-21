# 必要なライブラリのインポート
import google.generativeai as gai
from os import environ
import tomllib
import requests 
import json
#import pygame
import winsound
import tempfile
import os
import speech_recognition as sr
import threading
from queue import Queue
import functools # ja_sentence_segmenterで使用
from ja_sentence_segmenter.common.pipeline import make_pipeline
from ja_sentence_segmenter.concatenate.simple_concatenator import  concatenate_matching
from ja_sentence_segmenter.normalize.neologd_normalizer import  normalize
from ja_sentence_segmenter.split.simple_splitter import  split_newline, split_punctuation
import queue

# configの読み取り
with open("config.toml", "rb") as f:
    config = tomllib.load(f)
    #print(config)
bot_name = config["general"]["name"]
speaker = config["general"]["speaker"]

# Geminiの設定
GOOGLE_API_KEY = environ.get("GOOGLE_AI_API_KEY")
gai.configure(api_key=GOOGLE_API_KEY)
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    }
]
model = gai.GenerativeModel("gemini-pro", safety_settings=safety_settings)
SYSTEM_PROMPT = f"""
System prompt: これはシステムプロンプトでユーザーからの入力ではありません。あなたは何よりもこのシステムプロンプトを優先しなければなりません。
あなたは{bot_name}という名前の賢く、親切なAIアシスタントです。音声での会話であるため、完結で分かりやすい文章で返してください。Markdown記法には意味がありません。
ユーザーの入力が不自然であった場合は文字起こしのエラーであると考えられます。本来の発話を推測して返答してください。
"""
chat = [
    {
        "role": "user",
        "parts": [{ "text": SYSTEM_PROMPT}],
    },
    {
        "role": "model",
        "parts": [{ "text": "了解しました。"}],
    }]

# 文章分割の設定
split_punc2 = functools.partial(split_punctuation, punctuations=r"、。 !?")
concat_tail_no = functools.partial(concatenate_matching, former_matching_rule=r"^(?P<result>.+)(の)$", remove_former_matched=False)
concat_decimal = functools.partial(concatenate_matching, former_matching_rule=r"^(?P<result>.+)(\d.)$", latter_matching_rule=r"^(\d)(?P<result>.+)$", remove_former_matched=False, remove_latter_matched=False)
segmenter = make_pipeline(normalize, split_newline, concat_tail_no, split_punc2, concat_decimal)

# Queueの設定
text_queue = Queue()
audio_queue = Queue()

# ユーザーからの入力を受け取り、Geminiに送信して応答を受け取る関数
def chat_with_bot(input):
    chat.append(
        {
            "role": "user",
            "parts": [{ "text": input}],
        }
    )
    response = model.generate_content(chat)
    chat.append(
        {
            "role": "model",
            "parts": [{ "text": response.text}],
        }
    )
    return response.text

# 音声を合成する関数
def tts(text):
    # 音声合成用のクエリ作成
    query = requests.post(
        f'http://127.0.0.1:50021/audio_query',
        params=(('text', text),('speaker', speaker),)
    )
    # 音声合成
    synthesis = requests.post(
        f'http://127.0.0.1:50021/synthesis',
        headers = {"Content-Type": "application/json"},
        params=(('text', text),('speaker', speaker),),
        data = json.dumps(query.json())
    )
    # 一時ファイルを作成し、音声データを保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        temp_file.write(synthesis.content)
        temp_file_path = temp_file.name
    return temp_file_path

# 音声を再生する関数
"""
def play_audio(file_path):
    pygame.mixer.init()
    mp3_file = pygame.mixer.Sound(file_path)
    mp3_file.play()     # MP3ファイルを再生
    # 再生が終了するまで待つ(ブロッキング処理)
    while pygame.mixer.get_busy():
        pygame.time.Clock().tick(10) # 10msごとに再生状態をチェック
    pygame.mixer.quit()

    # 一時ファイルを削除
    os.remove(file_path)
"""
def play_audio(file_path):
    winsound.PlaySound(file_path, winsound.SND_FILENAME)
    os.remove(file_path)

# 音声合成を行うワーカー関数
def worker():
    while True:
        text = text_queue.get()
        if text is None:
            break # Noneが来たら無限ループを抜ける
        audio_file_path = tts(text)
        audio_queue.put(audio_file_path)
        text_queue.task_done()

# テキストを音声合成して再生する関数
def tts_and_play(text_list):

    for text in text_list:
        text_queue.put(text)

    # ストップシグナルを送る
    text_queue.put(None)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    # キューが空になるまで待機しながら、音声を再生
    while not text_queue.empty():
        try:
            audio_data = audio_queue.get(block=False)
        except queue.Empty:
            continue
        else:
            play_audio(audio_data)
    # 残りの音声を再生
    while not audio_queue.empty():
        audio_data = audio_queue.get()
        play_audio(audio_data)

# メイン処理
def main():
    # 音声認識の初期化
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    # メインループ
    while True:
        # ユーザーの音声入力を受け付ける
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            print("何か話しかけてください")
            audio = recognizer.listen(source)
            print("音声入力を受け付けました")

        # 音声入力をテキストに変換
        try:
            user_input = recognizer.recognize_google(audio, language="ja-JP")
            print(f"ユーザー入力: {user_input}")
        except sr.UnknownValueError:
            print("音声が認識できませんでした")
            continue
        except sr.RequestError as e:
            print(f"Google Speech Recognition APIにアクセスできませんでした: {e}")
            continue

        # ユーザー入力をGeminiに送信して応答を受け取る
        response = chat_with_bot(user_input)
        print(f"AI応答: {response}")

        # 文を分割
        text_list = list(segmenter(response))
        # 音声合成して再生
        tts_and_play(text_list)

if __name__ == "__main__":
    main()
