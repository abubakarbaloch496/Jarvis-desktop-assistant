# J.A.R.V.I.S v2.0 — Desktop AI Assistant

> **Just A Rather Very Intelligent System**  
> Voice-first desktop assistant with automatic text-input fallback.

---

## What's New in This Build

| Feature | Details |
|---|---|
| ⌨ Text-input fallback | If voice fails, Jarvis asks you to type instead |
| 🎙 Voice input (default) | Microphone via Google Speech Recognition |
| 🤖 Offline AI brain | Optional Ollama integration (llama3 / mistral / phi3) |
| 📋 Clipboard control | Copy, read, and paste via voice or text |
| 💻 System info | Battery, RAM, CPU, Disk usage |
| 📰 Live news | BBC RSS headlines, no API key needed |
| ⌨ Global hotkey | Ctrl + Shift + J activates Jarvis from anywhere |
| 📄 Chat log | Every exchange saved to `~/jarvis_chat_log.txt` |

---

## Installation

### 1. Clone or download this folder

```bash
git clone <your-repo-url>
cd jarvis
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

#### PyAudio (microphone support) — platform notes

| Platform | Command |
|---|---|
| **Windows** | `pip install pipwin` then `pipwin install pyaudio` |
| **macOS** | `brew install portaudio` then `pip install pyaudio` |
| **Linux** | `sudo apt install python3-pyaudio` or `pip install pyaudio` |

### 3. (Optional) Set up Ollama for offline AI

1. Download from [https://ollama.com](https://ollama.com)
2. Run: `ollama pull llama3`
3. Jarvis will automatically detect and use it for unknown commands.

---

## Running Jarvis

```bash
python jarvis_assistant_v2.py
```

> **Linux hotkey note:** The `keyboard` package requires elevated permissions.  
> Run with `sudo python jarvis_assistant_v2.py` if Ctrl+Shift+J does not work.

---

## How Voice + Text Fallback Works

```
Press START  →  Jarvis speaks "How may I assist you?"
                        │
                        ▼
              🎙  Microphone listens (5 s timeout)
                        │
            ┌───────────┴───────────┐
         Success                 Failure
      (voice heard)        (timeout / mic error /
            │               unrecognised speech)
            │                       │
            │               ⌨  Terminal shows:
            │               "Type your command: "
            │                       │
            └──────────┬────────────┘
                       ▼
              execute_command(cmd)
              (same logic for both)
```

- Voice input is always attempted **first**.
- Text fallback triggers **only** when voice returns an empty string.
- Both paths feed into the **exact same** `execute_command()` function.
- No code is duplicated.

---

## Voice / Text Commands

| Command | What it does |
|---|---|
| `time` | Current time |
| `date` | Today's date |
| `youtube` | Opens YouTube |
| `google` | Opens Google |
| `facebook` | Opens Facebook |
| `whatsapp` | Opens WhatsApp Web |
| `notepad` | Opens text editor |
| `calculator` | Opens calculator |
| `battery` | Battery level & status |
| `ram` / `memory` | RAM usage |
| `cpu` / `processor` | CPU usage |
| `disk` / `storage` | Disk usage |
| `news` / `headline` | Top 5 BBC headlines |
| `joke` | Random programming joke |
| `copy <text>` | Copies text to clipboard |
| `clipboard` | Reads clipboard content |
| `paste` | Pastes clipboard (Ctrl+V) |
| `type <text>` | Types text via automation |
| `open log` / `history` | Opens chat log file |
| `exit` / `quit` / `bye` | Closes Jarvis |

Any unrecognised command is sent to **Ollama** if installed, otherwise Jarvis prompts you with supported commands.

---

## File Structure

```
jarvis/
├── jarvis_assistant_v2.py   # Main application
├── requirements.txt          # Python dependencies
└── README.md                 # This file

~/jarvis_chat_log.txt         # Auto-created chat history (home directory)
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `PyAudio` install fails | See platform-specific instructions above |
| Hotkey not working on Linux | Run with `sudo` |
| `ollama` module not found | Run `pip install ollama` (optional) |
| Speech recognition offline | Check internet connection (Google STT needs it) |
| Text input prompt not visible | The prompt appears in the **terminal window**, not the GUI |

---

## Requirements

- Python **3.8+**
- Internet connection for speech recognition and news headlines
- Microphone (optional — text fallback works without one)

---

## License

MIT — free to use, modify, and distribute.
