"""
╔══════════════════════════════════════════════════════════════╗
║         J.A.R.V.I.S  v2.0  –  Desktop AI Assistant          ║
║  ─────────────────────────────────────────────────────────   ║
║  NEW  ▸ System info  (battery / RAM / CPU)                   ║
║  NEW  ▸ Clipboard control  (copy / read / paste)             ║
║  NEW  ▸ Type assistant  ("type hello world")                 ║
║  NEW  ▸ Chat history log  (auto-saved to ~/jarvis_log.txt)   ║
║  NEW  ▸ Global hotkey  Ctrl + Shift + J                      ║
║  NEW  ▸ News headlines  (BBC RSS, no API key)                ║
║  NEW  ▸ Offline AI brain  via Ollama (optional)              ║
╚══════════════════════════════════════════════════════════════╝

File   : jarvis_assistant_v2.py

pip install PyQt5 SpeechRecognition pyttsx3 pyaudio
           psutil pyperclip pyautogui feedparser keyboard ollama
           
Notes  :
  • Ollama  →  install from https://ollama.com  then  `ollama pull llama3`
  • keyboard on Linux may require sudo
  • pyaudio on Windows → pip install pipwin && pipwin install pyaudio
"""

# ── Standard library ──────────────────────────────────────────────────────────
import sys
import os
import webbrowser
import subprocess
import datetime
import random
import time
import threading

# ── Speech / TTS ──────────────────────────────────────────────────────────────
import pyttsx3
import speech_recognition as sr

# ── System / IO ───────────────────────────────────────────────────────────────
import psutil
import pyperclip
import pyautogui
import feedparser

# ── Qt ────────────────────────────────────────────────────────────────────────
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QLineEdit,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui  import QFont, QTextCursor

# ── Optional: global hotkey ───────────────────────────────────────────────────
try:
    import keyboard as kb
    KEYBOARD_OK = True
except ImportError:
    KEYBOARD_OK = False

# ── Optional: Ollama offline AI ───────────────────────────────────────────────
try:
    import ollama
    OLLAMA_OK = True
except ImportError:
    OLLAMA_OK = False

# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL SETTINGS
# ─────────────────────────────────────────────────────────────────────────────
OLLAMA_MODEL = "llama3"            # change to "mistral", "phi3", etc.
LOG_FILE     = os.path.join(os.path.expanduser("~"), "jarvis_chat_log.txt")

pyautogui.FAILSAFE = True          # move mouse to top-left corner to abort typing

# ─────────────────────────────────────────────────────────────────────────────
#  JOKES  (offline)
# ─────────────────────────────────────────────────────────────────────────────
JOKES = [
    "Why did the computer go to the doctor? Because it caught a virus.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break — it said no problem, it will go to sleep.",
    "Why was the math book sad? Because it had too many problems.",
    "What do you call a computer that sings? A Dell.",
    "A SQL query walks into a bar, walks up to two tables and asks: Can I join you?",
    "Why do Java developers wear glasses? Because they do not C sharp.",
    "How many programmers does it take to change a light bulb? None — that is a hardware problem.",
    "I changed my password to incorrect. Now it always tells me: your password is incorrect.",
    "There are 10 types of people: those who understand binary, and those who do not.",
]

