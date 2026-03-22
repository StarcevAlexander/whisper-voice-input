"""
Голосовой ввод через Whisper — два режима работы:

  Режим 1 — Голосовые команды (фоновый, без кнопок):
    Скажите "слушай центральная" — начнётся запись.
    Скажите "конец связи"        — запись остановится, текст вставится в активное поле.

  Режим 2 — Кнопка F9 (удерживать):
    Удерживайте F9 — идёт запись.
    Отпустите F9   — текст вставится в активное поле.

Требует установки:
  pip install vosk sounddevice openai-whisper pyperclip keyboard numpy
  Скачать модель Vosk для русского: https://alphacephei.com/vosk/models
  (vosk-model-small-ru-0.22 — маленькая и быстрая)
"""

import time
import queue
import threading
import json
import numpy as np
import sounddevice as sd
import whisper
import pyperclip
import keyboard
from vosk import Model, KaldiRecognizer

# ── Настройки ──────────────────────────────────────────────────────────────
WHISPER_MODEL   = "base"            # tiny / base / small / medium / large
VOSK_MODEL_PATH = r"C:\Users\master\vosk-model-small-ru-0.22"
SAMPLE_RATE     = 16000
LANGUAGE        = "ru"

WAKE_PHRASE = "слушай центральная"
STOP_PHRASE = "конец связи"

# Минимальное расстояние Левенштейна для нечёткого совпадения фраз
MATCH_THRESHOLD = 0.6

# Режим работы: "voice" — голосовые команды, "hotkey" — кнопка F9
MODE   = "voice"   # "voice" | "hotkey"
HOTKEY = "f9"
# ───────────────────────────────────────────────────────────────────────────


def levenshtein_ratio(a: str, b: str) -> float:
    """Возвращает коэффициент сходства двух строк (0..1)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev[j - 1] + cost)
    return 1 - dp[n] / max(m, n)


def phrase_in_text(phrase: str, text: str) -> bool:
    """Проверяет, содержится ли фраза в тексте (точно или нечётко)."""
    text = text.lower().strip()
    phrase = phrase.lower().strip()
    if phrase in text:
        return True
    # Нечёткое: ищем совпадение по скользящему окну размером с фразу
    words_phrase = phrase.split()
    words_text   = text.split()
    wlen = len(words_phrase)
    for i in range(len(words_text) - wlen + 1):
        window = " ".join(words_text[i: i + wlen])
        if levenshtein_ratio(phrase, window) >= MATCH_THRESHOLD:
            return True
    return False


def load_models():
    print(f"Загрузка Vosk модели из '{VOSK_MODEL_PATH}'...")
    vosk_model = Model(VOSK_MODEL_PATH)
    print(f"Загрузка Whisper модели '{WHISPER_MODEL}'...")
    whisper_model = whisper.load_model(WHISPER_MODEL)
    return vosk_model, whisper_model


class VoiceAssistant:
    def __init__(self, vosk_model, whisper_model):
        self.vosk_model    = vosk_model
        self.whisper_model = whisper_model
        self.state         = "waiting"   # waiting | recording
        self.record_frames = []
        self.audio_queue   = queue.Queue()

    def _recognizer(self):
        return KaldiRecognizer(self.vosk_model, SAMPLE_RATE)

    def run(self):
        print(f'\nГотово! Скажите "{WAKE_PHRASE}" чтобы начать запись.')
        print(f'Скажите "{STOP_PHRASE}" чтобы завершить и распознать.')
        print("Ctrl+C — выход.\n")

        rec = self._recognizer()

        def audio_callback(indata, frames, time_info, status):
            self.audio_queue.put(bytes(indata))

        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=4000,
            dtype="int16",
            channels=1,
            callback=audio_callback,
        ):
            while True:
                data = self.audio_queue.get()

                if self.state == "recording":
                    # Сохраняем аудио для Whisper
                    arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                    self.record_frames.append(arr)

                if rec.AcceptWaveform(data):
                    result_text = json.loads(rec.Result()).get("text", "")
                else:
                    result_text = json.loads(rec.PartialResult()).get("partial", "")

                if not result_text:
                    continue

                if self.state == "waiting":
                    if phrase_in_text(WAKE_PHRASE, result_text):
                        print(f'[Vosk] Услышано: "{result_text}"')
                        print("Запись началась... Говорите!")
                        self.state = "recording"
                        self.record_frames = []
                        rec = self._recognizer()  # сброс распознавателя

                elif self.state == "recording":
                    if phrase_in_text(STOP_PHRASE, result_text):
                        print(f'[Vosk] Услышано: "{result_text}"')
                        print("Запись остановлена. Распознаю через Whisper...")
                        self.state = "waiting"
                        self._transcribe_and_paste()
                        rec = self._recognizer()

    def _transcribe_and_paste(self):
        if not self.record_frames:
            print("Запись пустая, пропускаю.\n")
            return

        audio = np.concatenate(self.record_frames)
        if len(audio) < SAMPLE_RATE * 0.5:
            print("Слишком короткая запись, пропускаю.\n")
            return

        result = self.whisper_model.transcribe(audio, language=LANGUAGE, fp16=False)
        text = result["text"].strip()

        # Убираем стоп-фразу из конца, если Whisper её тоже захватил
        for stop in [STOP_PHRASE, "конец"]:
            idx = text.lower().rfind(stop)
            if idx != -1:
                text = text[:idx].strip()

        if text:
            print(f"Распознано: {text}\n")
            pyperclip.copy(text)
            keyboard.press_and_release("ctrl+v")
        else:
            print("Ничего не распознано.\n")


def run_hotkey_mode(whisper_model):
    """Режим удержания F9: запись пока кнопка нажата."""
    print(f"Режим кнопки. Удерживайте {HOTKEY.upper()} для записи речи.")
    print("Ctrl+C — выход.\n")
    while True:
        keyboard.wait(HOTKEY)
        print("Запись... (отпустите кнопку чтобы завершить)")
        audio_frames = []
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
            while keyboard.is_pressed(HOTKEY):
                data, _ = stream.read(1024)
                audio_frames.append(data.copy())
                time.sleep(0.01)
        print("Распознавание...")
        audio = np.concatenate(audio_frames, axis=0).flatten()
        if len(audio) < SAMPLE_RATE * 0.3:
            print("Слишком короткая запись, пропускаю.\n")
            continue
        result = whisper_model.transcribe(audio, language=LANGUAGE, fp16=False)
        text = result["text"].strip()
        if text:
            print(f"Распознано: {text}")
            pyperclip.copy(text)
            keyboard.press_and_release("ctrl+v")
        else:
            print("Ничего не распознано.")
        print()


if __name__ == "__main__":
    try:
        if MODE == "hotkey":
            print(f"Загрузка Whisper модели '{WHISPER_MODEL}'...")
            whisper_model = whisper.load_model(WHISPER_MODEL)
            print("Готово!")
            run_hotkey_mode(whisper_model)
        else:
            vosk_model, whisper_model = load_models()
            assistant = VoiceAssistant(vosk_model, whisper_model)
            assistant.run()
    except KeyboardInterrupt:
        print("\nВыход.")
