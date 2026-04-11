"""
MAX Web Assistant — Flask Backend v5.4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES v5.4:
  - App opening:  os.startfile / subprocess + post-launch maximize via win32gui
  - App closing:  Corrected ALL proc names (UWP apps use correct host names)
                  Multi-strategy kill: psutil → taskkill /IM → taskkill /T /F
  - Tab closing:  Robust site-key resolution on server side
  - New /api/maximize_app endpoint to bring window to front & maximize
"""

import os, re, math, json, random, socket, platform, subprocess, threading
import datetime, webbrowser, time, logging
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, session,
    redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

try:    import psutil;    PSUTIL = True
except: PSUTIL = False;  psutil = None

try:    import requests as req_lib;  REQUESTS = True
except: REQUESTS = False;            req_lib = None

try:    import wikipedia as wiki_lib; WIKI = True
except: WIKI = False;                 wiki_lib = None

try:
    import anthropic
    CLAUDE = True
except:
    CLAUDE = False
    anthropic = None

try:    import pyjokes; JOKES_LIB = True
except: JOKES_LIB = False; pyjokes = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "max-super-secret-key-change-in-prod")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///max.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True

db = SQLAlchemy(app)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("MAX")

IS_WIN   = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MAC   = platform.system() == "Darwin"
VERSION  = "5.4"

# ── models ────────────────────────────────────────────────────────────────────
class User(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    username     = db.Column(db.String(80),  unique=True, nullable=False)
    email        = db.Column(db.String(120), unique=True, nullable=False)
    password     = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(100), default="")
    created_at   = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    last_login   = db.Column(db.DateTime)
    cmd_count    = db.Column(db.Integer, default=0)
    ow_api_key   = db.Column(db.String(64), default="")
    news_api_key = db.Column(db.String(64), default="")
    claude_key   = db.Column(db.String(128), default="")

