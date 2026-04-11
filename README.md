# MAX — Personal AI Web Assistant
### Version 5.3 | Built for Rushindhra

---

## What is MAX?

MAX is a full-stack AI-powered personal assistant that runs locally on your Windows PC via a browser. It combines voice recognition, text commands, system monitoring, and AI chat into a single sleek dashboard. It can open/close websites and desktop applications, answer questions, show system stats, tell jokes, get weather, and much more — all through voice or text.

---

## Tech Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Backend    | Python 3.x + Flask 3.x                          |
| Database   | SQLite via Flask-SQLAlchemy                     |
| Auth       | Werkzeug password hashing + Flask sessions      |
| AI / NLP   | Anthropic Claude API (claude-sonnet-4)          |
| Voice      | Web Speech API (browser-native, Chrome only)    |
| TTS        | Web SpeechSynthesis API (browser-native)        |
| Frontend   | Vanilla HTML/CSS/JS — no frameworks             |
| Fonts      | Syne + JetBrains Mono (Google Fonts)            |
| System     | psutil (CPU, RAM, disk, battery)                |
| Weather    | OpenWeatherMap API                              |
| News       | NewsAPI                                         |
| Wikipedia  | python-wikipedia library                        |
| Dictionary | Free Dictionary API (dictionaryapi.dev)         |

---

## Project Structure

```
max_assistant/
│
├── app.py                    ← Main Flask application (ALL backend logic)
│
├── templates/
│   ├── dashboard.html        ← Main UI (voice, console, dashboard, sites, tools)
│   ├── login.html            ← Login page
│   ├── register.html         ← Registration page
│   └── settings.html         ← Profile + API key settings
│
├── static/                   ← (optional) custom CSS/JS if separated
│
├── instance/
│   └── max.db                ← Auto-generated SQLite database
│
└── requirements.txt          ← Python dependencies
```

---

## Installation & Setup

### Step 1 — Clone / Download the project