# ─────────────────────────────────────────────────────────────────────────────
#  CHAT LOG  –  saves every exchange to ~/jarvis_chat_log.txt
# ─────────────────────────────────────────────────────────────────────────────
def save_to_log(you_said: str, jarvis_said: str) -> None:
    """Append one Q&A pair to the log file with a timestamp."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]\n")
            f.write(f"  You    : {you_said}\n")
            f.write(f"  Jarvis : {jarvis_said}\n")
            f.write("─" * 55 + "\n")
    except Exception:
        pass  # logging must never crash the app


# ─────────────────────────────────────────────────────────────────────────────
#  HOTKEY LISTENER  –  Ctrl + Shift + J anywhere on screen
# ─────────────────────────────────────────────────────────────────────────────
class HotkeyListener(QThread):
    """
    Runs in the background.
    Emits `triggered` when Ctrl+Shift+J is pressed anywhere.
    Requires the `keyboard` package (sudo on Linux).
    """
    triggered = pyqtSignal()

    def run(self):
        if not KEYBOARD_OK:
            return
        try:
            kb.add_hotkey("ctrl+shift+j", self.triggered.emit)
            kb.wait()          # keep thread alive indefinitely
        except Exception:
            pass               # silently ignore permission errors


# ─────────────────────────────────────────────────────────────────────────────
#  JARVIS WORKER  –  one listen → execute cycle per button press
# ─────────────────────────────────────────────────────────────────────────────
class JarvisWorker(QThread):
    status_signal      = pyqtSignal(str)        # → status label text
    chat_signal        = pyqtSignal(str, str)   # (you_said, jarvis_said) → chat area
    finished           = pyqtSignal(bool)       # True = exit requested
    request_text_input = pyqtSignal()           # tell GUI to show text input row

    def __init__(self):
        super().__init__()
        self._exit_requested      = False
        self._text_input          = ""
        self._text_event          = threading.Event()

    def receive_text(self, text: str) -> None:
        """Called by the GUI when the user submits typed text."""
        self._text_input = text.strip().lower()
        self._text_event.set()          # unblock run()

    # ── Text-to-Speech ────────────────────────────────────────────────────────
    def speak(self, text: str) -> None:
        """Initialise TTS engine fresh each call (avoids COM threading issues)."""
        self.status_signal.emit(f"🔊  {text}")
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate",   160)
            engine.setProperty("volume", 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            self.status_signal.emit(f"TTS error: {e}")

    # ── Listen ONCE ───────────────────────────────────────────────────────────
    def take_command(self) -> str:
        """
        Listens ONCE via microphone.
        Returns recognised text (lower-case) if words were caught clearly.
        Returns "" on ANY failure — caller decides what to do next.
        """
        self.status_signal.emit("🎙  Listening…")
        rec = sr.Recognizer()
        rec.pause_threshold           = 0.8
        rec.energy_threshold          = 300
        rec.dynamic_energy_threshold  = True

        try:
            with sr.Microphone() as src:
                rec.adjust_for_ambient_noise(src, duration=0.5)
                audio = rec.listen(src, timeout=5, phrase_time_limit=6)

            text = rec.recognize_google(audio).lower()
            self.status_signal.emit(f'✅  You said: "{text}"')
            return text

        except sr.WaitTimeoutError:
            self.status_signal.emit("⏰  No speech detected.")
            return ""
        except sr.UnknownValueError:
            self.status_signal.emit("❓  Could not understand your words.")
            return ""
        except sr.RequestError as e:
            self.status_signal.emit(f"🌐  Speech service error: {e}")
            return ""
        except OSError as e:
            self.status_signal.emit(f"🎤  Microphone error: {e}")
            return ""
        except Exception as e:
            self.status_signal.emit(f"⚠  Unexpected error: {e}")
            return ""

    # ── Execute command ───────────────────────────────────────────────────────
    def execute_command(self, cmd: str) -> None:
        """
        Match keywords in `cmd` and carry out the right action.
        Every branch ends by setting `response`, which is then
        spoken + appended to the chat area + saved to the log.
        """
        response = ""

        # ── Open websites ─────────────────────────────────────────────────────
        if "youtube" in cmd:
            response = "Opening YouTube"
            webbrowser.open("https://www.youtube.com")

        elif "google" in cmd:
            response = "Opening Google"
            webbrowser.open("https://www.google.com")

        elif "facebook" in cmd:
            response = "Opening Facebook"
            webbrowser.open("https://www.facebook.com")

        elif "whatsapp" in cmd:
            response = "Opening WhatsApp Web"
            webbrowser.open("https://web.whatsapp.com")

        # ── Open local apps ───────────────────────────────────────────────────
        elif "notepad" in cmd:
            response = "Opening Notepad"
            if sys.platform == "win32":
                os.startfile("notepad.exe")
            else:
                for ed in ["gedit", "mousepad", "xed", "nano"]:
                    try:
                        subprocess.Popen([ed]); break
                    except FileNotFoundError:
                        continue

        elif "calculator" in cmd or "calc" in cmd:
            response = "Opening Calculator"
            if sys.platform == "win32":
                os.startfile("calc.exe")
            else:
                for ca in ["gnome-calculator", "kcalc", "xcalc"]:
                    try:
                        subprocess.Popen([ca]); break
                    except FileNotFoundError:
                        continue

        # ── Time / Date ───────────────────────────────────────────────────────
        elif "time" in cmd:
            now      = datetime.datetime.now().strftime("%I:%M %p")
            response = f"The current time is {now}"

        elif "date" in cmd:
            today    = datetime.datetime.now().strftime("%B %d, %Y")
            response = f"Today is {today}"

        # ── Offline weather ───────────────────────────────────────────────────
        elif "weather" in cmd:
            response = "I am offline, but it looks like a perfect day to write some code!"

        # ── Jokes ─────────────────────────────────────────────────────────────
        elif any(kw in cmd for kw in ["joke", "make me laugh", "funny"]):
            response = random.choice(JOKES)

        # ─────────────────────────────────────────────────────────────────────
        #  NEW FEATURES
        # ─────────────────────────────────────────────────────────────────────

        # ── Battery ───────────────────────────────────────────────────────────
        elif "battery" in cmd:
            batt = psutil.sensors_battery()
            if batt:
                plug     = "plugged in" if batt.power_plugged else "running on battery"
                response = (f"Battery is at {batt.percent:.0f} percent "
                            f"and is currently {plug}")
            else:
                response = "No battery detected. You may be on a desktop computer."

        # ── RAM / Memory ──────────────────────────────────────────────────────
        elif "ram" in cmd or "memory" in cmd:
            m        = psutil.virtual_memory()
            used_gb  = m.used  / 1024 ** 3
            total_gb = m.total / 1024 ** 3
            response = (f"RAM usage is {used_gb:.1f} gigabytes "
                        f"out of {total_gb:.1f} gigabytes, "
                        f"which is {m.percent:.0f} percent")

        # ── CPU ───────────────────────────────────────────────────────────────
        elif "cpu" in cmd or "processor" in cmd:
            pct      = psutil.cpu_percent(interval=1)
            cores    = psutil.cpu_count(logical=False)
            response = f"CPU usage is {pct} percent across {cores} physical cores"

        # ── Disk space ────────────────────────────────────────────────────────
        elif "disk" in cmd or "storage" in cmd or "hard drive" in cmd:
            disk     = psutil.disk_usage("/")
            used_gb  = disk.used  / 1024 ** 3
            total_gb = disk.total / 1024 ** 3
            response = (f"Disk usage is {used_gb:.1f} gigabytes "
                        f"used out of {total_gb:.1f} gigabytes total")

        # ── Copy text to clipboard ────────────────────────────────────────────
        elif cmd.startswith("copy "):
            text_to_copy = cmd[5:].strip()
            if text_to_copy:
                pyperclip.copy(text_to_copy)
                response = f"Copied to clipboard: {text_to_copy}"
            else:
                response = "Please say what you want to copy. For example: copy hello world"

        # ── Read clipboard ────────────────────────────────────────────────────
        elif any(kw in cmd for kw in ["clipboard", "what did i copy",
                                       "read clipboard", "show clipboard"]):
            content = pyperclip.paste()
            if content:
                preview  = content[:80] + ("…" if len(content) > 80 else "")
                response = f"Your clipboard contains: {preview}"
            else:
                response = "The clipboard is currently empty"

        # ── Paste (type clipboard via Ctrl+V) ─────────────────────────────────
        elif "paste" in cmd:
            content = pyperclip.paste()
            if content:
                self.speak("Pasting now. Click your target window.")
                time.sleep(2.0)          # give user time to click target window
                pyautogui.hotkey("ctrl", "v")
                response = "Clipboard content pasted"
            else:
                response = "The clipboard is empty, there is nothing to paste"

        # ── Type assistant ────────────────────────────────────────────────────
        elif cmd.startswith("type "):
            to_type = cmd[5:].strip()
            if to_type:
                self.speak("Click your target window. I will type in 2 seconds.")
                time.sleep(2.0)
                # Use clipboard → Ctrl+V for full Unicode support
                original = pyperclip.paste()        # save current clipboard
                pyperclip.copy(to_type)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.3)
                pyperclip.copy(original)            # restore original clipboard
                response = f"Typed: {to_type}"
            else:
                response = "Please say what to type. For example: type good morning"

        # ── News headlines (BBC RSS, no API key) ──────────────────────────────
        elif "news" in cmd or "headline" in cmd:
            self.status_signal.emit("📰  Fetching BBC headlines…")
            try:
                feed   = feedparser.parse("http://feeds.bbci.co.uk/news/rss.xml")
                titles = [e.title for e in feed.entries[:5]]
                if titles:
                    response = ("Here are today's top 5 BBC headlines. "
                                + ". ".join(titles))
                else:
                    response = "No headlines found. Check your internet connection."
            except Exception as e:
                response = f"Could not fetch news: {e}"

        # ── Open chat log ─────────────────────────────────────────────────────
        elif any(kw in cmd for kw in ["open log", "chat log",
                                       "history", "show log"]):
            if os.path.exists(LOG_FILE):
                response = "Opening your chat history log"
                try:
                    if sys.platform == "win32":
                        os.startfile(LOG_FILE)
                    else:
                        subprocess.Popen(["xdg-open", LOG_FILE])
                except Exception:
                    response = f"Your log is saved at {LOG_FILE}"
            else:
                response = "No chat log found yet. It will be created after your first command."

        # ── Exit ──────────────────────────────────────────────────────────────
        elif any(kw in cmd for kw in ["exit", "quit", "bye",
                                       "goodbye", "stop", "close"]):
            farewell = "Goodbye! Have a great day."
            self.speak(farewell)
            self.status_signal.emit("👋  Goodbye!")
            self.chat_signal.emit(cmd, farewell)
            save_to_log(cmd, farewell)
            self._exit_requested = True
            return

        # ── Ollama offline AI fallback ────────────────────────────────────────
        else:
            if OLLAMA_OK:
                self.status_signal.emit(f"🤖  Asking Ollama ({OLLAMA_MODEL})…")
                try:
                    res = ollama.chat(
                        model    = OLLAMA_MODEL,
                        messages = [{"role": "user", "content": cmd}],
                    )
                    # Handle both dict-style and object-style responses
                    if isinstance(res, dict):
                        response = res["message"]["content"]
                    else:
                        response = res.message.content

                    # Trim very long AI answers before speaking
                    if len(response) > 450:
                        response = response[:450].rsplit(" ", 1)[0] + "…"

                except Exception as e:
                    response = (f"Ollama error: {e}. "
                                "Make sure Ollama is running and the model is pulled.")
            else:
                response = ("I did not understand that command. "
                            "Try: time, date, battery, RAM, CPU, news, joke, "
                            "copy, paste, type, or a website name.")

        # ── Speak + log every non-exit response ──────────────────────────────
        if response:
            self.speak(response)
            self.chat_signal.emit(cmd, response)
            save_to_log(cmd, response)

    # ── Thread entry point ────────────────────────────────────────────────────
    def run(self):
        """
        Single complete cycle:
          1. Greet user
          2. Listen ONCE via microphone (default)
          3. If voice fails/times-out, fall back to keyboard input()
          4. Execute command if something was heard / typed
          5. Signal finished so GUI re-enables the START button
        """
        self.speak("How may I assist you?")
        cmd = self.take_command()

        # Voice caught words clearly → execute immediately, no text input
        if cmd:
            self.execute_command(cmd)
            self.finished.emit(self._exit_requested)
            return

        # Voice did NOT catch words → politely ask user to type instead
        self.status_signal.emit("⌨  Kindly use the text input method below.")
        self._text_input = ""
        self._text_event.clear()
        self.request_text_input.emit()   # show GUI text input row
        self._text_event.wait()          # block until user submits
        cmd = self._text_input

        if cmd:
            self.execute_command(cmd)
        self.finished.emit(self._exit_requested)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class JarvisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.hotkey = None
        self._build_ui()
        self._start_hotkey_listener()

    # ── Build GUI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("J.A.R.V.I.S  v2.0")
        self.setFixedSize(580, 650)
        self.setStyleSheet(STYLESHEET)

        central = QWidget(objectName="central")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(32, 22, 32, 22)
        root.setSpacing(11)

        # ── Header ────────────────────────────────────────────────────────────
        lbl_title = QLabel("J.A.R.V.I.S", objectName="lbl_title")
        lbl_title.setAlignment(Qt.AlignCenter)
        root.addWidget(lbl_title)

        lbl_sub = QLabel("JUST A RATHER VERY INTELLIGENT SYSTEM  v2.0", objectName="lbl_sub")
        lbl_sub.setAlignment(Qt.AlignCenter)
        root.addWidget(lbl_sub)

        # Feature badges row
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(6)
        for badge_text in ["SYSTEM", "CLIPBOARD", "TYPE", "NEWS", "AI", "LOG"]:
            b = QLabel(badge_text, objectName="badge")
            b.setAlignment(Qt.AlignCenter)
            badges_layout.addWidget(b)
        root.addLayout(badges_layout)

        # Divider
        div = QFrame(objectName="divider")
        div.setFrameShape(QFrame.HLine)
        root.addWidget(div)

        # ── Chat history area ─────────────────────────────────────────────────
        self.chat_area = QTextEdit(objectName="chat_area")
        self.chat_area.setReadOnly(True)
        self.chat_area.setMinimumHeight(220)
        self.chat_area.setPlaceholderText(
            "  Chat history appears here…\n\n"
            "  Try saying:\n"
            "  • battery / RAM / CPU / disk\n"
            "  • copy hello world\n"
            "  • type good morning\n"
            "  • news / headlines\n"
            "  • paste / clipboard\n"
            "  • joke / time / date / exit"
        )
        root.addWidget(self.chat_area)

        # ── Status label ──────────────────────────────────────────────────────
        self.status_lbl = QLabel(
            "Press  START  or  Ctrl+Shift+J  to activate",
            objectName="lbl_status"
        )
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setMinimumHeight(46)
        root.addWidget(self.status_lbl)

        # ── Text-input fallback row (hidden until voice fails) ────────────────
        self.text_input_row = QWidget(objectName="text_input_row")
        text_row_layout = QHBoxLayout(self.text_input_row)
        text_row_layout.setContentsMargins(0, 0, 0, 0)
        text_row_layout.setSpacing(8)

        self.cmd_input = QLineEdit(objectName="cmd_input")
        self.cmd_input.setPlaceholderText("Type your command here and press Send…")
        self.cmd_input.setFixedHeight(38)
        text_row_layout.addWidget(self.cmd_input)

        self.btn_send = QPushButton("⏎  SEND", objectName="btn_send")
        self.btn_send.setFixedSize(90, 38)
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.clicked.connect(self._submit_text_input)
        text_row_layout.addWidget(self.btn_send)

        self.cmd_input.returnPressed.connect(self._submit_text_input)

        self.text_input_row.setVisible(False)   # hidden by default
        root.addWidget(self.text_input_row)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_start = QPushButton("▶   START", objectName="btn_start")
        self.btn_start.setFixedHeight(52)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self.btn_start)

        btn_log = QPushButton("📄  LOG", objectName="btn_secondary")
        btn_log.setFixedSize(100, 52)
        btn_log.setCursor(Qt.PointingHandCursor)
        btn_log.clicked.connect(self._open_log)
        btn_row.addWidget(btn_log)

        btn_clear = QPushButton("🗑  CLEAR", objectName="btn_secondary")
        btn_clear.setFixedSize(100, 52)
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self.chat_area.clear)
        btn_row.addWidget(btn_clear)

        root.addLayout(btn_row)

        # ── Footer ────────────────────────────────────────────────────────────
        hotkey_info = "Ctrl+Shift+J  active" if KEYBOARD_OK else "install keyboard pkg for hotkey"
        ollama_info = f"Ollama/{OLLAMA_MODEL}  ready" if OLLAMA_OK else "Ollama not installed"
        lbl_foot = QLabel(
            f"⌨  {hotkey_info}   |   🤖  {ollama_info}   |   📄  {LOG_FILE}",
            objectName="lbl_hint"
        )
        lbl_foot.setAlignment(Qt.AlignCenter)
        lbl_foot.setWordWrap(True)
        root.addWidget(lbl_foot)

    # ── Hotkey listener ───────────────────────────────────────────────────────
    def _start_hotkey_listener(self):
        if not KEYBOARD_OK:
            return
        self.hotkey = HotkeyListener()
        self.hotkey.triggered.connect(self._on_start)
        self.hotkey.daemon = True
        self.hotkey.start()

    # ── Slots ─────────────────────────────────────────────────────────────────
    def _on_start(self):
        """Fires on button click OR Ctrl+Shift+J hotkey."""
        if not self.btn_start.isEnabled():
            return  # already running — ignore duplicate trigger

        self.btn_start.setEnabled(False)
        self.btn_start.setText("⏳   Processing…")

        self.worker = JarvisWorker()
        self.worker.status_signal.connect(self._update_status)
        self.worker.chat_signal.connect(self._add_chat_entry)
        self.worker.finished.connect(self._on_worker_done)
        self.worker.request_text_input.connect(self._show_text_input)
        self.worker.start()

    def _show_text_input(self):
        """Show the text-input row when voice recognition fails."""
        self.cmd_input.clear()
        self.text_input_row.setVisible(True)
        self.cmd_input.setFocus()

    def _submit_text_input(self):
        """Send typed text to the worker and hide the input row."""
        text = self.cmd_input.text().strip()
        if not text:
            return
        self.text_input_row.setVisible(False)
        self.cmd_input.clear()
        if self.worker:
            self.worker.receive_text(text)

    def _update_status(self, text: str):
        self.status_lbl.setText(text)

    def _add_chat_entry(self, you_said: str, jarvis_said: str):
        """Append a formatted exchange bubble to the chat area."""
        ts = datetime.datetime.now().strftime("%H:%M")

        self.chat_area.append(
            f'<span style="color:#334455;font-size:9px;">[{ts}]</span>'
        )
        self.chat_area.append(
            f'<span style="color:#7ab8d4;"><b>You ›</b></span> '
            f'<span style="color:#aac8e0;">{you_said}</span>'
        )
        self.chat_area.append(
            f'<span style="color:#00e5ff;"><b>Jarvis ›</b></span> '
            f'<span style="color:#c8f0ff;">{jarvis_said}</span>'
        )
        self.chat_area.append(
            '<span style="color:#112233;">'
            + "─" * 40
            + '</span>'
        )
        # Auto-scroll to bottom
        self.chat_area.moveCursor(QTextCursor.End)

    def _on_worker_done(self, exit_requested: bool):
        self.text_input_row.setVisible(False)
        if exit_requested:
            QApplication.quit()
            return
        self.btn_start.setEnabled(True)
        self.btn_start.setText("▶   START")
        self.status_lbl.setText("Press  START  or  Ctrl+Shift+J  to activate")

    def _open_log(self):
        """Open the chat log in the system text editor."""
        if not os.path.exists(LOG_FILE):
            self.status_lbl.setText("No log yet. Use Jarvis first!")
            return
        try:
            if sys.platform == "win32":
                os.startfile(LOG_FILE)
            else:
                subprocess.Popen(["xdg-open", LOG_FILE])
        except Exception as e:
            self.status_lbl.setText(f"Cannot open log: {e}")

    def closeEvent(self, event):
        """Cleanly stop the hotkey thread when the window is closed."""
        if self.hotkey and self.hotkey.isRunning() and KEYBOARD_OK:
            try:
                kb.unhook_all()
            except Exception:
                pass
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  DARK SCI-FI STYLESHEET
# ─────────────────────────────────────────────────────────────────────────────
STYLESHEET = """
/* ── Window ──────────────────────────────────────────────────────── */
QMainWindow, QWidget#central {
    background-color: #080810;
}

