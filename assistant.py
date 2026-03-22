#!/usr/bin/env python3
"""
Max — Personal Assistant v3.2
Wake word : hey max  →  "Yes Rushindhra?"
Fixes     : fuzzy corrections for ALL commands, single tab close, no double triggers
INSTALL:
    pip install SpeechRecognition sounddevice numpy pyttsx3 psutil
    pip install requests wikipedia pyjokes pyautogui pygetwindow
    pip install python-dotenv

API KEYS SETUP:
    Create a file named  .env  in the same folder as this script:
    ─────────────────────────────────
    OPENWEATHER_API_KEY=your_key_here
    NEWS_API_KEY=your_key_here
    ─────────────────────────────────
    Then add  .env  to your  .gitignore  so it is never uploaded to GitHub.
"""

import datetime, webbrowser, os, threading, time, re, socket
import queue, platform, subprocess, random, math
import tkinter as tk
import tkinter.messagebox as msgbox

# ── load .env file if present (python-dotenv) ─────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # dotenv not installed — os.environ.get() still works for system env vars

try:    import speech_recognition as sr;  SR_AVAILABLE = True
except: SR_AVAILABLE = False;             sr = None

SOUNDDEVICE_AVAILABLE = False
try:
    import sounddevice as sd, numpy as np
    SOUNDDEVICE_AVAILABLE = True
except: pass

PYAUDIO_AVAILABLE = False
try:    import pyaudio; PYAUDIO_AVAILABLE = True
except: pass

try:    import pyttsx3;   TTS_AVAILABLE = True
except: TTS_AVAILABLE = False

try:    import psutil;    PSUTIL_AVAILABLE = True
except: PSUTIL_AVAILABLE = False; psutil = None

try:    import requests;  REQUESTS_AVAILABLE = True
except: REQUESTS_AVAILABLE = False; requests = None

try:    import wikipedia; WIKI_AVAILABLE = True
except: WIKI_AVAILABLE = False; wikipedia = None

try:    import pyjokes;   JOKES_AVAILABLE = True
except: JOKES_AVAILABLE = False; pyjokes = None

try:    import pyautogui; PYAUTOGUI_AVAILABLE = True
except: PYAUTOGUI_AVAILABLE = False; pyautogui = None

try:    import pygetwindow as gw; PYGETWINDOW_AVAILABLE = True
except: PYGETWINDOW_AVAILABLE = False; gw = None

VERSION   = "3.2"
USER_NAME = "Rushindhra"
WAKE_WORD = "hey max"
WAKE_PHRASES = [
    "hey max","hey macs","hey mac","hey marks","hey mark",
    "hey marx","a max","okay max","ok max","hi max",
    "hay max","aye max","max","hey man",
]

SAMPLE_RATE   = 16000
CHANNELS      = 1
DTYPE         = "int16"
CHUNK_MS      = 30
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_MS / 1000)

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"
IS_MAC     = platform.system() == "Darwin"

C = {
    "bg0":"#070B14","bg1":"#0C1220","bg2":"#111827","bg3":"#192338","bg4":"#1F2D47",
    "gold":"#F5C518","gold_dim":"#8A6C0A","teal":"#00E5CC","violet":"#9B59FF",
    "coral":"#FF5C5C","mint":"#39FF85","txt0":"#F0F6FF","txt1":"#8DA4C8",
    "txt2":"#3D566E","border":"#1E3054","orange":"#FF8C30",
}
FNT_BTN  = ("Helvetica Neue", 9, "bold")
FNT_MONO = ("Courier New", 10)

FUZZY_CORRECTIONS = {
    "charging ppt":"chatgpt","charge ppt":"chatgpt","chat gpt":"chatgpt",
    "charging pt":"chatgpt","chargingppt":"chatgpt","charging bt":"chatgpt",
    "chat gt":"chatgpt","charge gt":"chatgpt","charging gpt":"chatgpt",
    "sharjah ppt":"chatgpt","chart ppt":"chatgpt","sharp pt":"chatgpt",
    "charging pp":"chatgpt","charting ppt":"chatgpt","chat dpt":"chatgpt",
    "jemini":"gemini","jimini":"gemini","jimmy":"gemini","jamini":"gemini",
    "germini":"gemini","jimmie":"gemini","jemmy":"gemini","gimini":"gemini",
    "ge mini":"gemini","jay mini":"gemini",
    "you tube":"youtube","utube":"youtube","u tube":"youtube","you to":"youtube",
    "you too":"youtube","youth":"youtube","eu tube":"youtube",
    "what's app":"whatsapp","what sapp":"whatsapp","watsapp":"whatsapp",
    "whats up":"whatsapp","what sup":"whatsapp","what's up":"whatsapp",
    "what's ab":"whatsapp","what app":"whatsapp",
    "insta gram":"instagram","insta":"instagram","instant gram":"instagram",
    "instagram ram":"instagram","in stagram":"instagram",
    "linked in":"linkedin","lincoln":"linkedin","linked inn":"linkedin",
    "link din":"linkedin","link dein":"linkedin","linkin":"linkedin",
    "git hub":"github","give hub":"github","git up":"github",
    "get hub":"github","give up":"github",
    "stack overflow":"stackoverflow","stack over flow":"stackoverflow",
    "stack overflows":"stackoverflow",
    "disk cord":"discord","this cord":"discord","disc cord":"discord",
    "dis cord":"discord","this court":"discord",
    "spot if i":"spotify","spot ify":"spotify","spot a fly":"spotify",
    "spot fire":"spotify","spot ifi":"spotify",
    "no shun":"notion","no tion":"notion","ocean":"notion","noshun":"notion",
    "net flix":"netflix","net flex":"netflix","net flicks":"netflix",
    "google map":"maps","google maps":"maps","g maps":"maps",
    "google drive":"drive","g drive":"drive",
    "google meet":"meet","g meet":"meet",
    "google docs":"docs","g docs":"docs",
    "google sheets":"sheets","g sheets":"sheets",
    "amaz on":"amazon","amazone":"amazon",
    "red it":"reddit","red dit":"reddit",
    "twit er":"twitter","twitt er":"twitter",
    "be s code":"vscode","vs cold":"vscode","the s code":"vscode",
    "vs co":"vscode","visual studio code":"vscode","visual studio":"vscode",
    "be escort":"vscode","visa code":"vscode","vs court":"vscode",
    "bs code":"vscode","v s code":"vscode",
    "power point":"powerpoint","power pnt":"powerpoint","power pint":"powerpoint",
    "power points":"powerpoint","ppt":"powerpoint",
    "note pad":"notepad","notes pad":"notepad","noted":"notepad",
    "note path":"notepad","not pad":"notepad",
    "calculate or":"calculator","calculated":"calculator",
    "calculation":"calculator","calculater":"calculator",
    "task manage":"task manager","tasks manager":"task manager",
    "task manger":"task manager",
    "file explorer":"explorer","files explorer":"explorer",
    "file manager":"explorer",
    "fire fox":"firefox","fire fo":"firefox",
    "microsoft edge":"edge","ms edge":"edge",
    "ms paint":"paint","microsoft paint":"paint",
    "microsoft word":"word","ms word":"word",
    "microsoft excel":"excel","ms excel":"excel",
    "google chrome":"chrome","g chrome":"chrome",
    "what's the time":"what time","what is the time":"what time",
    "current time":"what time","tell me the time":"what time",
    "what's the date":"what date","what is the date":"what date",
    "current date":"what date","tell me the date":"what date",
    "todays date":"what date","today's date":"what date",
    "date and time":"date and time","time and date":"date and time",
    "google search":"search","search for":"search","look up":"search",
    "can you search":"search","please search":"search",
    "youtube search":"youtube search","search youtube":"youtube search",
    "play on youtube":"youtube search","find on youtube":"youtube search",
    "calculation":"calculate","solve this":"calculate","compute":"calculate",
    "what is the answer":"calculate","math":"calculate",
    "what's 2 plus 2":"calculate 2 plus 2",
    "screen shot":"screenshot","screen short":"screenshot",
    "take screen":"screenshot","capture screen":"screenshot",
    "screen capture":"screenshot","print screen":"screenshot",
    "system and for":"system info","system information":"system info",
    "system details":"system info","show system":"system info",
    "cp you":"cpu","see p you":"cpu","cpu usage":"cpu",
    "processor":"cpu","processor usage":"cpu",
    "ram usage":"ram","memory usage":"ram","ram memory":"ram",
    "disk space":"disk","disk usage":"disk","hard disk":"disk",
    "storage":"disk","hard drive":"disk",
    "battery level":"battery","battery status":"battery","batteries":"battery",
    "battery percentage":"battery","how much battery":"battery",
    "running processes":"processes","top processes":"processes",
    "active processes":"processes","process list":"processes",
    "network information":"network info","network status":"network info",
    "local ip":"network info","hostname":"network info",
    "my ip address":"my ip","what is my ip":"my ip","ip address":"my ip",
    "public ip address":"my ip","external ip":"my ip",
    "ping test":"ping","test ping":"ping","test connection":"ping",
    "check internet":"ping","internet speed":"ping",
    "lock the screen":"lock screen","lock my screen":"lock screen",
    "screen lock":"lock screen","lock the computer":"lock screen",
    "go to sleep":"sleep","put to sleep":"sleep","hibernate":"sleep",
    "suspend":"sleep",
    "shut down":"shutdown","turn off":"shutdown","power off":"shutdown",
    "switch off":"shutdown","shut it down":"shutdown",
    "re start":"restart","re boot":"restart","start again":"restart",
    "log out":"logout","sign out":"logout","log me out":"logout",
    "switch user":"logout",
    "wiki pedia":"wikipedia","wikki":"wikipedia","wickipedia":"wikipedia",
    "wiki search":"wikipedia","search wikipedia":"wikipedia",
    "tell me about":"wikipedia","what is":"wikipedia","who is":"wikipedia",
    "definition of":"define","meaning of":"define","what does":"define",
    "dictionary":"define","look up word":"define","define the word":"define",
    "weather today":"weather","today's weather":"weather",
    "temperature outside":"weather","what's the weather":"weather",
    "how's the weather":"weather","weather forecast":"weather",
    "weather report":"weather",
    "latest news":"news","today's news":"news","news update":"news",
    "what's in the news":"news","current news":"news","top headlines":"news",
    "news headlines":"news",
    "volume up":"volume up","turn up volume":"volume up",
    "increase volume":"volume up","louder":"volume up",
    "volume down":"volume down","turn down volume":"volume down",
    "decrease volume":"volume down","quieter":"volume down",
    "mute the sound":"mute","turn off sound":"mute","silence":"mute",
    "unmute the sound":"unmute","turn on sound":"unmute",
    "what is the volume":"volume","current volume":"volume",
    "set a timer":"set timer","start a timer":"set timer",
    "start timer":"set timer","create timer":"set timer",
    "countdown":"set timer","timer for":"set timer",
    "set an alarm":"set alarm","start an alarm":"set alarm",
    "create alarm":"set alarm","alarm for":"set alarm",
    "wake me up":"set alarm","wake me at":"set alarm",
    "create a note":"create note","take a note":"create note",
    "new note":"create note","open note":"create note",
    "make a note":"create note","write a note":"create note",
    "quick note":"create note","note down":"create note",
    "what's in clipboard":"clipboard","show clipboard":"clipboard",
    "read clipboard":"clipboard","paste content":"clipboard",
    "clear the clipboard":"clear clipboard","empty clipboard":"clear clipboard",
    "tell a joke":"joke","say a joke":"joke","give me a joke":"joke",
    "make me laugh":"joke","funny joke":"joke","crack a joke":"joke",
    "give me a quote":"quote","motivate me":"quote","inspire me":"quote",
    "motivation":"quote","inspiration":"quote","inspirational quote":"quote",
    "flip a coin":"flip coin","toss a coin":"flip coin",
    "heads or tails":"flip coin","coin toss":"flip coin",
    "roll a dice":"roll dice","roll a die":"roll dice","roll the dice":"roll dice",
    "random number":"roll dice","pick a number":"roll dice",
    "translation":"translate","translator":"translate",
    "translate this":"translate","convert language":"translate",
    "language translate":"translate",
    "show files":"list files","show all files":"list files",
    "what files":"list files","display files":"list files",
    "files here":"list files","current files":"list files",
    "hey there":"hello","hi there":"hello","hello max":"hello",
    "how are you doing":"how are you","how do you do":"how are you",
    "are you okay":"how are you","how is it going":"how are you",
    "what's your name":"who are you","what are you":"who are you",
    "tell me about yourself":"who are you",
    "thank you max":"thank you","thanks max":"thank you",
    "thank you so much":"thank you","many thanks":"thank you",
    "what can you do":"help","show commands":"help","show help":"help",
    "list commands":"help","available commands":"help",
    "bye max":"goodbye","goodbye max":"goodbye","see you":"goodbye",
    "see you later":"goodbye","exit":"goodbye","quit":"goodbye",
    "halp":"help","helf":"help","hep":"help","kelp":"help","hepl":"help",
    "hulp":"help","hilp":"help","holp":"help","hel":"help","heip":"help",
    "hlp":"help","hlep":"help","h e l p":"help",
    "help me":"help","what can you do":"help","what do you do":"help",
    "what commands":"help","all commands":"help","give me help":"help",
    "i need help":"help","can you help":"help","please help":"help",
    "tell me commands":"help","show me commands":"help",
    "what are your commands":"help","how to use":"help",
    "instructions":"help","guide":"help","manual":"help",
    "features":"help","capabilities":"help",
    "what can max do":"help","max commands":"help","max help":"help",
    "commands list":"help","helper":"help","helping":"help","helps":"help",
    "close the tab":"close","shut the tab":"close","kill the tab":"close",
    "close this tab":"close","close tab":"close",
}

