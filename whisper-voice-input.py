"""
Голосовой ввод через Whisper — оба способа работают одновременно:

  Способ 1 — Голосовые команды:
    Скажите "центральная" — начнётся запись.
    Скажите "исполнять"   — запись остановится, текст вставится в активное поле.

  Способ 2 — Кнопка F9:
    Удерживайте F9 — идёт запись.
    Отпустите F9   — текст вставится в активное поле.

Защита от повторного запуска: допускается только один экземпляр скрипта.

Требует установки:
  pip install vosk sounddevice openai-whisper pyperclip keyboard numpy pygame
  Скачать модель Vosk для русского: https://alphacephei.com/vosk/models
  (vosk-model-small-ru-0.22 — маленькая и быстрая)
"""

import sys
import os
import time
import queue
import threading
import msvcrt
import json
import numpy as np
import sounddevice as sd
import whisper
import pyperclip
import keyboard
import pygame
from vosk import Model, KaldiRecognizer

# ── Настройки ──────────────────────────────────────────────────────────────
WHISPER_MODEL   = "base"            # tiny / base / small / medium / large
VOSK_MODEL_PATH = r"C:\Users\master\vosk-model-small-ru-0.22"
SAMPLE_RATE     = 16000
LANGUAGE        = "ru"

WAKE_PHRASE = "центральная"
STOP_PHRASE = "исполнять"

# Минимальное расстояние Левенштейна для нечёткого совпадения фраз
MATCH_THRESHOLD = 0.6

HOTKEY = "f9"

# ───────────────────────────────────────────────────────────────────────────

# ── Звуковые сигналы ─────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOUND_START = os.path.join(_SCRIPT_DIR, "sound_done.mp3")
SOUND_DONE  = os.path.join(_SCRIPT_DIR, "sound_start.mp3")

pygame.mixer.init()
_sound_lock = threading.Lock()


def play_sound(path: str, wait: bool = True):
    """Проигрывает mp3-файл. wait=True — ждёт окончания воспроизведения."""
    with _sound_lock:
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            if wait:
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
        except Exception as e:
            print(f"[Sound] Ошибка воспроизведения: {e}")


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
    def __init__(self, vosk_model, whisper_model, busy_lock):
        self.vosk_model    = vosk_model
        self.whisper_model = whisper_model
        self.state         = "waiting"   # waiting | recording
        self.record_frames = []
        self.audio_queue   = queue.Queue()
        self.busy_lock     = busy_lock   # общий lock с hotkey-потоком

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
                        if not self.busy_lock.acquire(blocking=False):
                            print("[Voice] Пропуск: F9 режим занят")
                            continue
                        print(f'[Voice] Услышано: "{result_text}" → активация')
                        play_sound(SOUND_START)
                        print("[Voice] Запись началась... Говорите!")
                        self.state = "recording"
                        self.record_frames = []
                        rec = self._recognizer()

                elif self.state == "recording":
                    if phrase_in_text(STOP_PHRASE, result_text):
                        print(f'[Voice] Услышано: "{result_text}" → стоп')
                        print(f"[Voice] Фреймов записано: {len(self.record_frames)}")
                        self.state = "waiting"
                        self._transcribe_and_paste()
                        play_sound(SOUND_DONE)
                        self.busy_lock.release()
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
        for stop in [STOP_PHRASE, "исполнять", "исполняй", "конец"]:
            idx = text.lower().rfind(stop)
            if idx != -1:
                text = text[:idx].strip()

        if text:
            print(f"Распознано: {text}\n")
            pyperclip.copy(text)
            keyboard.press_and_release("ctrl+v")
        else:
            print("Ничего не распознано.\n")


def run_hotkey_mode(whisper_model, busy_lock):
    """Режим удержания F9: удерживать — запись, отпустить — распознавание."""
    while True:
        keyboard.wait(HOTKEY)
        print("[F9] Нажата клавиша")

        if not busy_lock.acquire(blocking=False):
            print("[F9] Пропуск: голосовой режим занят")
            continue

        try:
            # Стартовый звук в фоне — не блокирует начало записи
            play_sound(SOUND_START, wait=False)

            print("[F9] Запись... (удерживайте, отпустите для остановки)")
            audio_frames = []
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
                while keyboard.is_pressed(HOTKEY):
                    data, _ = stream.read(1024)
                    audio_frames.append(data.copy())
                    time.sleep(0.005)

            print(f"[F9] Кнопка отпущена. Фреймов: {len(audio_frames)}")

            if not audio_frames:
                print("[F9] Пустая запись, пропускаю.")
                continue

            audio = np.concatenate(audio_frames, axis=0).flatten()
            duration = len(audio) / SAMPLE_RATE
            print(f"[F9] Длительность: {duration:.1f}с")

            if duration < 0.3:
                print("[F9] Слишком короткая запись, пропускаю.")
                continue

            print("[F9] Распознавание через Whisper...")
            result = whisper_model.transcribe(audio, language=LANGUAGE, fp16=False)
            text = result["text"].strip()
            print(f"[F9] Whisper вернул: '{text}'")

            if text:
                pyperclip.copy(text)
                keyboard.press_and_release("ctrl+v")
                print(f"[F9] Текст вставлен: {text}")
                play_sound(SOUND_DONE)
            else:
                print("[F9] Ничего не распознано.")
        finally:
            busy_lock.release()


def ensure_single_instance():
    """Гарантирует, что запущен только один экземпляр скрипта."""
    lock_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".lock")
    try:
        lock_file = open(lock_path, "w")
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        return lock_file  # держим файл открытым
    except (OSError, IOError):
        print("Скрипт уже запущен. Выход.")
        sys.exit(0)


if __name__ == "__main__":
    _lock = ensure_single_instance()
    try:
        vosk_model, whisper_model = load_models()
        busy_lock = threading.Lock()

        # F9 в отдельном потоке
        hotkey_thread = threading.Thread(
            target=run_hotkey_mode,
            args=(whisper_model, busy_lock),
            daemon=True,
        )
        hotkey_thread.start()
        print(f"[F9] Кнопка {HOTKEY.upper()} активна.")

        # Голосовые команды в основном потоке
        assistant = VoiceAssistant(vosk_model, whisper_model, busy_lock)
        assistant.run()
    except KeyboardInterrupt:
        print("\nВыход.")