/* ── Title ───────────────────────────────────────────────────────── */
QLabel#lbl_title {
    color: #00e5ff;
    font-family: "Courier New", monospace;
    font-size: 32px;
    font-weight: bold;
    letter-spacing: 10px;
}
QLabel#lbl_sub {
    color: #223344;
    font-family: "Courier New", monospace;
    font-size: 9px;
    letter-spacing: 2px;
}

/* ── Feature badges ──────────────────────────────────────────────── */
QLabel#badge {
    color: #004455;
    background-color: #0a0a18;
    border: 1px solid #003344;
    border-radius: 4px;
    font-family: "Courier New", monospace;
    font-size: 8px;
    letter-spacing: 1px;
    padding: 2px 6px;
}

/* ── Divider ─────────────────────────────────────────────────────── */
QFrame#divider {
    background-color: #0a1525;
    max-height: 1px;
}

/* ── Chat area ───────────────────────────────────────────────────── */
QTextEdit#chat_area {
    background-color: #050510;
    color: #c8d8e8;
    font-family: "Courier New", monospace;
    font-size: 11px;
    border: 1px solid #0a1525;
    border-radius: 8px;
    padding: 10px;
    selection-background-color: #00e5ff;
    selection-color: #050510;
}
QScrollBar:vertical {
    background: #080810;
    width: 6px;
    border-radius: 3px;
}
QScrollBar::handle:vertical {
    background: #003344;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #00e5ff; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }

/* ── Status label ────────────────────────────────────────────────── */
QLabel#lbl_status {
    color: #88aacc;
    font-family: "Courier New", monospace;
    font-size: 12px;
    background-color: #0a0a18;
    border: 1px solid #0a1525;
    border-radius: 6px;
    padding: 8px;
}