def _fuzzy_correct(text):
    t = text.lower().strip()
    for wrong in sorted(FUZZY_CORRECTIONS.keys(), key=len, reverse=True):
        if wrong in t:
            correct = FUZZY_CORRECTIONS[wrong]
            fixed = t.replace(wrong, correct)
            if fixed != t:
                _gui(_cwrite, f"  [corrected] '{wrong}' → '{correct}'\n", "dim")
            return fixed
    return t

# ── TTS worker ────────────────────────────────────────────────────────────────
_tts_q = queue.Queue()

def _tts_worker():
    if not TTS_AVAILABLE:
        while True: _tts_q.get(); _tts_q.task_done()
    engine = None
    while True:
        text = _tts_q.get()
        if text is None: _tts_q.task_done(); break
        if engine is None:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 155)
                engine.setProperty("volume", 1.0)
                voices = engine.getProperty("voices") or []
                if len(voices) > 1: engine.setProperty("voice", voices[1].id)
            except: engine = None
        if engine:
            try: engine.say(text); engine.runAndWait()
            except: engine = None
        _tts_q.task_done()

threading.Thread(target=_tts_worker, daemon=True).start()

# ── GUI queue ─────────────────────────────────────────────────────────────────
_gui_q = queue.Queue()
def _gui(fn, *args): _gui_q.put((fn, args))
def _flush_gui():
    try:
        while True:
            fn, args = _gui_q.get_nowait(); fn(*args)
    except queue.Empty: pass
    ROOT.after(40, _flush_gui)

def _cwrite(text, tag="normal"):
    console.config(state=tk.NORMAL)
    console.insert(tk.END, text, tag)
    console.see(tk.END)
    console.config(state=tk.DISABLED)

def speak(text):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    _gui(_cwrite, f"[{ts}] MAX: {text}\n", "pa")
    _tts_q.put(text)

def speak_and_wait(text):
    """Speak text and block until TTS fully finishes."""
    speak(text)
    _tts_q.join()

def user_echo(text):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    _gui(_cwrite, f"[{ts}] {USER_NAME}: {text}\n", "user")

def info(t):  _gui(_cwrite, f"  i  {t}\n", "info")
def warn(t):  _gui(_cwrite, f"  !  {t}\n", "warn")
def err(t):   _gui(_cwrite, f"  x  {t}\n", "err")

def set_status(text, color=None):
    _gui(_do_status, text, color or C["teal"])
def _do_status(text, color):
    status_var.set(text); status_lbl.config(fg=color)

def set_wake_led(state):
    _gui(_do_led, state)
def _do_led(state):
    S = {"idle":("IDLE",C["txt2"]),"scanning":("SCANNING",C["gold"]),
         "heard":("WAKE!",C["mint"]),"listening":("LISTENING",C["coral"])}
    t, c = S.get(state, S["idle"])
    wake_led.config(text=t, fg=c)

# ── mic ───────────────────────────────────────────────────────────────────────
_SPEECH_THRESHOLD = 150
_CALIBRATED       = False

def _calibrate():
    global _SPEECH_THRESHOLD, _CALIBRATED
    if _CALIBRATED or not SOUNDDEVICE_AVAILABLE: return
    try:
        info("Calibrating mic — stay quiet 1 s...")
        data = sd.rec(SAMPLE_RATE, samplerate=SAMPLE_RATE, channels=1, dtype=DTYPE)
        sd.wait()
        rms = max(50, float(np.sqrt(np.mean(data.astype(np.float32)**2))))
        _SPEECH_THRESHOLD = min(400, max(80, int(rms * 1.1)))
        _CALIBRATED = True
        info(f"Calibrated — threshold {_SPEECH_THRESHOLD}")
    except Exception as e:
        warn(f"Calibration failed: {e}"); _SPEECH_THRESHOLD = 150; _CALIBRATED = True

def _rms(chunk):
    return float(np.sqrt(np.mean(chunk.astype(np.float32)**2)))

def _record_speech(max_sec=12):
    if not SOUNDDEVICE_AVAILABLE: return None
    silence_needed = int(800 / CHUNK_MS)
    frames = []; streak = 0; count = 0
    try:
        s = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                           dtype=DTYPE, blocksize=CHUNK_SAMPLES)
        s.start()
        for _ in range(int(8000/CHUNK_MS)):
            c, _ = s.read(CHUNK_SAMPLES)
            if _rms(c) > _SPEECH_THRESHOLD: frames.append(c.copy()); count = 1; break
        if count:
            for _ in range(int(max_sec*1000/CHUNK_MS)):
                c, _ = s.read(CHUNK_SAMPLES); frames.append(c.copy())
                if _rms(c) > _SPEECH_THRESHOLD: streak = 0; count += 1
                else:
                    streak += 1
                    if streak >= silence_needed: break
        s.stop(); s.close()
        return np.concatenate(frames) if count >= 1 else None
    except Exception as e: err(f"Record error: {e}"); return None

def _google(audio_data):
    try:    return sr.Recognizer().recognize_google(audio_data)
    except sr.UnknownValueError: return None
    except sr.RequestError as e: err(f"Speech API: {e}"); return None

def _mic_ok(): return SOUNDDEVICE_AVAILABLE or PYAUDIO_AVAILABLE

def _is_wake(text):
    if not text: return False
    t = text.lower().strip()
    for p in WAKE_PHRASES:
        if p in t: return True
    return bool(re.search(r"\bmax\b", t))

def scan_once():
    if not SR_AVAILABLE or not SOUNDDEVICE_AVAILABLE: return "no_mic"
    s = None; frames = []; count = 0; streak = 0
    silence = int(800 / CHUNK_MS)
    try:
        s = sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                           dtype=DTYPE, blocksize=CHUNK_SAMPLES)
        s.start()
        for _ in range(int(6000/CHUNK_MS)):
            c, _ = s.read(CHUNK_SAMPLES)
            if _rms(c) > _SPEECH_THRESHOLD: frames.append(c.copy()); count = 1; break
        if count:
            for _ in range(int(4000/CHUNK_MS)):
                c, _ = s.read(CHUNK_SAMPLES); frames.append(c.copy())
                if _rms(c) > _SPEECH_THRESHOLD: streak = 0; count += 1
                else:
                    streak += 1
                    if streak >= silence: break
        s.stop(); s.close(); s = None
        if count < 1 or not frames: return "nothing"
        audio = sr.AudioData(np.concatenate(frames).tobytes(), SAMPLE_RATE, 2)
        text  = _google(audio)
        if text:
            _gui(_cwrite, f"  [wake] heard: '{text}'\n", "dim")
            return "woke" if _is_wake(text) else "nothing"
        return "nothing"
    except Exception as ex:
        if s:
            try: s.stop(); s.close()
            except: pass
        err(f"Wake error: {ex}"); return "nothing"

def capture_voice(duration=7):
    if not SR_AVAILABLE: return None
    if not _mic_ok():    return "NO_MIC"
    set_wake_led("listening")
    samples = _record_speech(max_sec=duration+4)
    if samples is None: set_wake_led("idle"); return None
    audio = sr.AudioData(samples.tobytes(), SAMPLE_RATE, 2)
    text  = _google(audio)
    set_wake_led("idle")
    if text:
        set_status("Command received", C["mint"])
        _gui(_cwrite, f"  Heard: {text}\n", "heard")
        return text.lower()
    speak(f"Sorry {USER_NAME}, I did not catch that. Please try again.")
    return None

