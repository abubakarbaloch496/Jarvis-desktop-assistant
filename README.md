# Jarvis-desktop-assistant
J.A.R.V.I.S v2.0 – Desktop AI Assistant

A futuristic Python-based desktop voice assistant inspired by Iron Man’s JARVIS.

This project is developed using Python and PyQt5 with voice recognition, text-to-speech, system monitoring, clipboard control, offline AI support using Ollama, GUI interaction, and automation features.

---

🚀 Features

🎤 Voice Assistant

- Voice command recognition
- Text-to-speech response system
- Smart fallback to text input if voice fails

🖥️ System Monitoring

- Battery percentage
- RAM usage
- CPU usage
- Disk storage information

🌐 Web Automation

- Open YouTube
- Open Google
- Open Facebook
- Open WhatsApp Web

📋 Clipboard Functions

- Copy text to clipboard
- Read clipboard content
- Paste clipboard automatically

⌨️ Smart Typing Assistant

- Automatically type text into any application
- Uses clipboard + keyboard automation

📰 Live News Headlines

- Fetches BBC news headlines using RSS feed

🤖 Offline AI Integration

- Optional Ollama AI support
- Works with local LLM models like:
  - llama3
  - mistral
  - phi3

📄 Chat History Logging

- Automatically saves conversation history
- Stores logs locally

🎹 Global Hotkey

- Activate assistant using:
  Ctrl + Shift + J

🎨 Futuristic GUI

- Modern sci-fi inspired interface
- Dark cyberpunk theme
- Real-time chat display

---

🛠️ Technologies Used

- Python
- PyQt5
- SpeechRecognition
- pyttsx3
- PyAutoGUI
- psutil
- pyperclip
- feedparser
- keyboard
- Ollama

---

📦 Installation

1️⃣ Clone Repository

git clone https://github.com/your-username/jarvis-assistant.git
cd jarvis-assistant

2️⃣ Install Dependencies

pip install PyQt5 SpeechRecognition pyttsx3 pyaudio psutil pyperclip pyautogui feedparser keyboard ollama

---

⚠️ PyAudio Installation (Windows)

If PyAudio fails:

pip install pipwin
pipwin install pyaudio

---

🤖 Ollama Setup (Optional)

Install Ollama:

https://ollama.com

Pull AI model:

ollama pull llama3

Run Ollama before starting Jarvis.

---

▶️ Run Project

python jarvis_assistant_v2.py

---

🧠 Example Commands

- "Open YouTube"
- "Open Google"
- "Tell me the time"
- "Battery status"
- "RAM usage"
- "CPU usage"
- "Tell me a joke"
- "Copy hello world"
- "Read clipboard"
- "Paste"
- "Type good morning"
- "News headlines"
- "Exit"

---

📸 Screenshots

Add your screenshots here.

Example:

![Main GUI](screenshots/main.png)

---

📂 Project Structure

jarvis-assistant/
│
├── jarvis_assistant_v2.py
├── README.md
├── screenshots/
└── requirements.txt

---

🎯 Future Improvements

- Weather API integration
- Face recognition
- ChatGPT API support
- Mobile control
- Wake-word activation
- Multi-language support

---

👨‍💻 Developer

Developed as a Final Year Python GUI Project.

---

📜 License

This project is for educational and learning purposes.