Place all files in a folder, e.g. `C:\Projects\max_assistant\`

### Step 2 — Install Python dependencies

Open Command Prompt in the project folder and run:

```bash
pip install flask flask-sqlalchemy werkzeug anthropic psutil requests wikipedia pyjokes
```

Optional (for volume control on Windows):
```bash
pip install pycaw comtypes
```

Optional (for screenshot feature):
```bash
pip install pyautogui
```

### Step 3 — Run the app

```bash
python app.py
```

You should see:
```
* Running on http://0.0.0.0:5000
```

### Step 4 — Open in browser

Go to: **http://localhost:5000**

> **Important:** Use **Google Chrome** for voice features. Firefox/Safari do not support Web Speech API.

### Step 5 — Login

Default credentials:
- **Username:** `rushindhra`
- **Password:** `max123`

Or register a new account at `/register`

---

## API Keys (Optional but recommended)

Set these in the app under **Settings → API Keys**:

| Key | What it does | Get it free at |
|-----|--------------|----------------|
| OpenWeather API Key | Live weather data | https://openweathermap.org/api |
| NewsAPI Key | Top news headlines | https://newsapi.org |
| Anthropic Claude Key | AI chat / fallback answers | https://console.anthropic.com |

Without these keys, the respective features will prompt you to add them. Everything else (voice, apps, system stats, jokes, calculator, etc.) works without any API keys.

---

## Features

### Voice Commands
- Click the microphone orb or press **SPACE** to activate
- Say **"Hey MAX"** from any tab to trigger hands-free wake
- Automatic wake word detection runs in the background at all times

### Open Websites
```
open youtube         → Opens YouTube in a new tab
open gmail           → Opens Gmail
open github          → Opens GitHub
open whatsapp        → Opens WhatsApp Web
open chatgpt         → Opens ChatGPT
(+ 17 more sites)
```

### Close Website Tabs
```
close youtube        → Closes the YouTube tab opened by MAX
close tab            → Closes the last tab MAX opened
close whatsapp       → Closes WhatsApp tab
```
> Note: MAX can only close tabs that **it opened** in the current session. Tabs opened manually cannot be closed by MAX (browser security restriction).

### Open Desktop Apps (Windows)
```
open notepad         → Opens Notepad
open calculator      → Opens Calculator
open vscode          → Opens VS Code
open chrome          → Opens Google Chrome
open word            → Opens Microsoft Word
open excel           → Opens Microsoft Excel
open powerpoint      → Opens PowerPoint
open spotify         → Opens Spotify (desktop app)
open discord         → Opens Discord
open zoom            → Opens Zoom
open teams           → Opens Microsoft Teams
open paint           → Opens MS Paint
open terminal        → Opens Command Prompt
open powershell      → Opens PowerShell
open settings        → Opens Windows Settings
open task manager    → Opens Task Manager
(+ many more)
```

### Close Desktop Apps (Windows)
```
close notepad        → Kills notepad.exe process
close calculator     → Kills calculator process
close vscode         → Kills Code.exe
close chrome         → Kills chrome.exe
close spotify        → Kills Spotify.exe
```

### System Monitoring
```
cpu                  → CPU usage percentage + frequency
ram                  → RAM usage (used / total)
disk                 → Disk usage (used / total)
battery              → Battery level + charging status
system info          → Full system overview
ping                 → Internet latency test
```

### AI & Knowledge
```
wikipedia black holes         → Wikipedia summary
define algorithm              → Dictionary definition
calculate 25 times 4 + 100   → Math evaluator
weather in London             → Live weather (needs API key)
news                          → Top headlines (needs API key)
[any question]                → Claude AI answer (needs API key)
```

### Fun Commands
```
joke                 → Random programmer joke
quote                → Motivational quote
flip coin            → Heads or Tails
roll dice            → Roll a 6-sided die (or "roll 20 dice")
```

### System Control
```
volume up            → Increase volume 10%
volume down          → Decrease volume 10%
mute                 → Mute system audio
unmute               → Unmute system audio
lock screen          → Lock Windows session
sleep                → Put PC to sleep
shutdown             → Shutdown (with confirmation)
restart              → Restart (with confirmation)
take a screenshot    → Saves screenshot as PNG
```

### Productivity
```
what time            → Current time
what date            → Today's date
translate hello      → Opens Google Translate
note                 → Write and download a .txt note
set timer 5 minutes  → Countdown timer with alert
set alarm 08:00      → Wake-up alarm
help                 → Full command list
```

### Wake Words (any of these work)
```
hey max / hi max / ok max / hello max / yo max / aye max
```

---

## How Tab Closing Works

MAX uses the browser's `window.open(url, windowName)` API with a consistent window name per site. When you say "close youtube", MAX looks up the stored `window` reference for YouTube and calls `win.close()`.

**Limitations:**
- MAX can only close tabs it opened **in the current browser session**
- If you close a MAX-opened tab manually, MAX will say "please close manually" instead of a false error
- This is a browser security feature — websites cannot close tabs they did not open

---

## How App Open/Close Works

App opening uses Python's `os.startfile()` (most reliable on Windows) with a subprocess fallback. App closing uses `psutil` to find and kill the process by name (case-insensitive).

**Requirements for app features:**
- `psutil` must be installed: `pip install psutil`
- The app must be installed on the system
- For Office apps (Word, Excel, PowerPoint): Microsoft Office must be installed
- For VS Code: must be in system PATH or installed via official installer

---

## Database Schema

**Users** — stores login credentials + API keys per user  
**CommandLog** — every command and response (last 50 shown in History tab)  
**Notes** — quick notes saved by the user

The SQLite database (`max.db`) is auto-created on first run in the `instance/` folder.

---

## Version History

| Version | Changes |
|---------|---------|
| 5.3 | Fixed tab closing (no more false "already closed" errors), fixed app open via os.startfile, fixed app close via psutil kill |
| 5.2 | Added server-side app open/close, login greeting TTS, named window tracking |
| 5.1 | Added wake word detection, voice state machine |
| 5.0 | Full rewrite — Flask + SQLite + multi-user auth |

---

## Known Limitations

1. **Voice only works in Google Chrome** — Firefox and Safari do not support Web Speech API
2. **Tab close only works for MAX-opened tabs** — browser security prevents closing arbitrary tabs
3. **App open/close only works when Flask runs on the same machine** (localhost) — this is by design since the Flask server is your own PC
4. **Volume control requires pycaw** — Windows only
5. **Weather/News require free API keys** — see API Keys section above
6. **Claude AI requires an Anthropic API key** — free tier available

---

## Troubleshooting

**"App not opening"**
→ Make sure the app is installed. For Office apps, Microsoft Office must be installed. For VS Code, ensure it's in PATH.

**"Could not close X: not running"**
→ The app is already closed or was never opened.

**"Popup blocked"**  
→ Click the address bar popup blocker icon and allow popups for localhost:5000

**"Voice not working"**  
→ Use Google Chrome. Allow microphone access when prompted. Check that your microphone is set as default in Windows Sound settings.

**"Claude AI not responding"**  
→ Add your Anthropic API key in Settings → API Keys.

---

## Credits

Built by **Rushindhra** using Flask, Anthropic Claude, and Web Speech API.

MAX v5.3 — Personal AI Web Assistant