def ask_text(prompt, title="Max"):
    res = [None]; ev = threading.Event()
    def _b():
        d = tk.Toplevel(ROOT); d.title(title); d.geometry("500x160")
        d.configure(bg=C["bg1"]); d.attributes("-topmost",True); d.grab_set()
        d.resizable(False,False); d.update_idletasks()
        d.geometry(f"500x160+{(d.winfo_screenwidth()-500)//2}+{(d.winfo_screenheight()-160)//2}")
        tk.Label(d,text=prompt,font=("Helvetica Neue",11,"bold"),fg=C["teal"],bg=C["bg1"]).pack(pady=(14,4),padx=18,anchor="w")
        v = tk.StringVar()
        e = tk.Entry(d,textvariable=v,width=52,font=FNT_MONO,bg=C["bg2"],fg=C["txt0"],
                     insertbackground=C["gold"],relief="flat",bd=6)
        e.pack(padx=18,fill="x"); e.focus()
        def ok():  res[0]=v.get().strip(); d.destroy(); ev.set()
        def no():  d.destroy(); ev.set()
        e.bind("<Return>", lambda _: ok())
        d.protocol("WM_DELETE_WINDOW", no)
        bf = tk.Frame(d,bg=C["bg1"]); bf.pack(pady=10)
        _mk_btn(bf,"OK",ok,C["teal"],C["bg0"],8).pack(side=tk.LEFT,padx=6)
        _mk_btn(bf,"Cancel",no,C["coral"],C["bg0"],8).pack(side=tk.LEFT,padx=6)
    ROOT.after(0,_b); ev.wait(60); return res[0]

# ── site & app maps ───────────────────────────────────────────────────────────
SITES = {
    "youtube":      ("YouTube",      "https://www.youtube.com"),
    "linkedin":     ("LinkedIn",     "https://www.linkedin.com"),
    "github":       ("GitHub",       "https://github.com"),
    "gmail":        ("Gmail",        "https://mail.google.com"),
    "email":        ("Gmail",        "https://mail.google.com"),
    "google":       ("Google",       "https://www.google.com"),
    "stackoverflow":("Stack Overflow","https://stackoverflow.com"),
    "twitter":      ("Twitter",      "https://twitter.com"),
    "reddit":       ("Reddit",       "https://www.reddit.com"),
    "amazon":       ("Amazon",       "https://www.amazon.in"),
    "netflix":      ("Netflix",      "https://www.netflix.com"),
    "maps":         ("Google Maps",  "https://maps.google.com"),
    "drive":        ("Google Drive", "https://drive.google.com"),
    "meet":         ("Google Meet",  "https://meet.google.com"),
    "docs":         ("Google Docs",  "https://docs.google.com"),
    "sheets":       ("Google Sheets","https://sheets.google.com"),
    "instagram":    ("Instagram",    "https://www.instagram.com"),
    "whatsapp":     ("WhatsApp",     "https://web.whatsapp.com"),
    "spotify":      ("Spotify",      "https://open.spotify.com"),
    "discord":      ("Discord",      "https://discord.com/app"),
    "notion":       ("Notion",       "https://www.notion.so"),
    "chatgpt":      ("ChatGPT",      "https://chat.openai.com"),
    "gemini":       ("Gemini",       "https://gemini.google.com"),
}

APP_MAP_WIN = {
    "notepad":"notepad","calculator":"calc","paint":"mspaint",
    "explorer":"explorer","task manager":"taskmgr","cmd":"start cmd",
    "powershell":"start powershell","word":"start winword",
    "excel":"start excel","powerpoint":"start powerpnt",
    "vs code":"code","vscode":"code","spotify":"start spotify",
    "edge":"start msedge","firefox":"start firefox",
}
APP_MAP_LINUX = {
    "terminal":"x-terminal-emulator","files":"nautilus","gedit":"gedit",
    "calculator":"gnome-calculator","vs code":"code","vscode":"code",
    "firefox":"firefox","chrome":"google-chrome","vlc":"vlc","gimp":"gimp",
}

PROC_MAP = {
    "notepad":"notepad.exe","calculator":"calculator.exe","paint":"mspaint.exe",
    "word":"winword.exe","excel":"excel.exe","powerpoint":"powerpnt.exe",
    "vs code":"code.exe","vscode":"code.exe","spotify":"spotify.exe",
    "edge":"msedge.exe","firefox":"firefox.exe","chrome":"chrome.exe",
    "vlc":"vlc","gimp":"gimp","powershell":"powershell.exe",
    "cmd":"cmd.exe","explorer":"explorer.exe",
}

# ── tab close helper ──────────────────────────────────────────────────────────
def _close_tab_by_title(site_name):
    if not PYGETWINDOW_AVAILABLE:
        speak(f"{USER_NAME}, pygetwindow not installed. Run pip install pygetwindow.")
        return False
    import ctypes
    all_titles = gw.getAllTitles()
    target_win = None
    for title in all_titles:
        if site_name.lower() in title.lower():
            wins = gw.getWindowsWithTitle(title)
            if wins: target_win = wins[0]; break
    if target_win is None:
        for title in all_titles:
            t = title.lower()
            if any(b in t for b in ["chrome","firefox","edge","brave","opera"]):
                wins = gw.getWindowsWithTitle(title)
                if wins: target_win = wins[0]; break
    if target_win is None:
        speak(f"{USER_NAME}, I could not find {site_name} open in any browser.")
        return False
    try:
        hwnd = target_win._hWnd
        ctypes.windll.user32.ShowWindow(hwnd, 9)
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        time.sleep(0.8)
        pyautogui.hotkey("ctrl", "F4")
        time.sleep(0.4)
        return True
    except Exception as e:
        err(f"Tab close error: {e}"); return False

# ── features ──────────────────────────────────────────────────────────────────

def feat_time():
    speak(f"{USER_NAME}, the time is {datetime.datetime.now().strftime('%I:%M %p')}.")

def feat_date():
    speak(f"{USER_NAME}, today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}.")

def feat_datetime():
    n = datetime.datetime.now()
    speak(f"{USER_NAME}, it is {n.strftime('%A, %B %d')} and the time is {n.strftime('%I:%M %p')}.")

def feat_open_site(site_key):
    if site_key in SITES:
        name, url = SITES[site_key]
        speak(f"Opening {name} for you, {USER_NAME}.")
        webbrowser.open(url)
    else:
        speak(f"{USER_NAME}, I could not find that website.")

def feat_close_site(site_key=""):
    if not PYAUTOGUI_AVAILABLE:
        speak(f"{USER_NAME}, pyautogui is not installed. Run pip install pyautogui.")
        return
    name = SITES.get(site_key, (site_key.title(), ""))[0] if site_key else "that tab"
    if _close_tab_by_title(name):
        speak(f"{USER_NAME}, {name} tab has been closed.")

def feat_google_search(query):
    if query:
        speak(f"Searching Google for {query}, {USER_NAME}.")
        webbrowser.open(f"https://www.google.com/search?q={query.replace(' ','+')}")
    else:
        speak(f"{USER_NAME}, no search query given.")

def feat_youtube_search(query):
    if query:
        speak(f"Searching YouTube for {query}, {USER_NAME}.")
        webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ','+')}")
    else:
        speak(f"{USER_NAME}, no YouTube query given.")

def feat_open_chrome():
    speak(f"Opening Chrome, {USER_NAME}.")
    if IS_WINDOWS:
        for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]:
            if os.path.exists(p): subprocess.Popen([p]); return
        os.system("start chrome")
    elif IS_MAC:   subprocess.Popen(["open","-a","Google Chrome"])
    elif IS_LINUX: subprocess.Popen(["google-chrome"])

def feat_close_chrome():
    speak(f"{USER_NAME}, closing Chrome now.")
    if IS_WINDOWS:   os.system("taskkill /f /im chrome.exe")
    elif IS_LINUX:   os.system("pkill chrome")
    elif IS_MAC:     os.system("osascript -e 'quit app \"Google Chrome\"'")

def feat_open_app(app_key):
    amap = APP_MAP_WIN if IS_WINDOWS else APP_MAP_LINUX
    if app_key in amap:
        speak(f"Opening {app_key}, {USER_NAME}.")
        try:
            if IS_WINDOWS: os.system(amap[app_key])
            else: subprocess.Popen(amap[app_key].split())
        except Exception as e: speak(f"{USER_NAME}, could not open {app_key}. {e}")
    else:
        speak(f"{USER_NAME}, I could not find that app.")

def feat_close_app(app_key):
    if app_key in PROC_MAP:
        speak(f"Closing {app_key}, {USER_NAME}.")
        if IS_WINDOWS: os.system(f"taskkill /f /im {PROC_MAP[app_key]}")
        else:          os.system(f"pkill -f {PROC_MAP[app_key]}")
    else:
        speak(f"{USER_NAME}, I could not find that application to close.")

def feat_calculate(expr_raw):
    expr = (expr_raw.replace("plus","+").replace("minus","-").replace("times","*")
                    .replace("multiplied by","*").replace("divided by","/")
                    .replace("mod","%").replace("power","**").replace("^","**")
                    .replace("square root of","math.sqrt("))
    if "math.sqrt(" in expr and not expr.endswith(")"): expr += ")"
    if not expr.strip(): speak(f"{USER_NAME}, please give me an expression."); return
    if re.search(r"[a-zA-Z]",expr.replace("math","").replace("sqrt","")):
        speak(f"{USER_NAME}, I can only calculate numeric expressions."); return
    try:
        r = eval(expr,{"__builtins__":{},"math":math})
        if isinstance(r,float) and r==int(r): r=int(r)
        speak(f"{USER_NAME}, the answer is {r}.")
    except ZeroDivisionError: speak(f"{USER_NAME}, I cannot divide by zero.")
    except Exception:         speak(f"{USER_NAME}, I could not evaluate that.")

def feat_screenshot():
    if not PYAUTOGUI_AVAILABLE: speak(f"{USER_NAME}, pyautogui is not installed."); return
    fname = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    try:
        pyautogui.screenshot().save(fname)
        speak(f"{USER_NAME}, screenshot saved as {fname}.")
    except Exception as e: speak(f"{USER_NAME}, screenshot failed. {e}")

def feat_system_info():
    if not PSUTIL_AVAILABLE: speak(f"{USER_NAME}, psutil is not installed."); return
    cpu = psutil.cpu_percent(interval=1); mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/"); cores = psutil.cpu_count(logical=True)
    speak(f"{USER_NAME}, CPU {cpu}% on {cores} cores, RAM {mem.percent}% used, disk {disk.percent}% full.")