class CommandLog(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    command    = db.Column(db.String(500))
    response   = db.Column(db.Text)
    source     = db.Column(db.String(20), default="text")
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class Note(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title      = db.Column(db.String(200), default="Untitled")
    content    = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

# ── site map ──────────────────────────────────────────────────────────────────
SITES = {
    "youtube":       ("YouTube",        "https://www.youtube.com"),
    "gmail":         ("Gmail",          "https://mail.google.com"),
    "google":        ("Google",         "https://www.google.com"),
    "github":        ("GitHub",         "https://github.com"),
    "linkedin":      ("LinkedIn",       "https://www.linkedin.com"),
    "whatsapp":      ("WhatsApp",       "https://web.whatsapp.com"),
    "instagram":     ("Instagram",      "https://www.instagram.com"),
    "twitter":       ("Twitter/X",      "https://twitter.com"),
    "reddit":        ("Reddit",         "https://www.reddit.com"),
    "discord":       ("Discord",        "https://discord.com/app"),
    "spotify":       ("Spotify",        "https://open.spotify.com"),
    "netflix":       ("Netflix",        "https://www.netflix.com"),
    "amazon":        ("Amazon",         "https://www.amazon.in"),
    "chatgpt":       ("ChatGPT",        "https://chat.openai.com"),
    "gemini":        ("Gemini",         "https://gemini.google.com"),
    "notion":        ("Notion",         "https://www.notion.so"),
    "maps":          ("Google Maps",    "https://maps.google.com"),
    "drive":         ("Google Drive",   "https://drive.google.com"),
    "meet":          ("Google Meet",    "https://meet.google.com"),
    "docs":          ("Google Docs",    "https://docs.google.com"),
    "sheets":        ("Google Sheets",  "https://sheets.google.com"),
    "stackoverflow": ("Stack Overflow", "https://stackoverflow.com"),
}

# ── App maps ──────────────────────────────────────────────────────────────────
APP_MAP_WIN = {
    "notepad":            "notepad.exe",
    "calculator":         "calc.exe",
    "paint":              "mspaint.exe",
    "explorer":           "explorer.exe",
    "file explorer":      "explorer.exe",
    "files":              "explorer.exe",
    "task manager":       "taskmgr.exe",
    "taskmanager":        "taskmgr.exe",
    "cmd":                "cmd.exe",
    "command prompt":     "cmd.exe",
    "terminal":           "wt.exe",          # Windows Terminal first, fallback to cmd
    "powershell":         "powershell.exe",
    "power shell":        "powershell.exe",
    "word":               "winword.exe",
    "ms word":            "winword.exe",
    "microsoft word":     "winword.exe",
    "excel":              "excel.exe",
    "ms excel":           "excel.exe",
    "spreadsheet":        "excel.exe",
    "powerpoint":         "powerpnt.exe",
    "power point":        "powerpnt.exe",
    "ppt":                "powerpnt.exe",
    "vs code":            "code.exe",
    "vscode":             "code.exe",
    "visual studio code": "code.exe",
    "visual studio":      "code.exe",
    "edge":               "msedge.exe",
    "microsoft edge":     "msedge.exe",
    "firefox":            "firefox.exe",
    "mozilla firefox":    "firefox.exe",
    "chrome":             "chrome.exe",
    "google chrome":      "chrome.exe",
    "vlc":                "vlc.exe",
    "vlc media player":   "vlc.exe",
    "zoom":               "zoom.exe",
    "zoom meeting":       "zoom.exe",
    "teams":              "Teams.exe",
    "microsoft teams":    "Teams.exe",
    "slack":              "slack.exe",
    "discord":            "Discord.exe",
    "spotify":            "Spotify.exe",
    "snipping tool":      "SnippingTool.exe",
    "snip":               "SnippingTool.exe",
    "control panel":      "control.exe",
}

# Windows URI scheme apps (launched via start command)
APP_URI_WIN = {
    "settings":         "ms-settings:",
    "windows settings": "ms-settings:",
    "camera":           "microsoft.windows.camera:",
    "photos":           "ms-photos:",
    "clock":            "ms-clock:",
    "calendar":         "outlookcal:",
    "mail":             "outlookmail:",
    "store":            "ms-windows-store:",
    "sticky notes":     "ms-stickynotes:",
    "music":            "mswindowsmusic:",
}

APP_MAP_LINUX = {
    "terminal":           "x-terminal-emulator",
    "files":              "nautilus",
    "file manager":       "nautilus",
    "calculator":         "gnome-calculator",
    "vs code":            "code",
    "vscode":             "code",
    "visual studio code": "code",
    "firefox":            "firefox",
    "chrome":             "google-chrome",
    "chromium":           "chromium-browser",
    "vlc":                "vlc",
    "text editor":        "gedit",
    "gedit":              "gedit",
    "settings":           "gnome-control-center",
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROC_MAP — FIXED v5.4
# Rules:
#   • Win32 apps: exact .exe name as seen in Task Manager "Details" tab
#   • UWP / Store apps: their actual host process name
#   • Multiple names allowed as comma-separated string; all will be tried
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROC_MAP = {
    # Win32 apps — straightforward
    "notepad":            "notepad.exe",
    "paint":              "mspaint.exe",
    "word":               "WINWORD.EXE",
    "ms word":            "WINWORD.EXE",
    "microsoft word":     "WINWORD.EXE",
    "excel":              "EXCEL.EXE",
    "ms excel":           "EXCEL.EXE",
    "powerpoint":         "POWERPNT.EXE",
    "power point":        "POWERPNT.EXE",
    "ppt":                "POWERPNT.EXE",
    "vs code":            "Code.exe",
    "vscode":             "Code.exe",
    "visual studio code": "Code.exe",
    "edge":               "msedge.exe",
    "microsoft edge":     "msedge.exe",
    "firefox":            "firefox.exe",
    "mozilla firefox":    "firefox.exe",
    "chrome":             "chrome.exe",
    "google chrome":      "chrome.exe",
    "vlc":                "vlc.exe",
    "zoom":               "Zoom.exe",
    "zoom meeting":       "Zoom.exe",
    "teams":              "Teams.exe",
    "microsoft teams":    "Teams.exe",
    "slack":              "slack.exe",
    "discord":            "Discord.exe",
    "spotify":            "Spotify.exe",
    "task manager":       "Taskmgr.exe",
    "taskmanager":        "Taskmgr.exe",
    "control panel":      "control.exe",
    "cmd":                "cmd.exe",
    "command prompt":     "cmd.exe",
    "powershell":         "powershell.exe",
    "power shell":        "powershell.exe",
    "terminal":           "WindowsTerminal.exe",
    "explorer":           "explorer.exe",
    "file explorer":      "explorer.exe",

    # UWP / Store apps — these run under ApplicationFrameHost.exe as the
    # visible window, but their actual background process names are below.
    # We kill BOTH the frame host window (by title via taskkill) AND the process.
    # Comma-separated = try each name in order.
    "calculator":         "CalculatorApp.exe,Calculator.exe,ApplicationFrameHost.exe",
    "calc":               "CalculatorApp.exe,Calculator.exe",
    "camera":             "WinStore.App.exe,Microsoft.WindowsCamera",
    "photos":             "Microsoft.Photos.exe,PhotosApp.exe",
    "clock":              "TimeDate.cpl",
    "snipping tool":      "SnippingTool.exe,ScreenClippingHost.exe",
    "snip":               "SnippingTool.exe,ScreenClippingHost.exe",
    "sticky notes":       "Microsoft.Notes.exe",
    "store":              "WinStore.App.exe",
    "mail":               "HxOutlook.exe,Microsoft.WindowsCommunicationsApps_8wekyb3d8bbwe",
}

# Window title keywords for UWP apps (used as fallback kill-by-title)
UWP_TITLE_MAP = {
    "calculator": "Calculator",
    "calc":       "Calculator",
    "camera":     "Camera",
    "photos":     "Photos",
    "clock":      "Clock",
    "store":      "Microsoft Store",
    "mail":       "Mail",
    "sticky notes": "Sticky Notes",
}

FUZZY = {
    # Wake word stripping
    "hey max ": "", "ok max ": "", "hi max ": "", "hello max ": "",
    "yo max ": "", "hey mack ": "", "okay max ": "", "hey marks ": "",
    "hey mac ": "", "aye max ": "", "hay max ": "", "hey max, ": "",
    "ok max, ": "", "okay max, ": "",

    # Polite prefixes
    "can you open ": "open ", "please open ": "open ",
    "would you open ": "open ", "could you open ": "open ",
    "can you please open ": "open ", "would you please open ": "open ",
    "i want to open ": "open ", "launch the ": "open ",
    "open up ": "open ", "i need to open ": "open ",
    "take me to ": "open ", "go to ": "open ",
    "can you close ": "close ", "please close ": "close ",
    "would you close ": "close ", "could you close ": "close ",
    "can you shut ": "close ", "please shut ": "close ",
    "can you please close ": "close ",

    # Close tab variants
    "close the tab": "close tab", "close this tab": "close tab",
    "shut the tab": "close tab", "close current tab": "close tab",
    "close my tab": "close tab", "shut this tab": "close tab",
    "close it": "close tab", "shut it": "close tab",
    "close that": "close tab", "exit tab": "close tab",
    "close the window": "close tab", "shut the window": "close tab",
    "shut down the tab": "close tab", "close out the tab": "close tab",
    "get rid of the tab": "close tab", "remove the tab": "close tab",
    "close out": "close tab",

    # Site name fuzzy
    "charging ppt": "chatgpt", "chat gpt": "chatgpt",
    "chat g p t": "chatgpt", "chargee ppt": "chatgpt",
    "you tube": "youtube", "utube": "youtube", "u tube": "youtube",
    "you-tube": "youtube", "youtub": "youtube",
    "what's app": "whatsapp", "watsapp": "whatsapp",
    "watts app": "whatsapp", "whats app": "whatsapp",
    "wats app": "whatsapp", "what sapp": "whatsapp",
    "insta gram": "instagram", "insta": "instagram",
    "instgram": "instagram",
    "linked in": "linkedin", "linked-in": "linkedin",
    "linkdin": "linkedin", "linkin": "linkedin",
    "git hub": "github", "git-hub": "github", "githb": "github",
    "disk cord": "discord", "disc cord": "discord",
    "discoard": "discord", "dis cord": "discord",
    "spot if i": "spotify", "spotfy": "spotify",
    "spottify": "spotify", "sportify": "spotify",
    "no shun": "notion", "notian": "notion", "notoin": "notion",
    "net flix": "netflix", "netflex": "netflix", "netfix": "netflix",
    "google map": "maps", "google maps": "maps",
    "gmap": "maps", "g maps": "maps",
    "google drive": "drive", "gdrive": "drive", "g drive": "drive",
    "google meet": "meet", "gmeet": "meet", "g meet": "meet",
    "google docs": "docs", "gdocs": "docs", "g docs": "docs",
    "google sheets": "sheets", "gsheets": "sheets",
    "amaz on": "amazon", "amazn": "amazon", "amzon": "amazon",
    "red it": "reddit", "readit": "reddit", "reddt": "reddit",
    "twit er": "twitter", "twiter": "twitter", "twiiter": "twitter",
    "be s code": "vscode", "vs cold": "vscode",
    "visual studio code": "vscode", "bs code": "vscode",
    "vee es code": "vscode", "v s code": "vscode",
    "stack over flow": "stackoverflow", "stack overflow": "stackoverflow",
    "stackover flow": "stackoverflow",
    "jemin eye": "gemini", "gem ini": "gemini", "gemenie": "gemini",

    # Time / date
    "what's the time": "what time", "current time": "what time",
    "what's the date": "what date", "today's date": "what date",
    "what is the time": "what time", "tell me the time": "what time",
    "what is today": "what date", "today's day": "what date",
    "whats the time": "what time", "whats the date": "what date",
    "time please": "what time", "date please": "what date",
    "show me the time": "what time", "show me the date": "what date",

    # Search
    "google search": "search", "search for": "search",
    "look up": "search", "look for": "search",
    "google for": "search", "find me": "search",
    "search about": "search", "find info on": "search",
    "youtube search": "youtube search", "play on youtube": "youtube search",
    "search on youtube": "youtube search", "find on youtube": "youtube search",
    "play youtube": "youtube search", "watch on youtube": "youtube search",

    # System commands
    "cpu usage": "cpu", "processor usage": "cpu", "cpu load": "cpu",
    "cpu status": "cpu", "how much cpu": "cpu", "check cpu": "cpu",
    "ram usage": "ram", "memory usage": "ram", "ram status": "ram",
    "how much ram": "ram", "check ram": "ram", "memory left": "ram",
    "disk space": "disk", "disk usage": "disk", "storage space": "disk",
    "check disk": "disk", "how much disk": "disk", "disk status": "disk",
    "battery level": "battery", "battery status": "battery",
    "battery percentage": "battery", "battery life": "battery",
    "how much battery": "battery", "check battery": "battery",
    "battery remaining": "battery", "battery charge": "battery",
    "current battery": "battery", "battery percent": "battery",
    "what is the battery": "battery", "what is battery": "battery",
    "internet speed": "ping", "check internet": "ping",
    "network speed": "ping", "test internet": "ping",
    "system information": "system info", "system details": "system info",
    "computer info": "system info", "pc info": "system info",

    # Volume
    "volume louder": "volume up", "make it louder": "volume up",
    "increase volume": "volume up", "turn up volume": "volume up",
    "volume quieter": "volume down", "make it quieter": "volume down",
    "decrease volume": "volume down", "turn down volume": "volume down",
    "silence": "mute", "silent mode": "mute", "no sound": "mute",
    "turn off sound": "mute",
    "turn on sound": "unmute", "sound on": "unmute",

    # Fun
    "tell a joke": "joke", "give me a joke": "joke",
    "make me laugh": "joke", "funny joke": "joke",
    "say a joke": "joke", "crack a joke": "joke",
    "tell me a joke": "joke", "share a joke": "joke",
    "give me a quote": "quote", "motivate me": "quote",
    "inspire me": "quote", "say something inspiring": "quote",
    "share a quote": "quote", "motivational quote": "quote",
    "inspirational quote": "quote",
    "flip a coin": "flip coin", "toss a coin": "flip coin",
    "heads or tails": "flip coin", "coin flip": "flip coin",
    "toss coin": "flip coin",
    "roll a dice": "roll dice", "roll a die": "roll dice",
    "throw dice": "roll dice", "dice roll": "roll dice",
    "roll the dice": "roll dice",

    # Wikipedia
    "wiki pedia": "wikipedia",
    "definition of": "define ", "meaning of": "define ",
    "search wikipedia": "wikipedia ", "wiki search": "wikipedia ",

    # Weather
    "weather today": "weather", "what's the weather": "weather",
    "how's the weather": "weather", "weather forecast": "weather",
    "temperature today": "weather", "current weather": "weather",
    "weather now": "weather",

    # News
    "latest news": "news", "today's news": "news",
    "top headlines": "news", "what's happening": "news",
    "breaking news": "news", "news update": "news",

    # Help / Greetings
    "halp": "help", "kelp": "help",
    "commands": "help", "what can you do": "help",
    "hey": "hello", "sup": "hello", "what's up": "hello",
    "howdy": "hello", "hiya": "hello",
    "bye": "goodbye", "see you": "goodbye",
    "later": "goodbye", "quit": "goodbye",
    "farewell": "goodbye", "cya": "goodbye",
}

JOKES_LIST = [
    "Why do programmers prefer dark mode? Because light attracts bugs! 🐛",
    "How many programmers to change a lightbulb? None — that's a hardware problem.",
    "A SQL query walks into a bar. It sees two tables. Can I JOIN you?",
    "Why did the developer go broke? He used up all his cache. 💸",
    "What's a programmer's favorite hangout? The Foo Bar. 🍺",
    "Why do Java developers wear glasses? Because they don't C#.",
    "I told my computer I needed a break. Now it sends me Kit Kat ads.",
    "Debugging is like being the detective in a crime movie where you're also the murderer.",
]
QUOTES_LIST = [
    ("The only way to do great work is to love what you do.", "Steve Jobs"),
    ("In the middle of every difficulty lies opportunity.", "Einstein"),
    ("It does not matter how slowly you go as long as you do not stop.", "Confucius"),
    ("Code is like humor. When you have to explain it, it's bad.", "Cory House"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("Programs must be written for people to read.", "SICP"),
]

# ── helpers ───────────────────────────────────────────────────────────────────
def strip_wake_words(text):
    WAKE_PATTERNS = [
        r"^(hey|hi|hello|ok|okay|yo|aye)\s+max[,\.\s]*",
        r"^(hey|hi|hello)\s+mack[,\.\s]*",
        r"^hay\s+max[,\.\s]*",
    ]
    t = text.lower().strip()
    for pat in WAKE_PATTERNS:
        t = re.sub(pat, "", t, flags=re.IGNORECASE).strip()
    return t

def fuzzy_correct(text):
    t = text.lower().strip()
    t = strip_wake_words(t)
    for wrong, right in sorted(FUZZY.items(), key=lambda x: len(x[0]), reverse=True):
        if wrong and wrong in t:
            t = t.replace(wrong, right).strip()
    return t.strip()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def get_user():
    return db.session.get(User, session["user_id"]) if "user_id" in session else None

def log_cmd(user_id, cmd, resp, source="text"):
    try:
        entry = CommandLog(user_id=user_id, command=cmd[:500], response=resp[:2000], source=source)
        db.session.add(entry)
        user = db.session.get(User, user_id)
        if user:
            user.cmd_count = (user.cmd_count or 0) + 1
        db.session.commit()
    except Exception as e:
        log.warning(f"log_cmd error: {e}")

def r_ok(data):  return jsonify({"ok": True,  **data})
def r_err(msg):  return jsonify({"ok": False, "message": msg})


# ══════════════════════════════════════════════════════════════════════════════
#  APP OPEN — v5.4
#  Uses os.startfile on Windows.  After launch, tries to maximize the window
#  via win32gui (if pywin32 is installed).  Falls back gracefully.
# ══════════════════════════════════════════════════════════════════════════════

def _maximize_window_by_exe(exe_name, retries=8, delay=0.4):
    """
    After launching an app, poll for its window and maximize + bring to front.
    Requires pywin32:  pip install pywin32
    Runs in a background thread so it doesn't block the response.
    """
    try:
        import win32gui, win32con, win32process
        name_lower = exe_name.lower().replace(".exe", "")

        def enum_cb(hwnd, found):
            if not win32gui.IsWindowVisible(hwnd):
                return
            title = win32gui.GetWindowText(hwnd).lower()
            # Match by window title containing the app name, OR by process name
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = None
                if PSUTIL:
                    try: proc = psutil.Process(pid)
                    except: pass
                proc_name = proc.name().lower() if proc else ""
                if name_lower in title or name_lower in proc_name or proc_name.startswith(name_lower):
                    found.append(hwnd)
            except:
                pass

        for _ in range(retries):
            time.sleep(delay)
            found = []
            try: win32gui.EnumWindows(enum_cb, found)
            except: pass
            if found:
                hwnd = found[0]
                try:
                    win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
                    win32gui.SetForegroundWindow(hwnd)
                    win32gui.BringWindowToTop(hwnd)
                except: pass
                return
    except ImportError:
        pass  # pywin32 not installed — silently skip
    except Exception as e:
        log.warning(f"maximize_window error: {e}")


def open_app_serverside(app_name_key):
    """Launch a local app. Returns (success, message, exe_hint)."""
    key = app_name_key.lower().strip()

    if IS_WIN:
        # ── URI scheme apps (Settings, Camera, etc.)
        uri = APP_URI_WIN.get(key)
        if uri:
            try:
                os.startfile(uri)
                return True, f"Opened {key}"
            except Exception as e:
                try:
                    subprocess.Popen(f'start "" "{uri}"', shell=True)
                    return True, f"Opened {key}"
                except Exception as e2:
                    return False, str(e2)

        # ── Regular .exe apps
        exe = APP_MAP_WIN.get(key)
        if not exe:
            return False, f"App '{key}' not found in app map"

        # Try os.startfile first
        try:
            os.startfile(exe)
            # Maximize in background thread
            threading.Thread(
                target=_maximize_window_by_exe,
                args=(exe,),
                daemon=True
            ).start()
            return True, f"Opened {exe}"
        except Exception:
            pass

        # Fallback: subprocess
        try:
            flags = 0
            if exe.lower() in ("cmd.exe", "powershell.exe", "windowsterminal.exe"):
                flags = subprocess.CREATE_NEW_CONSOLE
            proc = subprocess.Popen(exe, shell=True, creationflags=flags)
            threading.Thread(
                target=_maximize_window_by_exe,
                args=(exe,),
                daemon=True
            ).start()
            return True, f"Opened {exe}"
        except Exception as e:
            # Last resort: start command
            try:
                subprocess.Popen(f'start "" "{exe}"', shell=True)
                return True, f"Opened {exe}"
            except Exception as e2:
                return False, str(e2)

    elif IS_LINUX:
        cmd_str = APP_MAP_LINUX.get(key)
        if not cmd_str:
            return False, f"App '{key}' not found"
        try:
            subprocess.Popen(cmd_str.split(), start_new_session=True)
            return True, f"Opened {key}"
        except Exception as e:
            return False, str(e)

    elif IS_MAC:
        try:
            subprocess.Popen(["open", "-a", key.title()], start_new_session=True)
            return True, f"Opened {key}"
        except Exception as e:
            return False, str(e)

    return False, "Unsupported OS"


# ══════════════════════════════════════════════════════════════════════════════
#  APP CLOSE — FIXED v5.4
#
#  Strategy (in order):
#    1. psutil — scan all processes, kill any whose name matches (case-insensitive)
#    2. taskkill /F /IM <name>  — for each name in the comma-separated list
#    3. taskkill by window title (UWP fallback) — for apps that hide under
#       ApplicationFrameHost.exe (Calculator, Camera, etc.)
#    4. Report actual result
# ══════════════════════════════════════════════════════════════════════════════

def _kill_by_title_windows(title_keyword):
    """Kill a window whose title contains title_keyword using taskkill /FI."""
    try:
        result = subprocess.run(
            f'taskkill /F /FI "WINDOWTITLE eq *{title_keyword}*"',
            shell=True, capture_output=True, text=True
        )
        return result.returncode == 0
    except:
        return False


def close_app_serverside(app_name_key):
    """Kill a running app. Returns (success, message)."""
    key = app_name_key.lower().strip()
    proc_entry = PROC_MAP.get(key)

    if not proc_entry:
        return False, f"Process for '{key}' not found in process map"

    # Build list of candidate process names to try
    proc_names = [p.strip() for p in proc_entry.split(",")]

    if IS_WIN:
        killed_total = 0

        # ── Strategy 1: psutil (most reliable for Win32 apps)
        if PSUTIL:
            for proc_name in proc_names:
                # Skip generic host processes in psutil pass
                if proc_name.lower() in ("applicationframehost.exe",):
                    continue
                try:
                    for proc in psutil.process_iter(["name", "pid"]):
                        try:
                            if proc.info["name"].lower() == proc_name.lower():
                                proc.kill()
                                killed_total += 1
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                except Exception as e:
                    log.warning(f"psutil kill failed for {proc_name}: {e}")

        # ── Strategy 2: taskkill /F /IM for each process name
        for proc_name in proc_names:
            if proc_name.lower() in ("applicationframehost.exe",):
                continue
            try:
                r = subprocess.run(
                    f'taskkill /F /IM "{proc_name}"',
                    shell=True, capture_output=True, text=True
                )
                if r.returncode == 0:
                    killed_total += 1
            except Exception:
                pass

        # ── Strategy 3: Kill by window title (UWP / Store apps)
        title_kw = UWP_TITLE_MAP.get(key)
        if title_kw:
            if _kill_by_title_windows(title_kw):
                killed_total += 1

        # ── Strategy 4: ApplicationFrameHost — last resort for stubborn UWPs
        # Only use if we still haven't killed anything AND it's a UWP app
        if killed_total == 0 and title_kw:
            try:
                # Use PowerShell to close the UWP app package
                pkg_close = (
                    f'powershell -Command "Get-Process | '
                    f'Where-Object {{$_.MainWindowTitle -like \'*{title_kw}*\'}} | '
                    f'Stop-Process -Force"'
                )
                r = subprocess.run(pkg_close, shell=True, capture_output=True, text=True)
                if r.returncode == 0:
                    killed_total += 1
            except:
                pass

        if killed_total > 0:
            return True, f"Closed {key} successfully"
        else:
            return False, f"{key} is not running (or already closed)"

    elif IS_LINUX or IS_MAC:
        killed = False
        for proc_name in proc_names:
            ret = os.system(f"pkill -f '{proc_name}' 2>/dev/null")
            if ret == 0:
                killed = True
        return (True, f"Closed {key}") if killed else (False, f"{key} is not running")

    return False, "Unsupported OS"


# ── auth routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "").strip()
        user = User.query.filter_by(username=username).first()
        if not user:
            error = "Username not found."
        elif not check_password_hash(user.password, password):
            error = "Incorrect password."
        else:
            session["user_id"]  = user.id
            session["username"] = user.username
            session["display"]  = user.display_name or user.username
            user.last_login = datetime.datetime.now(datetime.timezone.utc)
            db.session.commit()
            return redirect(url_for("dashboard"))
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        username     = request.form.get("username", "").strip().lower()
        email        = request.form.get("email", "").strip().lower()
        display_name = request.form.get("display_name", "").strip()
        password     = request.form.get("password", "").strip()
        confirm      = request.form.get("confirm", "").strip()
        if len(username) < 3:
            error = "Username must be at least 3 characters."
        elif not re.match(r"^[a-z0-9_]+$", username):
            error = "Username can only contain letters, numbers, and underscores."
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            error = "Enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif User.query.filter_by(username=username).first():
            error = "Username already taken."
        elif User.query.filter_by(email=email).first():
            error = "Email already registered."
        else:
            user = User(
                username=username, email=email,
                display_name=display_name or username.capitalize(),
                password=generate_password_hash(password)
            )
            db.session.add(user); db.session.commit()
            session["user_id"]  = user.id
            session["username"] = user.username
            session["display"]  = user.display_name
            return redirect(url_for("dashboard"))
    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_user()
    recent = CommandLog.query.filter_by(user_id=user.id)\
                 .order_by(CommandLog.created_at.desc()).limit(20).all()
    notes  = Note.query.filter_by(user_id=user.id)\
                 .order_by(Note.created_at.desc()).limit(5).all()
    return render_template("dashboard.html", user=user, recent=recent,
                           notes=notes, version=VERSION,
                           psutil_ok=PSUTIL, claude_ok=CLAUDE)

@app.route("/api/greeting")
@login_required
def api_greeting():
    user = get_user()
    name = user.display_name or user.username
    h = datetime.datetime.now().hour
    if h < 12:   g = "Good morning"
    elif h < 18: g = "Good afternoon"
    else:        g = "Good evening"
    msg = f"{g}, {name}! I'm MAX v{VERSION}, your Personal Assistant. How can I help you today?"
    return r_ok({"message": msg, "name": name, "greeting": g})

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = get_user()
    msg = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "profile":
            user.display_name = request.form.get("display_name","").strip() or user.display_name
            new_email = request.form.get("email","").strip().lower()
            if new_email and new_email != user.email:
                if User.query.filter_by(email=new_email).first():
                    msg = ("error", "Email already in use.")
                else:
                    user.email = new_email
            db.session.commit()
            session["display"] = user.display_name
            msg = ("ok", "Profile updated.")
        elif action == "password":
            cur = request.form.get("current","")
            new = request.form.get("new","")
            if not check_password_hash(user.password, cur):
                msg = ("error", "Current password incorrect.")
            elif len(new) < 6:
                msg = ("error", "New password must be at least 6 characters.")
            else:
                user.password = generate_password_hash(new)
                db.session.commit()
                msg = ("ok", "Password changed.")
        elif action == "apikeys":
            user.ow_api_key   = request.form.get("ow_key","").strip()
            user.news_api_key = request.form.get("news_key","").strip()
            user.claude_key   = request.form.get("claude_key","").strip()
            db.session.commit()
            msg = ("ok", "API keys saved.")
    return render_template("settings.html", user=user, msg=msg)

@app.route("/api/settings", methods=["GET","POST"])
@login_required
def api_settings():
    user = get_user()
    if request.method == "POST":
        data = request.json or {}
        if "ow_key"     in data: user.ow_api_key   = data["ow_key"].strip()
        if "news_key"   in data: user.news_api_key  = data["news_key"].strip()
        if "claude_key" in data: user.claude_key    = data["claude_key"].strip()
        db.session.commit()
        return r_ok({"message":"Settings saved."})
    return r_ok({
        "ow_key":        "set" if user.ow_api_key   else "",
        "news_key":      "set" if user.news_api_key  else "",
        "anthropic_key": "set" if user.claude_key    else "",
        "cmd_count":     user.cmd_count or 0,
        "created_at":    user.created_at.strftime("%b %d, %Y") if user.created_at else "—",
        "last_login":    user.last_login.strftime("%b %d %H:%M") if user.last_login else "Never",
    })

# ── Open app endpoint ─────────────────────────────────────────────────────────
@app.route("/api/open_app", methods=["POST"])
@login_required
def api_open_app():
    data    = request.json or {}
    app_key = data.get("app_key", "").lower().strip()
    user    = get_user()
    name    = user.display_name or user.username
    if not app_key:
        return r_err("No app specified.")
    success, detail = open_app_serverside(app_key)
    if success:
        return r_ok({"message": f"{name}, opening {app_key.title()}! ✅", "app_key": app_key})
    else:
        # Try terminal fallback for "terminal" if wt.exe not found
        if app_key == "terminal":
            success2, detail2 = open_app_serverside("cmd")
            if success2:
                return r_ok({"message": f"{name}, opening Command Prompt! ✅", "app_key": "cmd"})
        return r_err(f"{name}, could not open {app_key}: {detail}")

# ── Close app endpoint ────────────────────────────────────────────────────────
@app.route("/api/close_app", methods=["POST"])
@login_required
def api_close_app():
    data    = request.json or {}
    app_key = data.get("app_key", "").lower().strip()
    user    = get_user()
    name    = user.display_name or user.username
    if not app_key:
        return r_err("No app specified.")
    success, detail = close_app_serverside(app_key)
    if success:
        return r_ok({"message": f"{name}, {app_key} has been closed! ✅"})
    else:
        return r_err(f"{name}, {detail}")

# ── Main command endpoint ─────────────────────────────────────────────────────
@app.route("/api/command", methods=["POST"])
@login_required
def api_command():
    user = get_user()
    data = request.json or {}
    raw  = data.get("command", "").strip()
    src  = data.get("source", "text")
    if not raw:
        return r_err("Empty command")
    c = fuzzy_correct(raw)
    response = dispatch(c, user)
    log_cmd(user.id, raw, response.get("message",""), src)
    return r_ok(response)

def dispatch(c, user):
    name = user.display_name or user.username

    # ── PRIORITY 1: System metrics
    if re.search(r"\b(battery|bat\s*percent|bat\s*level|bat\s*status|bat\s*charge)\b", c):
        return feat_battery(name)
    if re.search(r"\bcpu\b", c):
        return feat_cpu(name)
    if re.search(r"\b(ram|memory\s*usage|memory\s*left)\b", c):
        return feat_ram(name)
    if re.search(r"\b(disk|storage|hard\s*drive|ssd\s*space)\b", c):
        return feat_disk(name)

    # ── time / date
    if re.search(r"date.*time|time.*date", c):
        n = datetime.datetime.now()
        return {"type":"info","message":f"{name}, it's {n.strftime('%A, %B %d')} and {n.strftime('%I:%M %p')}."}
    if re.search(r"what.?time|current.?time|tell.*time", c) and "timer" not in c:
        t = datetime.datetime.now().strftime("%I:%M:%S %p")
        return {"type":"info","message":f"{name}, the time is {t} ⏰"}
    if re.search(r"what.?date|today.*date|current.?date", c):
        d = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return {"type":"info","message":f"{name}, today is {d} 📅"}

    # ── close tab (generic)
    if re.search(r"^close\s*(tab|current\s*tab|this\s*tab|the\s*tab|it|that|window|my\s*tab)$", c):
        return {"type":"close_tab","message":f"{name}, closing the tab! 🗑",
                "action":"close_tab","site_key":"__last__"}

    # ── close site/app by name
    close_site_m = re.match(r"^close\s+(\w[\w\s]*)(?:\s+tab)?$", c)
    if close_site_m:
        target = close_site_m.group(1).strip().lower()
        # Check sites first — return site_key so JS can handle it
        for key in SITES:
            if key == target or key in target or target in key:
                return {"type":"close_tab","message":f"{name}, closing {SITES[key][0]} tab! 🗑",
                        "action":"close_tab","site_key":key}
        # Check desktop apps
        for key in sorted(PROC_MAP.keys(), key=len, reverse=True):
            if key == target or key in target or target in key:
                ok, detail = close_app_serverside(key)
                msg = f"{name}, closed {key}! ✅" if ok else f"{name}, {detail}"
                return {"type":"ok" if ok else "warn","message":msg}

    # ── open site / app
    open_m = re.match(r"(?:open|launch|go\s+to|load|show)\s+(.+)", c)
    if open_m:
        target = open_m.group(1).strip().lower()
        # Websites — exact key match first, then partial
        for key, (sname, url) in SITES.items():
            if key == target or key in target or target in key:
                return {"type":"open","url":url,"message":f"Opening {sname} for you, {name}! 🌐",
                        "site_key":key,"site_name":sname}
        # Desktop apps
        amap = {**APP_MAP_WIN, **APP_URI_WIN} if IS_WIN else APP_MAP_LINUX
        for key in sorted(amap.keys(), key=len, reverse=True):
            if key == target or key in target or target in key:
                ok, detail = open_app_serverside(key)
                msg = f"{name}, opening {key.title()}! ✅" if ok else f"{name}, couldn't open {key}: {detail}"
                return {"type":"app_opened" if ok else "error","message":msg,"app_key":key}
        return {"type":"error","message":f"{name}, I couldn't find '{target}'. Try the Sites tab."}

    # ── standalone app name (e.g. just "notepad" or "calculator")
    amap = {**APP_MAP_WIN, **APP_URI_WIN} if IS_WIN else APP_MAP_LINUX
    for key in sorted(amap.keys(), key=len, reverse=True):
        if re.search(r'\b' + re.escape(key) + r'\b', c):
            if re.search(r"\b(close|stop|shut|kill|exit)\b", c):
                break
            ok, detail = open_app_serverside(key)
            msg = f"{name}, opening {key.title()}! ✅" if ok else f"{name}, couldn't open {key}: {detail}"
            return {"type":"app_opened" if ok else "error","message":msg,"app_key":key}

    # ── direct site keyword (just "youtube", "github", etc.)
    for key, (sname, url) in SITES.items():
        if re.search(rf"\b{re.escape(key)}\b", c) and not re.search(r"\b(close|shut|kill)\b", c):
            if c.strip() == key:
                return {"type":"open","url":url,"message":f"Opening {sname}, {name}! 🌐",
                        "site_key":key,"site_name":sname}

    # ── close fallback
    close_m = re.match(r"(close|stop|shut|kill)\s+(.+)", c)
    if close_m:
        target = close_m.group(2).strip().lower()
        for key in SITES:
            if key in target:
                return {"type":"close_tab","message":f"{name}, closing {key} tab! 🗑",
                        "action":"close_tab","site_key":key}
        for key in sorted(PROC_MAP.keys(), key=len, reverse=True):
            if key in target or target in key:
                ok, detail = close_app_serverside(key)
                msg = f"{name}, {key} closed! ✅" if ok else f"{name}, {detail}"
                return {"type":"ok" if ok else "warn","message":msg}
        return {"type":"error","message":f"{name}, I couldn't find '{target}' to close."}

    # ── search
    search_m = re.match(r"(search|google|find|look\s*up)\s+(.+)", c)
    if search_m:
        q = search_m.group(2).strip()
        url = f"https://www.google.com/search?q={q.replace(' ','+')}"
        return {"type":"open","url":url,"message":f"Searching Google for '{q}', {name}! 🔍",
                "site_key":"google_search","site_name":"Google Search"}

    # ── youtube search
    if re.search(r"youtube\s+search|search\s+youtube|play.*youtube", c):
        q = re.sub(r"youtube|search|play|watch","",c).strip()
        if q:
            url = f"https://www.youtube.com/results?search_query={q.replace(' ','+')}"
            return {"type":"open","url":url,"message":f"Searching YouTube for '{q}', {name}! ▶",
                    "site_key":"youtube","site_name":"YouTube"}
        return {"type":"open","url":"https://www.youtube.com","message":f"Opening YouTube, {name}!",
                "site_key":"youtube","site_name":"YouTube"}

    # ── calculate
    if re.search(r"\b(calculate|compute|evaluate|solve|math)\b", c):
        expr = re.sub(r"\b(calculate|compute|evaluate|solve|math)\b","",c).strip()
        return feat_calculate(expr, name)

    # ── Wikipedia
    if re.search(r"\bwikipedia\b|\bwiki\b", c):
        q = re.sub(r"\bwikipedia\b|\bwiki\b","",c).strip()
        return feat_wikipedia(q, name)

    # ── define
    if re.search(r"\b(define|definition|meaning|dictionary)\b", c):
        w = re.sub(r"\b(define|definition|meaning of|dictionary)\b","",c).strip()
        return feat_define(w, name)

    # ── weather
    if re.search(r"\b(weather|temperature|forecast)\b", c):
        m = re.search(r"\bin\s+([a-z ]+)$", c)
        city = m.group(1).strip() if m else "Warangal"
        return feat_weather(city, user)

    # ── news
    if re.search(r"\b(news|headlines)\b", c):
        return feat_news(user)

    # ── system info
    if re.search(r"\bsystem\s*info\b", c):
        return feat_sysinfo(name)

    if re.search(r"\bprocess", c):
        return feat_processes(name)
    if re.search(r"\bnetwork\s*info\b|\bip\s*address\b|\bmy\s*ip\b", c):
        return feat_network(name)
    if re.search(r"\b(ping|latency|internet\s*speed)\b", c):
        return feat_ping(name)

    # ── volume
    if re.search(r"\bvolume\b|\bmute\b|\bunmute\b", c):
        if re.search(r"\b(up|louder|increase)\b", c):      return feat_volume("up", name)
        elif re.search(r"\b(down|quieter|decrease)\b", c): return feat_volume("down", name)
        elif re.search(r"\bmute\b", c):                    return feat_volume("mute", name)
        elif re.search(r"\bunmute\b", c):                  return feat_volume("unmute", name)
        else:                                              return feat_volume("status", name)

    # ── lock / power
    if re.search(r"\block\s*screen\b", c):
        def _lock():
            if IS_WIN:    os.system("rundll32.exe user32.dll,LockWorkStation")
            elif IS_LINUX:
                for cmd_str in ["gnome-screensaver-command -l","xdg-screensaver lock"]:
                    if os.system(f"{cmd_str} 2>/dev/null") == 0: break
        threading.Thread(target=_lock, daemon=True).start()
        return {"type":"ok","message":f"Locking screen, {name}."}

    if re.search(r"\b(sleep|hibernate|suspend)\b", c):
        def _sleep():
            time.sleep(2)
            if IS_WIN:    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            elif IS_LINUX: os.system("systemctl suspend")
            elif IS_MAC:   os.system("pmset sleepnow")
        threading.Thread(target=_sleep, daemon=True).start()
        return {"type":"warn","message":f"Sleeping in 2 seconds. Goodbye {name}!"}

    if re.search(r"\b(shutdown|shut\s*down|turn\s*off|power\s*off)\b", c):
        return {"type":"confirm","action":"shutdown",
                "message":"⚠ Are you sure you want to shut down?"}

    if re.search(r"\b(restart|reboot)\b", c):
        return {"type":"confirm","action":"restart",
                "message":"⚠ Restart the computer? All unsaved work will be lost."}

    # ── joke / quote
    if re.search(r"\bjoke\b", c):
        j = pyjokes.get_joke() if JOKES_LIB else random.choice(JOKES_LIST)
        return {"type":"joke","message":j}
    if re.search(r"\b(quote|inspire|motivate)\b", c):
        q, a = random.choice(QUOTES_LIST)
        return {"type":"quote","message":f'"{q}" — {a}'}

    # ── coin / dice
    if re.search(r"\bflip\s*coin|toss\s*coin|heads\s*or\s*tails\b", c):
        r = "Heads 🪙" if random.random() < 0.5 else "Tails 🪙"
        return {"type":"fun","message":f"{name}, it's {r}!"}
    if re.search(r"\broll\s*(dice|die)\b", c):
        m = re.search(r"(\d+)", c); sides = int(m.group(1)) if m else 6
        r = random.randint(1, sides)
        return {"type":"fun","message":f"{name}, I rolled a {sides}-sided die and got {r}! 🎲"}

    # ── translate
    if re.search(r"\btranslate\b", c):
        text = re.sub(r"\btranslate\b","",c).strip()
        url = f"https://translate.google.com/?text={text}" if text else "https://translate.google.com"
        return {"type":"open","url":url,"message":f"Opening Google Translate, {name}! 🌍",
                "site_key":"translate","site_name":"Google Translate"}

    # ── screenshot
    if re.search(r"\bscreenshot\b", c):
        return feat_screenshot(name)

    # ── greetings
    if re.search(r"\b(hello|hi|hey|greet)\b", c):
        h = datetime.datetime.now().hour
        g = "Good morning" if h<12 else "Good afternoon" if h<18 else "Good evening"
        return {"type":"info","message":f"{g} {name}! How can I help you today? 👋"}
    if re.search(r"\bhow\s*are\s*you\b", c):
        return {"type":"info","message":f"I'm running perfectly, {name}! All systems green. 🟢"}
    if re.search(r"\b(who\s*are\s*you|your\s*name|what\s*are\s*you)\b", c):
        return {"type":"info","message":f"I'm MAX v{VERSION}, your Personal Intelligence Assistant, {name}."}
    if re.search(r"\bthan(k|ks)\b", c):
        return {"type":"info","message":f"You're welcome, {name}! 😊"}
    if re.search(r"\b(help|commands|guide|manual)\b", c):
        return feat_help()
    if re.search(r"\b(bye|goodbye|exit|quit)\b", c):
        return {"type":"goodbye","message":f"Goodbye {name}! Have a great day! 👋"}

    # ── AI fallback via Claude
    if CLAUDE and user.claude_key:
        return feat_claude(c, user)

    return {"type":"unknown","message":f"{name}, I heard '{c}' but didn't understand. Type 'help' to see commands."}

# ── feature functions ─────────────────────────────────────────────────────────
def feat_calculate(expr, name):
    if not expr:
        return {"type":"error","message":f"{name}, please provide an expression."}
    clean = (expr.replace("plus","+").replace("minus","-").replace("times","*")
                 .replace("multiplied by","*").replace("divided by","/")
                 .replace("mod","%").replace("power","**").replace("^","**")
                 .replace("squared","**2").replace("square root of","math.sqrt("))
    if "math.sqrt(" in clean and not clean.strip().endswith(")"):
        clean += ")"
    if re.search(r"[a-zA-Z]", clean.replace("math","").replace("sqrt","").replace("e","2.71828")):
        return {"type":"error","message":f"{name}, I can only evaluate numeric expressions."}
    try:
        result = eval(clean, {"__builtins__":{}, "math":math})
        r = int(result) if isinstance(result, float) and result == int(result) else round(result, 8)
        return {"type":"calc","message":f"{name}, the answer is {r} 🧮","result":r}
    except ZeroDivisionError:
        return {"type":"error","message":f"{name}, I cannot divide by zero!"}
    except Exception:
        return {"type":"error","message":f"{name}, I couldn't evaluate that expression."}

def feat_wikipedia(query, name):
    if not query:
        return {"type":"prompt","message":"What would you like to look up on Wikipedia?","modal":"wiki"}
    if not WIKI:
        url = f"https://en.wikipedia.org/wiki/Special:Search/{query.replace(' ','+')}"
        return {"type":"open","url":url,"message":f"Opening Wikipedia for '{query}', {name}!",
                "site_key":"wikipedia","site_name":"Wikipedia"}
    try:
        wiki_lib.set_lang("en")
        summary = wiki_lib.summary(query, sentences=3, auto_suggest=False)
        return {"type":"wiki","message":summary,"query":query}
    except wiki_lib.exceptions.DisambiguationError as e:
        opts = ", ".join(e.options[:3])
        return {"type":"wiki","message":f"Multiple results: {opts}?","query":query}
    except Exception:
        try:
            summary = wiki_lib.summary(query, sentences=3, auto_suggest=True)
            return {"type":"wiki","message":summary,"query":query}
        except Exception:
            return {"type":"error","message":f"{name}, couldn't find '{query}' on Wikipedia."}

def feat_define(word, name):
    if not word:
        return {"type":"prompt","message":"Which word to define?","modal":"define"}
    if not REQUESTS:
        return {"type":"open","url":f"https://www.merriam-webster.com/dictionary/{word}",
                "message":f"Opening dictionary for '{word}', {name}!",
                "site_key":"dictionary","site_name":"Dictionary"}
    try:
        resp = req_lib.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=6)
        if resp.status_code == 200:
            defn = resp.json()[0]["meanings"][0]["definitions"][0]["definition"]
            return {"type":"define","message":f"'{word}': {defn}","word":word,"definition":defn}
        return {"type":"error","message":f"{name}, no definition found for '{word}'."}
    except Exception:
        return {"type":"error","message":f"{name}, dictionary is unavailable right now."}

def feat_weather(city, user):
    key  = user.ow_api_key
    name = user.display_name or user.username
    if not key:
        return {"type":"api_needed","service":"openweather",
                "message":f"{name}, I need your OpenWeather API key. Go to Settings → API Keys."}
    if not REQUESTS:
        return {"type":"error","message":"requests library not installed."}
    try:
        r = req_lib.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric",
            timeout=6
        ).json()
        if r.get("cod") not in [404, "404"]:
            temp   = round(r["main"]["temp"],1)
            feels  = round(r["main"]["feels_like"],1)
            desc   = r["weather"][0]["description"]
            hum    = r["main"]["humidity"]
            wind   = round(r.get("wind",{}).get("speed",0), 1)
            icon_code = r["weather"][0]["icon"]
            icon_url  = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
            msg = f"{city.title()}: {temp}°C, {desc}, humidity {hum}%, feels like {feels}°C, wind {wind} m/s"
            return {"type":"weather","message":msg,"city":city,"temp":temp,
                    "feels":feels,"desc":desc,"humidity":hum,"wind":wind,"icon":icon_url}
        return {"type":"error","message":f"{name}, city '{city}' not found."}
    except Exception:
        return {"type":"error","message":f"{name}, weather service unavailable."}

def feat_news(user):
    key  = user.news_api_key
    name = user.display_name or user.username
    if not key:
        return {"type":"api_needed","service":"newsapi",
                "message":f"{name}, I need your NewsAPI key. Go to Settings → API Keys."}
    if not REQUESTS:
        return {"type":"error","message":"requests library not installed."}
    try:
        r = req_lib.get(
            f"https://newsapi.org/v2/top-headlines?language=en&pageSize=5&apiKey={key}",
            timeout=6
        ).json()
        if r.get("status") == "ok":
            articles  = r.get("articles",[])[:5]
            headlines = [{"title":a["title"],"url":a.get("url",""),"source":a.get("source",{}).get("name","")} for a in articles]
            return {"type":"news","message":f"{name}, here are today's top headlines:","headlines":headlines}
        return {"type":"error","message":f"{name}, couldn't fetch news: {r.get('message','')}"}
    except Exception:
        return {"type":"error","message":f"{name}, news service unavailable."}

def feat_sysinfo(name):
    if not PSUTIL:
        return {"type":"error","message":f"{name}, psutil is not installed."}
    cpu  = psutil.cpu_percent(interval=0.5)
    mem  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    uname = platform.uname()
    return {
        "type":"sysinfo","message":f"{name}, system info shown below.",
        "data":{
            "os":f"{uname.system} {uname.release}",
            "cpu_pct":cpu,"cpu_cores":psutil.cpu_count(logical=True),
            "ram_pct":round(mem.percent,1),
            "ram_used_gb":round(mem.used/1024**3,2),
            "ram_total_gb":round(mem.total/1024**3,2),
            "disk_pct":round(disk.percent,1),
            "disk_used_gb":round(disk.used/1024**3,1),
            "disk_total_gb":round(disk.total/1024**3,1),
        }
    }

def feat_cpu(name):
    if not PSUTIL:
        return {"type":"error","message":f"{name}, psutil not installed."}
    cpu   = psutil.cpu_percent(interval=0.5)
    freq  = psutil.cpu_freq()
    cores = psutil.cpu_count(logical=True)
    mhz   = round(freq.current) if freq else "N/A"
    return {"type":"metric","message":f"{name}, CPU: {cpu}% on {cores} cores @ {mhz} MHz ⚡",
            "value":cpu,"label":"CPU %","icon":"⚡"}

def feat_ram(name):
    if not PSUTIL: return {"type":"error","message":f"{name}, psutil not installed."}
    m = psutil.virtual_memory()
    return {"type":"metric",
            "message":f"{name}, RAM: {m.percent}% used — {m.used//1024**2} MB of {m.total//1024**2} MB 🧠",
            "value":round(m.percent,1),"label":"RAM %","icon":"🧠"}

def feat_disk(name):
    if not PSUTIL: return {"type":"error","message":f"{name}, psutil not installed."}
    d = psutil.disk_usage("/")
    return {"type":"metric",
            "message":f"{name}, Disk: {d.percent}% full — {d.used/1024**3:.1f} GB of {d.total/1024**3:.1f} GB 💾",
            "value":round(d.percent,1),"label":"Disk %","icon":"💾"}

def feat_battery(name):
    if not PSUTIL: return {"type":"error","message":f"{name}, psutil not installed."}
    b = psutil.sensors_battery()
    if not b:
        return {"type":"info","message":f"{name}, no battery detected — this appears to be a desktop PC. 🔌"}
    st   = "charging ⚡" if b.power_plugged else "discharging 🔋"
    pct  = round(b.percent)
    mins = int(b.secsleft/60) if b.secsleft not in (psutil.POWER_TIME_UNLIMITED, -1) else -1
    extra = f" — approximately {mins} minutes remaining." if mins > 0 else ""
    return {"type":"metric",
            "message":f"{name}, battery is at {pct}% ({st}){extra}",
            "value":pct,"label":"Battery %","icon":"🔋"}

def feat_processes(name):
    if not PSUTIL: return {"type":"error","message":f"{name}, psutil not installed."}
    procs = sorted(psutil.process_iter(["pid","name","cpu_percent"]),
                   key=lambda p: p.info["cpu_percent"] or 0, reverse=True)[:8]
    rows = [{"pid":p.info["pid"],"name":p.info["name"],"cpu":p.info["cpu_percent"]} for p in procs]
    return {"type":"processes","message":f"{name}, top processes by CPU:","rows":rows}

def feat_network(name):
    try:
        host = socket.gethostname(); ip = socket.gethostbyname(host)
        return {"type":"info","message":f"{name}, hostname: {host}, local IP: {ip} 📡"}
    except Exception as e:
        return {"type":"error","message":f"{name}, network error: {e}"}

def feat_ping(name):
    if not REQUESTS:
        return {"type":"error","message":f"{name}, requests not installed."}
    try:
        t0 = time.perf_counter()
        req_lib.get("https://www.google.com", timeout=5)
        ms = int((time.perf_counter()-t0)*1000)
        q  = "excellent" if ms<50 else "good" if ms<100 else "slow"
        return {"type":"metric","message":f"{name}, ping: {ms}ms — {q} connection 📡",
                "value":ms,"label":"Ping ms","icon":"📡"}
    except:
        return {"type":"error","message":f"{name}, ping failed. Check your internet."}

def feat_screenshot(name):
    try:
        import pyautogui
        fname = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        pyautogui.screenshot().save(fname)
        return {"type":"ok","message":f"{name}, screenshot saved as {fname} 📸"}
    except ImportError:
        return {"type":"error","message":f"{name}, pyautogui not installed. Run: pip install pyautogui"}
    except Exception as e:
        return {"type":"error","message":f"{name}, screenshot failed: {e}"}

def feat_volume(action, name):
    if not IS_WIN:
        return {"type":"error","message":f"{name}, volume control is Windows-only."}
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        dev = AudioUtilities.GetSpeakers()
        vc  = cast(dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None), POINTER(IAudioEndpointVolume))
        if action == "up":
            v = min(1.0, vc.GetMasterVolumeLevelScalar()+0.1); vc.SetMasterVolumeLevelScalar(v,None)
            return {"type":"ok","message":f"{name}, volume is now {int(v*100)}%."}
        elif action == "down":
            v = max(0.0, vc.GetMasterVolumeLevelScalar()-0.1); vc.SetMasterVolumeLevelScalar(v,None)
            return {"type":"ok","message":f"{name}, volume is now {int(v*100)}%."}
        elif action == "mute":
            vc.SetMute(1,None); return {"type":"ok","message":f"{name}, muted. 🔇"}
        elif action == "unmute":
            vc.SetMute(0,None); return {"type":"ok","message":f"{name}, unmuted. 🔊"}
        else:
            v = vc.GetMasterVolumeLevelScalar()
            return {"type":"ok","message":f"{name}, volume is {int(v*100)}%."}
    except ImportError:
        return {"type":"error","message":f"{name}, run: pip install pycaw comtypes"}
    except Exception as e:
        return {"type":"error","message":f"{name}, volume error: {e}"}

def feat_claude(cmd, user):
    name = user.display_name or user.username
    try:
        client = anthropic.Anthropic(api_key=user.claude_key)
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=(
                f"You are MAX, a witty personal assistant for {name}. "
                "Keep answers short, helpful, and friendly. "
                "No markdown. Plain text only. Max 3 sentences."
            ),
            messages=[{"role":"user","content":cmd}]
        )
        reply = msg.content[0].text
        return {"type":"ai","message":reply}
    except Exception as e:
        return {"type":"error","message":f"{name}, Claude API error: {e}. Check your API key in Settings."}

