# Whisper Voice Input

Голосовой ввод текста для Windows на базе **Vosk** + **OpenAI Whisper**.
Оба способа ввода работают **одновременно**: голосовые команды и кнопка F9.

---

## Способы ввода

### Голосовые команды

Скрипт постоянно слушает микрофон через лёгкую модель Vosk (почти 0% CPU).

| Действие | Результат |
|---|---|
| Скажите **"центральная"** | Звуковой сигнал → начинается запись |
| Скажите **"исполнять"** | Запись останавливается → распознавание → текст вставляется в активное поле → звуковой сигнал |

Поддерживается **нечёткое распознавание** — не нужно произносить фразы идеально точно.

### Кнопка F9

| Действие | Результат |
|---|---|
| **Зажмите F9** | Звуковой сигнал → идёт запись |
| **Отпустите F9** | Распознавание → текст вставляется в активное поле → звуковой сигнал |

---

## Звуковые сигналы

Начало и окончание записи сопровождаются звуковыми дорожками:
- `sound_start.mp3` — при активации записи
- `sound_done.mp3` — после распознавания и вставки текста

Файлы можно заменить на свои.

---

## Установка

### 1. Зависимости

```bash
pip install vosk sounddevice openai-whisper pyperclip keyboard numpy pygame
```

### 2. Модель Vosk

Скачайте и распакуйте в `C:\Users\<ВашеИмя>\vosk-model-small-ru-0.22`:

```powershell
Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip" -OutFile "$env:USERPROFILE\vosk-model-small-ru-0.22.zip"
Expand-Archive "$env:USERPROFILE\vosk-model-small-ru-0.22.zip" "$env:USERPROFILE\"
```

### 3. Настройка

Откройте `whisper-voice-input.py` и задайте путь к модели:

```python
VOSK_MODEL_PATH = r"C:\Users\<ВашеИмя>\vosk-model-small-ru-0.22"
```

---

## Запуск

```bash
python whisper-voice-input.py
```

Для отладки с выводом логов:

```bash
python -u whisper-voice-input.py
```

### Автозапуск с Windows

Создайте файл `whisper-voice-input.vbs` в папке `shell:startup`:

```vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\...\pythonw.exe"" ""C:\...\whisper-voice-input.py""", 0, False
```

> Защита от повторного запуска: если скрипт уже работает, новый экземпляр завершится автоматически.

---

## Настройки

| Параметр | По умолчанию | Описание |
|---|---|---|
| `WHISPER_MODEL` | `base` | Размер модели Whisper: `tiny`, `base`, `small`, `medium`, `large` |
| `VOSK_MODEL_PATH` | `...small-ru-0.22` | Путь к папке с моделью Vosk |
| `WAKE_PHRASE` | `центральная` | Фраза для начала записи |
| `STOP_PHRASE` | `исполнять` | Фраза для остановки записи |
| `HOTKEY` | `f9` | Кнопка записи (удержание) |
| `MATCH_THRESHOLD` | `0.6` | Порог нечёткого совпадения фраз (0..1) |
| `LANGUAGE` | `ru` | Язык распознавания для Whisper |

---

## Требования

- Python 3.8+
- Windows 10/11
- Микрофон