def feat_battery():
    if not PSUTIL_AVAILABLE: speak(f"{USER_NAME}, psutil is not installed."); return
    b = psutil.sensors_battery()
    if b:
        st = "charging" if b.power_plugged else "discharging"
        mins = int(b.secsleft/60) if b.secsleft not in (psutil.POWER_TIME_UNLIMITED,-1) else -1
        msg = f"{USER_NAME}, battery is {b.percent:.0f}% and {st}."
        if mins > 0: msg += f" About {mins} minutes left."
        speak(msg)
    else: speak(f"{USER_NAME}, no battery found — desktop system.")

def feat_cpu():
    if not PSUTIL_AVAILABLE: speak(f"{USER_NAME}, psutil not installed."); return
    speak(f"{USER_NAME}, CPU is at {psutil.cpu_percent(interval=0.5)}%, {psutil.cpu_freq().current:.0f} MHz.")

def feat_ram():
    if not PSUTIL_AVAILABLE: speak(f"{USER_NAME}, psutil not installed."); return
    m = psutil.virtual_memory()
    speak(f"{USER_NAME}, RAM {m.percent}% used — {m.used//1024**2} MB of {m.total//1024**2} MB.")

def feat_disk():
    if not PSUTIL_AVAILABLE: speak(f"{USER_NAME}, psutil not installed."); return
    d = psutil.disk_usage("/")
    speak(f"{USER_NAME}, disk {d.percent}% full — {d.used//1024**3:.1f} GB of {d.total//1024**3:.1f} GB.")

def feat_processes():
    if not PSUTIL_AVAILABLE: speak(f"{USER_NAME}, psutil not installed."); return
    procs = sorted(psutil.process_iter(["pid","name","cpu_percent"]),
                   key=lambda p: p.info["cpu_percent"] or 0, reverse=True)[:5]
    speak(f"{USER_NAME}, top 5 CPU processes shown in console.")
    for p in procs: info(f"  {p.info['pid']:5d}  {p.info['cpu_percent']:5.1f}%  {p.info['name']}")

def feat_network():
    try:
        host = socket.gethostname(); ip = socket.gethostbyname(host)
        speak(f"{USER_NAME}, hostname {host}, local IP {ip}.")
    except Exception as e: speak(f"{USER_NAME}, network error: {e}")

def feat_public_ip():
    if not REQUESTS_AVAILABLE: speak(f"{USER_NAME}, requests not installed."); return
    try:
        ip = requests.get("https://api.ipify.org?format=json",timeout=6).json()["ip"]
        speak(f"{USER_NAME}, your public IP is {ip}.")
    except: speak(f"{USER_NAME}, could not fetch public IP.")

def feat_ping():
    if not REQUESTS_AVAILABLE: speak(f"{USER_NAME}, requests not installed."); return
    speak(f"{USER_NAME}, testing your connection.")
    try:
        t0 = time.perf_counter(); requests.get("https://www.google.com",timeout=5)
        ms = int((time.perf_counter()-t0)*1000)
        q = "excellent" if ms<50 else "good" if ms<100 else "slow"
        speak(f"{USER_NAME}, ping is {ms} ms — connection is {q}.")
    except: speak(f"{USER_NAME}, ping failed. Check your internet.")

def feat_lock():
    speak(f"Locking screen, {USER_NAME}.")
    time.sleep(1)
    if IS_WINDOWS:   os.system("rundll32.exe user32.dll,LockWorkStation")
    elif IS_LINUX:
        for c in ["gnome-screensaver-command -l","xdg-screensaver lock","loginctl lock-session"]:
            if os.system(f"{c} 2>/dev/null")==0: break
    elif IS_MAC: os.system(r'/System/Library/CoreServices/Menu\ Extras/User.menu/Contents/Resources/CGSession -suspend')

def feat_sleep():
    speak(f"Putting computer to sleep. Goodbye {USER_NAME}.")
    time.sleep(2)
    if IS_WINDOWS:   os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    elif IS_LINUX:   os.system("systemctl suspend")
    elif IS_MAC:     os.system("pmset sleepnow")

def feat_shutdown():
    def _c():
        if msgbox.askyesno("Shutdown","Shut down now?",parent=ROOT):
            speak(f"Shutting down in 5 seconds. Goodbye {USER_NAME}!")
            def _d(): time.sleep(5); os.system("shutdown /s /t 1" if IS_WINDOWS else "shutdown -h now")
            threading.Thread(target=_d,daemon=True).start()
        else: speak(f"Shutdown cancelled, {USER_NAME}.")
    ROOT.after(0,_c)

def feat_restart():
    def _c():
        if msgbox.askyesno("Restart","Restart now?",parent=ROOT):
            speak(f"Restarting in 5 seconds, {USER_NAME}.")
            def _d(): time.sleep(5); os.system("shutdown /r /t 1" if IS_WINDOWS else "reboot")
            threading.Thread(target=_d,daemon=True).start()
        else: speak(f"Restart cancelled, {USER_NAME}.")
    ROOT.after(0,_c)

def feat_logout():
    speak(f"Logging out. See you, {USER_NAME}.")
    time.sleep(1)
    if IS_WINDOWS:   os.system("shutdown /l")
    elif IS_LINUX:   os.system("pkill -KILL -u $USER")
    elif IS_MAC:     os.system("osascript -e 'tell app \"System Events\" to log out'")

def feat_wikipedia(query):
    if not WIKI_AVAILABLE: speak(f"{USER_NAME}, wikipedia not installed."); return
    if not query: query = ask_text("Search Wikipedia for?")
    if not query: return
    speak(f"{USER_NAME}, searching Wikipedia for {query}.")
    try:
        wikipedia.set_lang("en")
        speak(wikipedia.summary(query, sentences=3, auto_suggest=False))
    except wikipedia.exceptions.DisambiguationError as e:
        speak(f"{USER_NAME}, multiple results. Did you mean {', '.join(e.options[:3])}?")
    except Exception:
        try:    speak(wikipedia.summary(query, sentences=3, auto_suggest=True))
        except: speak(f"{USER_NAME}, could not find {query} on Wikipedia.")

def feat_define(word):
    if not word: word = ask_text("Which word to define?")
    if not word: return
    if not REQUESTS_AVAILABLE: speak(f"{USER_NAME}, requests not installed."); return
    speak(f"{USER_NAME}, looking up {word}.")
    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",timeout=6)
        if r.status_code == 200:
            d = r.json()[0]["meanings"][0]["definitions"][0]["definition"]
            speak(f"{USER_NAME}, {word} means: {d}")
        else: speak(f"{USER_NAME}, no definition found for {word}.")
    except: speak(f"{USER_NAME}, dictionary unavailable.")

# ── FIXED: API keys now loaded from .env file — no hardcoded secrets ──────────
def feat_weather(city="Warangal"):
    key = os.environ.get("OPENWEATHER_API_KEY")   # reads from .env via load_dotenv()
    if not key:
        speak(f"{USER_NAME}, weather API key missing. Add OPENWEATHER_API_KEY to your .env file.")
        return
    if not REQUESTS_AVAILABLE: speak(f"{USER_NAME}, requests not installed."); return
    speak(f"{USER_NAME}, checking weather in {city}.")
    try:
        d = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric",
            timeout=6
        ).json()
        if d.get("cod") != 404:
            speak(f"{USER_NAME}, {city}: {d['main']['temp']:.1f} degrees, {d['weather'][0]['description']}, humidity {d['main']['humidity']}%.")
        else:
            speak(f"{USER_NAME}, city {city} not found.")
    except:
        speak(f"{USER_NAME}, weather unavailable.")

def feat_news():
    key = os.environ.get("NEWS_API_KEY")           # reads from .env via load_dotenv()
    if not key:
        speak(f"{USER_NAME}, news API key missing. Add NEWS_API_KEY to your .env file.")
        return
    if not REQUESTS_AVAILABLE: speak(f"{USER_NAME}, requests not installed."); return
    speak(f"{USER_NAME}, fetching headlines.")
    try:
        d = requests.get(
            f"https://newsapi.org/v2/top-headlines?language=en&apiKey={key}",
            timeout=6
        ).json()
        if d.get("status") == "ok":
            articles = d.get("articles", [])
            if articles:
                for i, a in enumerate(articles[:3], 1):
                    speak(f"Headline {i}: {a.get('title', '')}")
            else:
                speak(f"{USER_NAME}, no headlines found.")
        else:
            speak(f"{USER_NAME}, could not fetch news. {d.get('message', '')}")
    except Exception:
        speak(f"{USER_NAME}, news unavailable.")
# ─────────────────────────────────────────────────────────────────────────────

def feat_joke():
    if JOKES_AVAILABLE:
        try: speak(pyjokes.get_joke()); return
        except: pass
    speak(random.choice([
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "How many programmers to change a bulb? None, that is a hardware problem.",
        "A SQL query walks into a bar. Can I join you?",
        "Why did the developer go broke? He used up all his cache.",
    ]))

def feat_quote():
    if REQUESTS_AVAILABLE:
        try:
            r = requests.get("https://zenquotes.io/api/random",timeout=6)
            if r.status_code==200:
                d = r.json()[0]; speak(f"{d['q']} — {d['a']}"); return
        except: pass
    speak(random.choice([
        "The only way to do great work is to love what you do. Steve Jobs.",
        "In the middle of difficulty lies opportunity. Einstein.",
        "It does not matter how slowly you go as long as you do not stop. Confucius.",
    ]))

def feat_timer(amount, unit):
    secs = amount*3600 if "hour" in unit else amount*60 if "minute" in unit else amount
    speak(f"{USER_NAME}, timer set for {amount} {unit}.")
    def _r(): time.sleep(secs); speak(f"{USER_NAME}, your {amount} {unit} timer is done!")
    threading.Thread(target=_r,daemon=True).start()

def feat_alarm(hour, minute, label=""):
    t = datetime.datetime.now().replace(hour=hour,minute=minute,second=0,microsecond=0)
    if t <= datetime.datetime.now(): t += datetime.timedelta(days=1)
    speak(f"{USER_NAME}, alarm set for {t.strftime('%I:%M %p')}.")
    def _r():
        time.sleep((t-datetime.datetime.now()).total_seconds())
        speak(f"{USER_NAME}, wake up! It is {t.strftime('%I:%M %p')}!")
    threading.Thread(target=_r,daemon=True).start()

