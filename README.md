# Whisper Voice Input

Голосовой ввод текста для Windows с активацией по ключевой фразе.

## Как работает

1. Запустите скрипт — он работает в фоне и постоянно слушает микрофон через лёгкую модель **Vosk**
2. Скажите **"слушай центральная"** — начнётся запись
3. Говорите всё что нужно
4. Скажите **"конец связи"** — **Whisper** распознаёт речь и вставляет текст в активное поле через Ctrl+V

Поддерживается нечёткое распознавание ключевых фраз — не нужно произносить их идеально точно.

## Установка

### 1. Зависимости

```bash
pip install vosk sounddevice openai-whisper pyperclip keyboard numpy
```

### 2. Модель Vosk (русский язык)

Скачайте и распакуйте в `C:\Users\<ВашеИмя>\vosk-model-small-ru-0.22`:

```
https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
```

Или через PowerShell:

```powershell
Invoke-WebRequest -Uri "https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip" -OutFile "$env:USERPROFILE\vosk-model-small-ru-0.22.zip"
Expand-Archive "$env:USERPROFILE\vosk-model-small-ru-0.22.zip" "$env:USERPROFILE\"
```

### 3. Настройка пути к модели

В файле `whisper-voice-input.py` укажите путь к папке с моделью Vosk:

```python
VOSK_MODEL_PATH = r"C:\Users\<ВашеИмя>\vosk-model-small-ru-0.22"
```

## Запуск

```bash
python whisper-voice-input.py
```

Или добавьте в автозапуск Windows через `shell:startup`.

## Настройки

| Параметр | По умолчанию | Описание |
|---|---|---|
| `WHISPER_MODEL` | `base` | Размер модели: `tiny`, `base`, `small`, `medium`, `large` |
| `WAKE_PHRASE` | `слушай центральная` | Фраза для начала записи |
| `STOP_PHRASE` | `конец связи` | Фраза для остановки записи |
| `MATCH_THRESHOLD` | `0.6` | Порог нечёткого совпадения (0..1) |

## Требования

- Python 3.8+
- Windows 10/11
- Микрофон