/* ── START button ────────────────────────────────────────────────── */
QPushButton#btn_start {
    background-color: transparent;
    color: #00e5ff;
    border: 2px solid #00e5ff;
    border-radius: 26px;
    font-family: "Courier New", monospace;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 4px;
    min-width: 180px;
}
QPushButton#btn_start:hover {
    background-color: #00e5ff;
    color: #050510;
}
QPushButton#btn_start:pressed {
    background-color: #00aabb;
    color: #050510;
}
QPushButton#btn_start:disabled {
    color: #113322;
    border-color: #113322;
}

/* ── Secondary buttons (LOG / CLEAR) ─────────────────────────────── */
QPushButton#btn_secondary {
    background-color: transparent;
    color: #334455;
    border: 1px solid #112233;
    border-radius: 26px;
    font-family: "Courier New", monospace;
    font-size: 10px;
    letter-spacing: 1px;
}
QPushButton#btn_secondary:hover {
    background-color: #0a1525;
    color: #00e5ff;
    border-color: #003344;
}

/* ── Text-input fallback row ─────────────────────────────────────── */
QWidget#text_input_row {
    background-color: transparent;
}
QLineEdit#cmd_input {
    background-color: #0a0a18;
    color: #00e5ff;
    border: 1px solid #00e5ff;
    border-radius: 6px;
    font-family: "Courier New", monospace;
    font-size: 12px;
    padding: 4px 10px;
    selection-background-color: #00e5ff;
    selection-color: #050510;
}
QLineEdit#cmd_input:focus {
    border: 1px solid #00e5ff;
    background-color: #0d0d22;
}
QPushButton#btn_send {
    background-color: transparent;
    color: #00e5ff;
    border: 1px solid #00e5ff;
    border-radius: 6px;
    font-family: "Courier New", monospace;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 2px;
}
QPushButton#btn_send:hover {
    background-color: #00e5ff;
    color: #050510;
}
QPushButton#btn_send:pressed {
    background-color: #00aabb;
    color: #050510;
}

/* ── Footer hint ─────────────────────────────────────────────────── */
QLabel#lbl_hint {
    color: #1a2a33;
    font-family: "Courier New", monospace;
    font-size: 8px;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Courier New", 10))
    win = JarvisApp()
    win.show()
    sys.exit(app.exec_())