def feat_note():
    speak(f"{USER_NAME}, opening quick note.")
    def _b():
        d = tk.Toplevel(ROOT); d.title("Quick Note"); d.geometry("520x320")
        d.configure(bg=C["bg1"]); d.attributes("-topmost",True); d.grab_set()
        d.resizable(False,False); d.update_idletasks()
        d.geometry(f"520x320+{(d.winfo_screenwidth()-520)//2}+{(d.winfo_screenheight()-320)//2}")
        tk.Label(d,text="Quick Note",font=("Helvetica Neue",13,"bold"),fg=C["gold"],bg=C["bg1"]).pack(pady=(12,4),anchor="w",padx=16)
        txt = tk.Text(d,height=9,font=FNT_MONO,bg=C["bg2"],fg=C["txt0"],
                      insertbackground=C["gold"],relief="flat",bd=4)
        txt.pack(padx=16,fill="both",expand=True); txt.focus()
        def save():
            content = txt.get("1.0",tk.END).strip()
            if content:
                fn = f"note_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                open(fn,"w",encoding="utf-8").write(content)
                speak(f"{USER_NAME}, note saved as {fn}.")
            d.destroy()
        def close_note(): speak(f"{USER_NAME}, note closed."); d.destroy()
        bf = tk.Frame(d,bg=C["bg1"]); bf.pack(pady=8)
        _mk_btn(bf,"Save",save,C["gold"],C["bg0"],10).pack(side=tk.LEFT,padx=6)
        _mk_btn(bf,"Close",close_note,C["coral"],C["bg0"],10).pack(side=tk.LEFT,padx=6)
    ROOT.after(0,_b)

def feat_clipboard():
    try:
        c = ROOT.clipboard_get()
        speak(f"{USER_NAME}, clipboard: {c[:80]}") if c else speak(f"{USER_NAME}, clipboard is empty.")
    except: speak(f"{USER_NAME}, clipboard is empty.")

def feat_clear_clipboard():
    try: ROOT.clipboard_clear(); speak(f"{USER_NAME}, clipboard cleared.")
    except: speak(f"{USER_NAME}, could not clear clipboard.")

def feat_coin():
    speak(f"{USER_NAME}, it is {random.choice(['Heads','Tails'])}!")

def feat_dice(sides=6):
    speak(f"{USER_NAME}, I rolled a {sides}-sided die and got {random.randint(1,sides)}!")

def feat_translate(text=""):
    speak(f"{USER_NAME}, opening Google Translate.")
    webbrowser.open(f"https://translate.google.com/?text={text}" if text else "https://translate.google.com")

def feat_list_files():
    items = os.listdir(".")
    files = [f for f in items if os.path.isfile(f)]
    dirs  = [f for f in items if os.path.isdir(f)]
    speak(f"{USER_NAME}, {len(files)} files and {len(dirs)} folders in current directory.")
    if files: info("Files: "+", ".join(files[:10]))
    if dirs:  info("Folders: "+", ".join(dirs[:6]))

def feat_volume(action="status"):
    if not IS_WINDOWS: speak(f"{USER_NAME}, volume control is Windows only."); return
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        dev = AudioUtilities.GetSpeakers()
        vc  = cast(dev.Activate(IAudioEndpointVolume._iid_,CLSCTX_ALL,None),POINTER(IAudioEndpointVolume))
        if action == "up":
            v=min(1.0,vc.GetMasterVolumeLevelScalar()+0.1); vc.SetMasterVolumeLevelScalar(v,None)
            speak(f"{USER_NAME}, volume is now {int(v*100)}%.")
        elif action == "down":
            v=max(0.0,vc.GetMasterVolumeLevelScalar()-0.1); vc.SetMasterVolumeLevelScalar(v,None)
            speak(f"{USER_NAME}, volume is now {int(v*100)}%.")
        elif action == "mute":   vc.SetMute(1,None); speak(f"{USER_NAME}, muted.")
        elif action == "unmute": vc.SetMute(0,None); speak(f"{USER_NAME}, unmuted.")
        else:
            v = vc.GetMasterVolumeLevelScalar()
            speak(f"{USER_NAME}, volume is {int(v*100)}%.")
    except ImportError: speak(f"{USER_NAME}, run: pip install pycaw")
    except Exception as e: speak(f"{USER_NAME}, volume error: {e}")

def feat_help():
    _gui(_cwrite, f"""
MAX v{VERSION} — {USER_NAME}'s Assistant
══════════════════════════════════════════════════
WAKE        : say "hey max" → "Yes {USER_NAME}?"
TIME/DATE   : what time / what date
OPEN        : open youtube / open gmail / open chrome
CLOSE       : close youtube / close gmail / close chrome
SEARCH      : search python tutorials
YOUTUBE     : youtube lo-fi music
WIKIPEDIA   : wikipedia black holes
DICTIONARY  : define algorithm
CALCULATE   : calculate 25 times 4
SCREENSHOT  : take a screenshot
SYSTEM      : system info / cpu / ram / disk / battery
NETWORK     : network info / my ip / ping
LOCK/SLEEP  : lock screen / sleep
SHUTDOWN    : shutdown / restart / logout
VOLUME      : volume up / down / mute / unmute
TIMER       : set timer 5 minutes
ALARM       : set alarm 7 30 am
NOTE        : create note
CLIPBOARD   : clipboard / clear clipboard
WEATHER     : weather (needs OPENWEATHER_API_KEY in .env)
NEWS        : news (needs NEWS_API_KEY in .env)
JOKE        : tell me a joke
QUOTE       : inspire me
COIN/DICE   : flip a coin / roll a dice
TRANSLATE   : translate hello world
FILES       : list files
EXIT        : goodbye
══════════════════════════════════════════════════
""","info")
    speak(f"{USER_NAME}, all commands are shown in the console.")

def feat_greet():
    h = datetime.datetime.now().hour
    g = "Good morning" if h<12 else "Good afternoon" if h<18 else "Good evening"
    speak(f"{g} {USER_NAME}! I am Max version {VERSION}. Say hey max to wake me up.")