def feat_help():
    return {"type":"help","message":"All commands listed below.","commands":[
        ["Time & Date",  "what time / what date / date and time"],
        ["Open Sites",   "open youtube / open gmail / open chatgpt"],
        ["Open Apps",    "open notepad / open calculator / open vscode"],
        ["Close Tabs",   "close tab / close youtube / close gmail"],
        ["Close Apps",   "close notepad / close calculator"],
        ["Search",       "search python tutorials"],
        ["YouTube",      "youtube search lo-fi music"],
        ["Calculate",    "calculate 25 times 4"],
        ["Wikipedia",    "wikipedia black holes"],
        ["Dictionary",   "define algorithm"],
        ["Weather",      "weather in London  (needs OpenWeather key)"],
        ["News",         "news  (needs NewsAPI key)"],
        ["AI Chat",      "Any free question  (needs Claude API key)"],
        ["System",       "system info / cpu / ram / disk / battery / ping"],
        ["Volume",       "volume up / volume down / mute / unmute"],
        ["Screenshot",   "take a screenshot"],
        ["Lock",         "lock screen"],
        ["Sleep",        "sleep / hibernate"],
        ["Shutdown",     "shutdown / restart"],
        ["Fun",          "joke / quote / flip coin / roll dice"],
        ["Translate",    "translate hello world"],
        ["Wake Word",    "hey max / ok max / hi max + any command"],
        ["Help",         "help"],
        ["Goodbye",      "goodbye / bye"],
    ]}

