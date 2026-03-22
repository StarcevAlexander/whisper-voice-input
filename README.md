# Whisper Voice Input

Голосовой ввод текста для Windows на базе **Vosk** + **OpenAI Whisper**.
Поддерживает два режима работы: голосовые команды-активаторы и удержание кнопки F9.

---

## Режимы работы

### Режим 1 — Голосовые команды (`MODE = "voice"`)

Скрипт работает в фоне и постоянно слушает микрофон через лёгкую модель Vosk (почти 0% CPU).

| Действие | Результат |
|---|---|
| Скажите **"слушай центральная"** | Начинается запись |
| Скажите **"конец связи"** | Запись останавливается, текст распознаётся через Whisper и вставляется в активное поле |

Поддерживается **нечёткое распознавание** ключевых фраз — не нужно произносить их идеально точно.

---

### Режим 2 — Кнопка F9 (`MODE = "hotkey"`)

Простой режим без голосовых команд и без Vosk.

| Действие | Результат |
|---|---|
| **Удерживайте F9** | Идёт запись речи |
| **Отпустите F9** | Whisper распознаёт речь и вставляет текст в активное поле |

---

## Установка

### 1. Зависимости

```bash
pip install vosk sounddevice openai-whisper pyperclip keyboard numpy
```

> Для режима `hotkey` установка Vosk и модели не требуется.

### 2. Модель Vosk (только для режима `voice`)

Скачайте и распакуйте в `C:\Users\<ВашеИмя>\vosk-model-small-ru-0.22`:

```powershell
Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip" -OutFile "$env:USERPROFILE\vosk-model-small-ru-0.22.zip"
Expand-Archive "$env:USERPROFILE\vosk-model-small-ru-0.22.zip" "$env:USERPROFILE\"
```

### 3. Настройка скрипта

Откройте `whisper-voice-input.py` и задайте нужные параметры:

```python
VOSK_MODEL_PATH = r"C:\Users\<ВашеИмя>\vosk-model-small-ru-0.22"
MODE = "voice"   # "voice" или "hotkey"
```

---

## Запуск

```bash
python whisper-voice-input.py
```

Для автозапуска вместе с Windows: поместите ярлык скрипта в папку `shell:startup`.

---

## Все настройки

| Параметр | По умолчанию | Описание |
|---|---|---|
| `MODE` | `voice` | Режим: `voice` — голосовые команды, `hotkey` — кнопка F9 |
| `WHISPER_MODEL` | `base` | Размер модели Whisper: `tiny`, `base`, `small`, `medium`, `large` |
| `VOSK_MODEL_PATH` | `...small-ru-0.22` | Путь к папке с моделью Vosk |
| `WAKE_PHRASE` | `слушай центральная` | Фраза для начала записи (режим `voice`) |
| `STOP_PHRASE` | `конец связи` | Фраза для остановки записи (режим `voice`) |
| `HOTKEY` | `f9` | Кнопка записи (режим `hotkey`) |
| `MATCH_THRESHOLD` | `0.6` | Порог нечёткого совпадения фраз (0..1) |
| `LANGUAGE` | `ru` | Язык распознавания для Whisper |

---

## Требования

- Python 3.8+
- Windows 10/11
- Микрофон