# ── dispatch ──────────────────────────────────────────────────────────────────
def dispatch(cmd):
    c = _fuzzy_correct(cmd.lower().strip())
    set_status("Processing…", C["violet"])
    T = threading.Thread

    close_match = re.match(r"(close|stop|shut|kill|exit)\s+(.+)", c)
    if close_match:
        target = close_match.group(2).strip()
        for key in SITES:
            if key in target:
                T(target=feat_close_site, args=(key,), daemon=True).start(); return
        if "chrome" in target:
            T(target=feat_close_chrome, daemon=True).start(); return
        for key in PROC_MAP:
            if key in target:
                T(target=feat_close_app, args=(key,), daemon=True).start(); return
        speak(f"{USER_NAME}, I could not find what to close."); return

    if re.search(r"clear\s+clipboard", c):
        T(target=feat_clear_clipboard, daemon=True).start(); return

    if re.search(r"date\s+and\s+time|time\s+and\s+date", c):
        T(target=feat_datetime, daemon=True).start(); return
    if re.search(r"what\s+time|current\s+time|tell.*time|time\b", c) and "timer" not in c:
        T(target=feat_time, daemon=True).start(); return
    if re.search(r"what.*date|today.*date|current\s+date|what\s+date", c):
        T(target=feat_date, daemon=True).start(); return

    if re.search(r"\b(open|launch|start|go\s+to|load|show)\b", c):
        if "chrome" in c:
            T(target=feat_open_chrome, daemon=True).start(); return
        for key in SITES:
            if key in c:
                T(target=feat_open_site, args=(key,), daemon=True).start(); return
        amap = APP_MAP_WIN if IS_WINDOWS else APP_MAP_LINUX
        for key in amap:
            if key in c:
                T(target=feat_open_app, args=(key,), daemon=True).start(); return
        speak(f"{USER_NAME}, I could not find what to open."); return

    if re.search(r"\byoutube\b", c):
        query = re.sub(r"\b(youtube|play|search|find|watch)\b","",c,flags=re.I).strip()
        if query: T(target=feat_youtube_search, args=(query,), daemon=True).start()
        else:     T(target=feat_open_site, args=("youtube",), daemon=True).start()
        return

    if re.search(r"\b(search|google|look\s+up|find)\b", c):
        query = re.sub(r"\b(search|google|look\s+up|find)\b","",c,flags=re.I).strip()
        if query: T(target=feat_google_search, args=(query,), daemon=True).start()
        else:
            q = ask_text("What to search?")
            if q: T(target=feat_google_search, args=(q,), daemon=True).start()
        return

    if re.search(r"\b(calculate|compute|evaluate|solve|math)\b", c):
        expr = re.sub(r"\b(calculate|compute|evaluate|solve|math)\b","",c,flags=re.I).strip()
        T(target=feat_calculate, args=(expr,), daemon=True).start(); return

    if re.search(r"\bscreenshot\b", c):
        T(target=feat_screenshot, daemon=True).start(); return

    if re.search(r"\bsystem\s+info\b", c):
        T(target=feat_system_info, daemon=True).start(); return
    if re.search(r"\bbattery\b", c):
        T(target=feat_battery, daemon=True).start(); return
    if re.search(r"\bcpu\b", c):
        T(target=feat_cpu, daemon=True).start(); return
    if re.search(r"\b(ram|memory)\b", c):
        T(target=feat_ram, daemon=True).start(); return
    if re.search(r"\b(disk|storage|hard drive)\b", c):
        T(target=feat_disk, daemon=True).start(); return
    if re.search(r"\bprocess", c):
        T(target=feat_processes, daemon=True).start(); return

    if re.search(r"\bnetwork\s+info\b", c):
        T(target=feat_network, daemon=True).start(); return
    if re.search(r"\b(public\s+ip|my\s+ip|ip\s+address)\b", c):
        T(target=feat_public_ip, daemon=True).start(); return
    if re.search(r"\bping\b", c):
        T(target=feat_ping, daemon=True).start(); return

    if re.search(r"\block\s+screen\b", c):
        T(target=feat_lock, daemon=True).start(); return
    if re.search(r"\b(sleep|hibernate|suspend)\b", c):
        T(target=feat_sleep, daemon=True).start(); return
    if re.search(r"\b(shutdown|shut\s+down|turn\s+off|power\s+off)\b", c):
        feat_shutdown(); return
    if re.search(r"\b(restart|reboot)\b", c):
        feat_restart(); return
    if re.search(r"\b(log\s*out|sign\s*out)\b", c):
        T(target=feat_logout, daemon=True).start(); return

    if re.search(r"\b(wikipedia|wiki)\b", c):
        query = re.sub(r"\b(wikipedia|wiki|tell\s+me\s+about|who\s+is|what\s+is)\b","",c,flags=re.I).strip()
        T(target=feat_wikipedia, args=(query,), daemon=True).start(); return
    if re.search(r"\b(define|definition|meaning|dictionary)\b", c):
        word = re.sub(r"\b(define|definition|meaning|dictionary)\b","",c,flags=re.I).strip()
        T(target=feat_define, args=(word,), daemon=True).start(); return
    if re.search(r"\b(weather|temperature|forecast)\b", c):
        m = re.search(r"\bin\s+([A-Za-z ]+)$", c)
        city = m.group(1).strip() if m else "Warangal"
        T(target=feat_weather, args=(city,), daemon=True).start(); return
    if re.search(r"\b(news|headlines)\b", c):
        T(target=feat_news, daemon=True).start(); return

    if re.search(r"\bvolume\b", c):
        if re.search(r"\b(up|louder|increase)\b",c):      T(target=feat_volume,args=("up",),daemon=True).start()
        elif re.search(r"\b(down|quieter|decrease)\b",c): T(target=feat_volume,args=("down",),daemon=True).start()
        elif re.search(r"\bmute\b",c):                    T(target=feat_volume,args=("mute",),daemon=True).start()
        elif re.search(r"\bunmute\b",c):                  T(target=feat_volume,args=("unmute",),daemon=True).start()
        else:                                              T(target=feat_volume,args=("status",),daemon=True).start()
        return

    if re.search(r"\b(set\s+timer|timer\s+for|countdown|start\s+timer)\b", c):
        m = re.search(r"(\d+)\s*(hour|hours|minute|minutes|second|seconds)",c)
        if m: T(target=feat_timer,args=(int(m.group(1)),m.group(2)),daemon=True).start()
        else:
            v = ask_text("Timer duration (e.g. 5 minutes):")
            if v:
                m2 = re.search(r"(\d+)\s*(hour|hours|minute|minutes|second|seconds)",v)
                if m2: T(target=feat_timer,args=(int(m2.group(1)),m2.group(2)),daemon=True).start()
        return

    if re.search(r"\b(set\s+alarm|alarm\s+for|wake\s+me)\b", c):
        m = re.search(r"(\d{1,2})[:\s]?(\d{2})?\s*(am|pm)?",c,re.I)
        if m:
            h=int(m.group(1)); mn=int(m.group(2) or 0); mer=(m.group(3) or "").lower()
            if mer=="pm" and h!=12: h+=12
            elif mer=="am" and h==12: h=0
            T(target=feat_alarm,args=(h,mn),daemon=True).start()
        else:
            v = ask_text("Alarm time (e.g. 7 30 am):")
            if v:
                m2 = re.search(r"(\d{1,2})[:\s]?(\d{2})?\s*(am|pm)?",v,re.I)
                if m2:
                    h=int(m2.group(1)); mn=int(m2.group(2) or 0); mer=(m2.group(3) or "").lower()
                    if mer=="pm" and h!=12: h+=12
                    elif mer=="am" and h==12: h=0
                    T(target=feat_alarm,args=(h,mn),daemon=True).start()
        return

    if re.search(r"\b(create\s+note|new\s+note|take\s+note|open\s+note|quick\s+note|note\s+down)\b", c):
        ROOT.after(0, feat_note); return

    if re.search(r"\bclipboard\b", c):
        T(target=feat_clipboard, daemon=True).start(); return

    if re.search(r"\bjoke\b", c):
        T(target=feat_joke, daemon=True).start(); return
    if re.search(r"\b(quote|inspire|motivate|motivation|inspiration)\b", c):
        T(target=feat_quote, daemon=True).start(); return
    if re.search(r"\b(flip\s+coin|toss\s+coin|heads\s+or\s+tails|coin\s+toss)\b", c):
        T(target=feat_coin, daemon=True).start(); return
    if re.search(r"\b(roll\s+dice|roll\s+die|roll\s+the\s+dice)\b", c):
        m = re.search(r"(\d+)",c); sides = int(m.group(1)) if m else 6
        T(target=feat_dice, args=(sides,), daemon=True).start(); return
    if re.search(r"\btranslate\b", c):
        text = re.sub(r"\btranslate\b","",c,flags=re.I).strip()
        T(target=feat_translate, args=(text,), daemon=True).start(); return
    if re.search(r"\blist\s+files\b", c):
        T(target=feat_list_files, daemon=True).start(); return

    if re.search(r"\b(hello|hi\s+max|hey\s+there|hi\s+there)\b", c):
        T(target=lambda:speak(f"Hello {USER_NAME}! How can I help you?"),daemon=True).start(); return
    if re.search(r"\bhow\s+are\s+you\b", c):
        T(target=lambda:speak(f"I am running perfectly, {USER_NAME}! Ready to help."),daemon=True).start(); return
    if re.search(r"\b(who\s+are\s+you|your\s+name|what\s+are\s+you|tell\s+me\s+about\s+yourself)\b", c):
        T(target=lambda:speak(f"I am Max, your personal assistant, {USER_NAME}. Version {VERSION}."),daemon=True).start(); return
    if re.search(r"\b(thank\s+you|thanks|many\s+thanks)\b", c):
        T(target=lambda:speak(f"You are welcome, {USER_NAME}!"),daemon=True).start(); return
    if re.search(r"\b(help|halp|helf|hep|kelp|hepl|hulp|hilp|holp|hlp|hlep|commands|guide|manual|features|capabilities|instructions)\b", c):
        T(target=feat_help, daemon=True).start(); return
    if re.search(r"\b(bye|goodbye|see\s+you|exit\s+max|stop\s+max|close\s+max)\b", c):
        def _bye():
            speak(f"Goodbye {USER_NAME}! Have a great day!")
            time.sleep(3); ROOT.after(0, ROOT.quit)
        T(target=_bye, daemon=True).start(); return

    T(target=lambda:speak(f"{USER_NAME}, I heard '{cmd}' but did not understand. Say help to see all commands."),daemon=True).start()
    set_status(f"Say '{WAKE_WORD}'…", C["txt2"])

# ── main loop ─────────────────────────────────────────────────────────────────
_running  = False
_loop_thr = None

def start_pa():
    global _running, _loop_thr
    if _running: return
    _running = True
    _gui(lambda: start_btn.config(state=tk.DISABLED, bg=C["txt2"]))
    _gui(lambda: stop_btn.config(state=tk.NORMAL,    bg=C["coral"]))
    _loop_thr = threading.Thread(target=_main_loop, daemon=True)
    _loop_thr.start()

def stop_pa():
    global _running
    _running = False
    start_btn.config(state=tk.NORMAL,  bg=C["mint"])
    stop_btn.config(state=tk.DISABLED, bg=C["txt2"])
    set_wake_led("idle")
    set_status("Stopped", C["gold"])
    speak(f"Max stopped, {USER_NAME}. Click Start to resume.")

def _main_loop():
    global _running
    feat_greet()
    if not _mic_ok():
        speak(f"{USER_NAME}, no microphone found. Install sounddevice.")
        _gui(lambda: start_btn.config(state=tk.NORMAL,  bg=C["mint"]))
        _gui(lambda: stop_btn.config(state=tk.DISABLED, bg=C["txt2"]))
        _running = False; return
    if not SR_AVAILABLE:
        speak(f"{USER_NAME}, SpeechRecognition missing. Run pip install SpeechRecognition.")
        _gui(lambda: start_btn.config(state=tk.NORMAL,  bg=C["mint"]))
        _gui(lambda: stop_btn.config(state=tk.DISABLED, bg=C["txt2"]))
        _running = False; return
    if SOUNDDEVICE_AVAILABLE: _calibrate()
    info(f'Say "{WAKE_WORD}" — corrections shown in dim text')
    while _running:
        set_status(f"Waiting for '{WAKE_WORD}'…", C["txt2"])
        set_wake_led("scanning")
        _gui(_cwrite, f'\n  Listening for "{WAKE_WORD}"…\n', "dim")
        woke = False
        while _running:
            r = scan_once()
            if r == "no_mic":
                speak(f"{USER_NAME}, microphone disconnected.")
                _running = False
                _gui(lambda: start_btn.config(state=tk.NORMAL,  bg=C["mint"]))
                _gui(lambda: stop_btn.config(state=tk.DISABLED, bg=C["txt2"]))
                break
            if r == "woke":
                set_wake_led("heard")
                _gui(_cwrite, "  Wake word detected!\n", "ok")
                speak(f"Yes {USER_NAME}?")
                woke = True; break
        if not _running: break
        if not woke: continue
        _tts_q.join()
        set_status("Listening for command…", C["coral"])
        set_wake_led("listening")
        _gui(_cwrite, "  Listening for command…\n", "dim")
        command = capture_voice(duration=7)
        if not _running: break
        if command and command != "NO_MIC":
            user_echo(command)
            speak_and_wait(f"{USER_NAME}, you said: {command}")
            dispatch(command)
        elif command == "NO_MIC":
            speak(f"{USER_NAME}, microphone unavailable.")
    set_wake_led("idle")
    set_status("Max stopped.", C["gold"])

# ── GUI ───────────────────────────────────────────────────────────────────────
def _mk_btn(p,t,c,bg,fg=None,w=20):
    return tk.Button(p,text=t,command=c,bg=bg,fg=fg or C["bg0"],font=FNT_BTN,
                     relief="flat",width=w,height=1,cursor="hand2",
                     activebackground=C["bg4"],activeforeground=C["txt0"],bd=0,padx=4)

def _sec(p,t):
    f=tk.Frame(p,bg=C["bg1"]); f.pack(fill="x",padx=10,pady=(10,2))
    tk.Label(f,text=f"  {t}",font=("Helvetica Neue",7,"bold"),
             fg=C["txt2"],bg=C["bg1"],anchor="w").pack(fill="x")
    tk.Frame(f,bg=C["border"],height=1).pack(fill="x",pady=(2,0))

def _sbtn(p,t,c,col=None):
    b=tk.Button(p,text=t,command=c,bg=col or C["bg3"],fg=C["txt1"],
                font=("Helvetica Neue",8,"bold"),relief="flat",anchor="w",
                cursor="hand2",width=24,padx=10,pady=3,
                activebackground=C["bg4"],activeforeground=C["txt0"])
    b.pack(fill="x",padx=10,pady=1); return b

def qr(fn,*a): threading.Thread(target=fn,args=a,daemon=True).start()

def _oneshot():
    def _r():
        if not _mic_ok(): speak(f"{USER_NAME}, no mic found."); return
        set_status("Listening…",C["coral"])
        r = capture_voice()
        if r and r!="NO_MIC": user_echo(r); dispatch(r)
        elif r=="NO_MIC": speak(f"{USER_NAME}, no microphone.")
    threading.Thread(target=_r,daemon=True).start()

def _textcmd():
    def _r():
        c = ask_text(f"Enter command, {USER_NAME}:")
        if c: user_echo(c); dispatch(c.lower())
    threading.Thread(target=_r,daemon=True).start()

def _calc_prompt():
    def _r():
        e = ask_text("Expression (e.g. 25 * 4):","Calculator")
        if e: feat_calculate(e)
    threading.Thread(target=_r,daemon=True).start()