# ── extra API endpoints ───────────────────────────────────────────────────────
@app.route("/api/confirm_action", methods=["POST"])
@login_required
def api_confirm():
    action = (request.json or {}).get("action")
    if action == "shutdown":
        def _s(): time.sleep(3); os.system("shutdown /s /t 1" if IS_WIN else "shutdown -h now")
        threading.Thread(target=_s, daemon=True).start()
        return r_ok({"message":"Shutting down in 3 seconds. Goodbye!"})
    elif action == "restart":
        def _r(): time.sleep(3); os.system("shutdown /r /t 1" if IS_WIN else "reboot")
        threading.Thread(target=_r, daemon=True).start()
        return r_ok({"message":"Restarting in 3 seconds."})
    return r_err("Unknown action")

@app.route("/api/notes", methods=["GET"])
@login_required
def api_notes_get():
    user  = get_user()
    notes = Note.query.filter_by(user_id=user.id).order_by(Note.created_at.desc()).all()
    return r_ok({"notes":[{"id":n.id,"title":n.title,"content":n.content,
                            "created_at":n.created_at.isoformat()} for n in notes]})

@app.route("/api/notes", methods=["POST"])
@login_required
def api_notes_post():
    user = get_user()
    data = request.json or {}
    note = Note(user_id=user.id, title=data.get("title","Untitled")[:200],
                content=data.get("content",""))
    db.session.add(note); db.session.commit()
    return r_ok({"id":note.id,"message":"Note saved!"})