def _wiki_prompt():
    def _r():
        q = ask_text("Search Wikipedia:","Wikipedia")
        if q: feat_wikipedia(q)
    threading.Thread(target=_r,daemon=True).start()

def _defn_prompt():
    def _r():
        w = ask_text("Define word:","Dictionary")
        if w: feat_define(w)
    threading.Thread(target=_r,daemon=True).start()

def _timer_prompt():
    def _r():
        v = ask_text("Duration (e.g. 5 minutes):","Timer")
        if v:
            m = re.search(r"(\d+)\s*(hour|hours|minute|minutes|second|seconds)",v)
            if m: feat_timer(int(m.group(1)), m.group(2))
    threading.Thread(target=_r,daemon=True).start()

def _alarm_prompt():
    def _r():
        v = ask_text("Alarm time (e.g. 7 30 am):","Alarm")
        if v:
            m = re.search(r"(\d{1,2})[:\s]?(\d{2})?\s*(am|pm)?",v,re.I)
            if m:
                h=int(m.group(1)); mn=int(m.group(2) or 0); mer=(m.group(3) or "").lower()
                if mer=="pm" and h!=12: h+=12
                elif mer=="am" and h==12: h=0
                feat_alarm(h,mn)
    threading.Thread(target=_r,daemon=True).start()

def _yt_prompt():
    def _r():
        q = ask_text("Search YouTube:","YouTube")
        if q: feat_youtube_search(q)
    threading.Thread(target=_r,daemon=True).start()

def _gs_prompt():
    def _r():
        q = ask_text("Search Google:","Google")
        if q: feat_google_search(q)
    threading.Thread(target=_r,daemon=True).start()

def _trans_prompt():
    def _r():
        t = ask_text("Text to translate:","Translate")
        if t: feat_translate(t)
    threading.Thread(target=_r,daemon=True).start()

ROOT = tk.Tk()
ROOT.title(f"Max — {USER_NAME}'s Assistant v{VERSION}")
ROOT.geometry("1060x760"); ROOT.configure(bg=C["bg0"]); ROOT.resizable(True,True)
ROOT.update_idletasks()
sw,sh = ROOT.winfo_screenwidth(), ROOT.winfo_screenheight()
ROOT.geometry(f"1060x760+{(sw-1060)//2}+{(sh-760)//2}")

tk.Frame(ROOT,bg=C["gold"],height=3).pack(fill="x",side="top")
hdr=tk.Frame(ROOT,bg=C["bg0"]); hdr.pack(fill="x")
hl=tk.Frame(hdr,bg=C["bg0"]); hl.pack(side=tk.LEFT,padx=20,pady=10)
tk.Label(hl,text="MAX",font=("Helvetica Neue",36,"bold"),fg=C["gold"],bg=C["bg0"]).pack(side=tk.LEFT)
tk.Label(hl,text=f"  {USER_NAME}'s Assistant  v{VERSION}",font=("Helvetica Neue",11),fg=C["txt2"],bg=C["bg0"]).pack(side=tk.LEFT,pady=(12,0))
hr=tk.Frame(hdr,bg=C["bg0"]); hr.pack(side=tk.RIGHT,padx=20)
wake_led=tk.Label(hr,text="IDLE",font=("Helvetica Neue",9,"bold"),fg=C["txt2"],bg=C["bg0"]); wake_led.pack(anchor="e")
cv=tk.StringVar(value="")
tk.Label(hr,textvariable=cv,font=("Courier New",9),fg=C["txt2"],bg=C["bg0"]).pack(anchor="e")
tk.Label(hdr,text=f'Say "{WAKE_WORD}" → "Yes {USER_NAME}?"',
         font=("Helvetica Neue",9,"italic"),fg=C["gold_dim"],bg=C["bg0"]).pack(side=tk.LEFT,padx=6)
def _tick(): cv.set(datetime.datetime.now().strftime("  %a %b %d  %H:%M:%S")); ROOT.after(1000,_tick)
_tick()

tk.Frame(ROOT,bg=C["border"],height=1).pack(fill="x")
sb=tk.Frame(ROOT,bg=C["bg1"],height=24); sb.pack(fill="x")
status_var=tk.StringVar(value="Initialising…")
status_lbl=tk.Label(sb,textvariable=status_var,font=("Helvetica Neue",8),
                    fg=C["teal"],bg=C["bg1"],anchor="w",padx=14); status_lbl.pack(side=tk.LEFT)
for lbl,ok in [("TTS",TTS_AVAILABLE),("SD",SOUNDDEVICE_AVAILABLE),
               ("SR",SR_AVAILABLE),("psutil",PSUTIL_AVAILABLE),
               ("wiki",WIKI_AVAILABLE),("pgw",PYGETWINDOW_AVAILABLE)]:
    tk.Label(sb,text=lbl,font=("Helvetica Neue",7,"bold"),
             fg=C["mint"] if ok else C["coral"],bg=C["bg1"]).pack(side=tk.RIGHT,padx=4)
tk.Label(sb,text="  libs: ",font=("Helvetica Neue",7),fg=C["txt2"],bg=C["bg1"]).pack(side=tk.RIGHT)
tk.Frame(ROOT,bg=C["border"],height=1).pack(fill="x")

body=tk.Frame(ROOT,bg=C["bg0"]); body.pack(fill="both",expand=True)
side=tk.Frame(body,bg=C["bg1"],width=220); side.pack(side=tk.LEFT,fill="y"); side.pack_propagate(False)
sbc=tk.Canvas(side,bg=C["bg1"],highlightthickness=0,bd=0); sbc.pack(side=tk.LEFT,fill="both",expand=True)
sbs=tk.Scrollbar(side,orient="vertical",command=sbc.yview); sbs.pack(side=tk.RIGHT,fill="y")
sbc.configure(yscrollcommand=sbs.set)
sbi=tk.Frame(sbc,bg=C["bg1"]); sbw=sbc.create_window((0,0),window=sbi,anchor="nw")
def _sbcfg(e): sbc.configure(scrollregion=sbc.bbox("all")); sbc.itemconfig(sbw,width=e.width)
sbi.bind("<Configure>",_sbcfg); sbc.bind("<Configure>",lambda e:sbc.itemconfig(sbw,width=e.width))
sbc.bind_all("<MouseWheel>",lambda e:sbc.yview_scroll(int(-1*(e.delta/120)),"units"))

_sec(sbi,"CONTROL")
start_btn=_mk_btn(sbi,"  Start Max",start_pa,C["mint"],C["bg0"],22); start_btn.pack(fill="x",padx=10,pady=2)
stop_btn =_mk_btn(sbi,"  Stop Max", stop_pa, C["txt2"],"white",22); stop_btn.pack(fill="x",padx=10,pady=2)
stop_btn.config(state=tk.DISABLED)
vr=tk.Frame(sbi,bg=C["bg1"]); vr.pack(fill="x",padx=10,pady=2)
for t,c,bg in [("Mic Voice",_oneshot,C["coral"]),("Text Input",_textcmd,C["teal"])]:
    tk.Button(vr,text=t,command=c,bg=bg,fg=C["bg0"],font=("Helvetica Neue",8,"bold"),
              relief="flat",cursor="hand2",padx=6,pady=4,
              activebackground=C["bg4"],activeforeground=C["txt0"]).pack(side=tk.LEFT,expand=True,fill="x",padx=1)
_sbtn(sbi,"Test Voice",lambda:qr(lambda:speak(f"Hello {USER_NAME}! Max is working.")),C["bg3"])

_sec(sbi,"TIME & DATE")
_sbtn(sbi,"Current Time", lambda:qr(feat_time))
_sbtn(sbi,"Current Date", lambda:qr(feat_date))
_sbtn(sbi,"Date & Time",  lambda:qr(feat_datetime))

_sec(sbi,"WEB — OPEN")
_sbtn(sbi,"Google Search",  _gs_prompt)
_sbtn(sbi,"YouTube Search", _yt_prompt)
_sbtn(sbi,"YouTube",    lambda:qr(feat_open_site,"youtube"))
_sbtn(sbi,"Gmail",      lambda:qr(feat_open_site,"gmail"))
_sbtn(sbi,"GitHub",     lambda:qr(feat_open_site,"github"))
_sbtn(sbi,"LinkedIn",   lambda:qr(feat_open_site,"linkedin"))
_sbtn(sbi,"WhatsApp",   lambda:qr(feat_open_site,"whatsapp"))
_sbtn(sbi,"Instagram",  lambda:qr(feat_open_site,"instagram"))
_sbtn(sbi,"Discord",    lambda:qr(feat_open_site,"discord"))
_sbtn(sbi,"Spotify",    lambda:qr(feat_open_site,"spotify"))
_sbtn(sbi,"ChatGPT",    lambda:qr(feat_open_site,"chatgpt"))
_sbtn(sbi,"Gemini",     lambda:qr(feat_open_site,"gemini"))
_sbtn(sbi,"Reddit",     lambda:qr(feat_open_site,"reddit"))
_sbtn(sbi,"Netflix",    lambda:qr(feat_open_site,"netflix"))

_sec(sbi,"WEB — CLOSE TAB")
_sbtn(sbi,"Close YouTube",   lambda:qr(feat_close_site,"youtube"))
_sbtn(sbi,"Close Gmail",     lambda:qr(feat_close_site,"gmail"))
_sbtn(sbi,"Close GitHub",    lambda:qr(feat_close_site,"github"))
_sbtn(sbi,"Close LinkedIn",  lambda:qr(feat_close_site,"linkedin"))
_sbtn(sbi,"Close WhatsApp",  lambda:qr(feat_close_site,"whatsapp"))
_sbtn(sbi,"Close Instagram", lambda:qr(feat_close_site,"instagram"))
_sbtn(sbi,"Close Discord",   lambda:qr(feat_close_site,"discord"))
_sbtn(sbi,"Close Spotify",   lambda:qr(feat_close_site,"spotify"))
_sbtn(sbi,"Close ChatGPT",   lambda:qr(feat_close_site,"chatgpt"))
_sbtn(sbi,"Close Gemini",    lambda:qr(feat_close_site,"gemini"))

_sec(sbi,"CHROME")
_sbtn(sbi,"Open Chrome",  lambda:qr(feat_open_chrome))
_sbtn(sbi,"Close Chrome", lambda:qr(feat_close_chrome))

_sec(sbi,"APPS — OPEN")
_sbtn(sbi,"Notepad",     lambda:qr(feat_open_app,"notepad"))
_sbtn(sbi,"Calculator",  lambda:qr(feat_open_app,"calculator"))
_sbtn(sbi,"VS Code",     lambda:qr(feat_open_app,"vscode"))
_sbtn(sbi,"Firefox",     lambda:qr(feat_open_app,"firefox"))
_sbtn(sbi,"Paint",       lambda:qr(feat_open_app,"paint"))
_sbtn(sbi,"Word",        lambda:qr(feat_open_app,"word"))
_sbtn(sbi,"Excel",       lambda:qr(feat_open_app,"excel"))
_sbtn(sbi,"PowerPoint",  lambda:qr(feat_open_app,"powerpoint"))

_sec(sbi,"APPS — CLOSE")
_sbtn(sbi,"Close Notepad",    lambda:qr(feat_close_app,"notepad"))
_sbtn(sbi,"Close Calculator", lambda:qr(feat_close_app,"calculator"))
_sbtn(sbi,"Close VS Code",    lambda:qr(feat_close_app,"vscode"))
_sbtn(sbi,"Close Firefox",    lambda:qr(feat_close_app,"firefox"))
_sbtn(sbi,"Close Paint",      lambda:qr(feat_close_app,"paint"))
_sbtn(sbi,"Close Word",       lambda:qr(feat_close_app,"word"))
_sbtn(sbi,"Close Excel",      lambda:qr(feat_close_app,"excel"))
_sbtn(sbi,"Close PowerPoint", lambda:qr(feat_close_app,"powerpoint"))

_sec(sbi,"SYSTEM INFO")
_sbtn(sbi,"System Info", lambda:qr(feat_system_info))
_sbtn(sbi,"Battery",     lambda:qr(feat_battery))
_sbtn(sbi,"CPU Usage",   lambda:qr(feat_cpu))
_sbtn(sbi,"RAM Usage",   lambda:qr(feat_ram))
_sbtn(sbi,"Disk Usage",  lambda:qr(feat_disk))
_sbtn(sbi,"Processes",   lambda:qr(feat_processes))
_sbtn(sbi,"Network",     lambda:qr(feat_network))
_sbtn(sbi,"Public IP",   lambda:qr(feat_public_ip))
_sbtn(sbi,"Ping",        lambda:qr(feat_ping))

_sec(sbi,"POWER")
_sbtn(sbi,"Lock Screen", lambda:qr(feat_lock),C["bg3"])
_sbtn(sbi,"Sleep",       lambda:qr(feat_sleep),C["bg3"])
_sbtn(sbi,"Restart",     feat_restart,C["bg3"])
_sbtn(sbi,"Log Out",     lambda:qr(feat_logout),C["bg3"])
_sbtn(sbi,"Shutdown",    feat_shutdown,C["bg3"])

_sec(sbi,"TOOLS")
_sbtn(sbi,"Calculator",      _calc_prompt)
_sbtn(sbi,"Screenshot",      lambda:qr(feat_screenshot))
_sbtn(sbi,"Set Timer",       _timer_prompt)
_sbtn(sbi,"Set Alarm",       _alarm_prompt)
_sbtn(sbi,"Quick Note",      lambda:ROOT.after(0,feat_note))
_sbtn(sbi,"Clipboard",       lambda:qr(feat_clipboard))
_sbtn(sbi,"Clear Clipboard", lambda:qr(feat_clear_clipboard))
_sbtn(sbi,"Vol Up",          lambda:qr(feat_volume,"up"))
_sbtn(sbi,"Vol Down",        lambda:qr(feat_volume,"down"))
_sbtn(sbi,"Mute",            lambda:qr(feat_volume,"mute"))
_sbtn(sbi,"Unmute",          lambda:qr(feat_volume,"unmute"))

_sec(sbi,"KNOWLEDGE")
_sbtn(sbi,"Wikipedia",  _wiki_prompt)
_sbtn(sbi,"Dictionary", _defn_prompt)
_sbtn(sbi,"Weather",    lambda:qr(feat_weather))
_sbtn(sbi,"News",       lambda:qr(feat_news))
_sbtn(sbi,"Translate",  _trans_prompt)

_sec(sbi,"FUN")
_sbtn(sbi,"Tell a Joke", lambda:qr(feat_joke))
_sbtn(sbi,"Inspire Me",  lambda:qr(feat_quote))
_sbtn(sbi,"Flip a Coin", lambda:qr(feat_coin))
_sbtn(sbi,"Roll a Dice", lambda:qr(feat_dice))

_sec(sbi,"ACTIONS")
_sbtn(sbi,"List Files",    lambda:qr(feat_list_files))
_sbtn(sbi,"Help",          lambda:qr(feat_help),C["violet"])
_sbtn(sbi,"Clear Console", lambda:(console.config(state=tk.NORMAL),
                                    console.delete("1.0",tk.END),
                                    console.config(state=tk.DISABLED)),C["bg3"])

tk.Frame(body,bg=C["border"],width=1).pack(side=tk.LEFT,fill="y")
right=tk.Frame(body,bg=C["bg0"]); right.pack(side=tk.LEFT,fill="both",expand=True)
ch=tk.Frame(right,bg=C["bg1"],height=30); ch.pack(fill="x"); ch.pack_propagate(False)
tk.Label(ch,text=f"  MAX CONSOLE — {USER_NAME}",font=("Helvetica Neue",9,"bold"),
         fg=C["teal"],bg=C["bg1"]).pack(side=tk.LEFT,padx=4,pady=5)
tk.Label(ch,text=f"{platform.system()} · Python {platform.python_version()}  ",
         font=("Helvetica Neue",8),fg=C["txt2"],bg=C["bg1"]).pack(side=tk.RIGHT,pady=5)
cf=tk.Frame(right,bg=C["bg0"]); cf.pack(fill="both",expand=True)
console=tk.Text(cf,font=FNT_MONO,bg=C["bg0"],fg=C["txt1"],insertbackground=C["gold"],
                relief="flat",bd=0,wrap=tk.WORD,padx=16,pady=10,
                selectbackground=C["gold"],selectforeground=C["bg0"],state=tk.DISABLED)
console.pack(side=tk.LEFT,fill="both",expand=True)
cs=tk.Scrollbar(cf,orient="vertical",command=console.yview,bg=C["bg1"],troughcolor=C["bg0"])
cs.pack(side=tk.RIGHT,fill="y"); console.configure(yscrollcommand=cs.set)
for tag,fg in [("pa",C["teal"]),("user",C["gold"]),("heard",C["violet"]),("info",C["txt2"]),
               ("warn",C["orange"]),("err",C["coral"]),("ok",C["mint"]),
               ("dim",C["bg4"]),("normal",C["txt1"])]:
    console.tag_configure(tag,foreground=fg)

ib=tk.Frame(right,bg=C["bg1"],height=44); ib.pack(fill="x",side="bottom"); ib.pack_propagate(False)
tk.Frame(right,bg=C["border"],height=1).pack(fill="x",side="bottom")
tk.Label(ib,text="  >",font=("Courier New",16,"bold"),fg=C["gold"],bg=C["bg1"]).pack(side=tk.LEFT,padx=(8,2))
PH="Type a command and press Enter…"
iv=tk.StringVar()
ie=tk.Entry(ib,textvariable=iv,font=("Courier New",10),bg=C["bg2"],fg=C["txt0"],
            insertbackground=C["gold"],relief="flat",bd=4,highlightthickness=1,
            highlightcolor=C["teal"],highlightbackground=C["border"])
ie.pack(side=tk.LEFT,fill="both",expand=True,padx=4,pady=7)
ie.insert(0,PH); ie.config(fg=C["txt2"])
ie.bind("<FocusIn>", lambda e:(ie.delete(0,tk.END),ie.config(fg=C["txt0"])) if ie.get()==PH else None)
ie.bind("<FocusOut>",lambda e:(ie.insert(0,PH),ie.config(fg=C["txt2"])) if not ie.get() else None)
def _sub(e=None):
    c=iv.get().strip()
    if c and c!=PH:
        ie.delete(0,tk.END); user_echo(c)
        threading.Thread(target=dispatch,args=(c.lower(),),daemon=True).start()
ie.bind("<Return>",_sub)
_mk_btn(ib,"Send",_sub,C["gold"],C["bg0"],9).pack(side=tk.RIGHT,padx=8,pady=7)

def _boot():
    _cwrite("╔══════════════════════════════════════════════════╗\n","ok")
    _cwrite(f"║   Max v{VERSION} — {USER_NAME}'s Personal Assistant     ║\n","ok")
    _cwrite("╚══════════════════════════════════════════════════╝\n\n","ok")
    _cwrite(f"  Platform : {platform.system()} {platform.release()}\n","info")
    _cwrite(f"  Python   : {platform.python_version()}\n\n","info")
    for lbl,ok,fix in [
        ("SpeechRecognition",  SR_AVAILABLE,          "pip install SpeechRecognition"),
        ("sounddevice+numpy",  SOUNDDEVICE_AVAILABLE, "pip install sounddevice numpy"),
        ("pyttsx3 (TTS)",      TTS_AVAILABLE,          "pip install pyttsx3"),
        ("psutil",             PSUTIL_AVAILABLE,       "pip install psutil"),
        ("wikipedia",          WIKI_AVAILABLE,         "pip install wikipedia"),
        ("pyautogui",          PYAUTOGUI_AVAILABLE,    "pip install pyautogui"),
        ("pygetwindow",        PYGETWINDOW_AVAILABLE,  "pip install pygetwindow"),
        ("requests",           REQUESTS_AVAILABLE,     "pip install requests"),
        ("python-dotenv",      True,                   "pip install python-dotenv"),
    ]:
        _cwrite(f"  {lbl:<22}: {'OK' if ok else 'MISSING — '+fix}\n","ok" if ok else "warn")
    # Warn if API keys are missing
    if not os.environ.get("OPENWEATHER_API_KEY"):
        _cwrite("  ! OPENWEATHER_API_KEY not set — add to .env for weather\n","warn")
    if not os.environ.get("NEWS_API_KEY"):
        _cwrite("  ! NEWS_API_KEY not set — add to .env for news\n","warn")
    _cwrite(f'\n  Say "{WAKE_WORD}" → Max says "Yes {USER_NAME}?"\n',"normal")
    _cwrite("  Fuzzy corrections active — mishearings auto-fixed.\n","info")
    _cwrite("  [corrected] lines show what was fixed in dim text.\n","info")
    _cwrite("  Or type in the bar below and press Enter.\n\n","normal")

_boot()
set_status(f"Ready {USER_NAME} — click Start Max", C["mint"])
ROOT.after(40, _flush_gui)
ROOT.protocol("WM_DELETE_WINDOW", ROOT.destroy)
ROOT.mainloop()
_tts_q.put(None)