@app.route("/api/notes/<int:nid>", methods=["DELETE"])
@login_required
def api_notes_delete(nid):
    user = get_user()
    note = Note.query.filter_by(id=nid, user_id=user.id).first()
    if not note: return r_err("Note not found")
    db.session.delete(note); db.session.commit()
    return r_ok({"message":"Note deleted."})

@app.route("/api/stats")
@login_required
def api_stats():
    if not PSUTIL:
        return r_ok({"cpu":None,"ram":None,"disk":None,"battery":None})
    cpu  = psutil.cpu_percent(interval=0.2)
    mem  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    bat  = psutil.sensors_battery()
    return r_ok({
        "cpu":     round(cpu,1),
        "ram":     round(mem.percent,1),
        "disk":    round(disk.percent,1),
        "battery": round(bat.percent) if bat else None,
    })

@app.route("/api/history")
@login_required
def api_history():
    user = get_user()
    logs = CommandLog.query.filter_by(user_id=user.id)\
               .order_by(CommandLog.created_at.desc()).limit(50).all()
    return r_ok({"history":[{
        "command":l.command,"response":l.response,
        "source":l.source,"created_at":l.created_at.isoformat()
    } for l in logs]})

# ── init DB ───────────────────────────────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="rushindhra").first():
            default = User(
                username="rushindhra", email="rushindhra@example.com",
                display_name="Rushindhra",
                password=generate_password_hash("max123")
            )
            db.session.add(default); db.session.commit()
            log.info("Default user 'rushindhra' created (password: max123)")

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)