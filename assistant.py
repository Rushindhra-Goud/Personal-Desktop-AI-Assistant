#!/usr/bin/env python3
"""
PA — Personal Assistant v2.3
Wake word: pvporcupine (offline) with Google Speech fallback
Install:
    pip install SpeechRecognition sounddevice numpy pyttsx3 psutil
    pip install requests wikipedia pyjokes pyautogui
    pip install pvporcupine  (optional but recommended for wake word)
"""

import datetime
import webbrowser
import os
import threading
import time
import re
import socket
import queue
import platform
import subprocess
import random
import math
import ast
import operator as op
import logging
import tkinter as tk
import tkinter.messagebox as msgbox

# ── OPTIONAL IMPORTS ──────────────────────────────────────────────────────────
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False
    sr = None

try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None
    np = None

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except (ImportError, OSError):
    PYAUDIO_AVAILABLE = False

# pvporcupine — offline wake word engine (no internet needed)
try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    pvporcupine = None

try:
    import pyttsx3
    _tts_test        = pyttsx3.init()
    _tts_voices_list = _tts_test.getProperty('voices') or []
    TTS_VOICE_IDX    = 1 if len(_tts_voices_list) > 1 else 0
    TTS_VOICE_ID     = _tts_voices_list[TTS_VOICE_IDX].id if _tts_voices_list else None
    _tts_test.stop()
    del _tts_test
    TTS_AVAILABLE = True
except Exception:
    TTS_AVAILABLE = False
    TTS_VOICE_ID  = None

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

try:
    import wikipedia
    WIKI_AVAILABLE = True
except ImportError:
    WIKI_AVAILABLE = False
    wikipedia = None

try:
    import pyjokes
    JOKES_AVAILABLE = True
except ImportError:
    JOKES_AVAILABLE = False
    pyjokes = None

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
VERSION       = "2.3"
WAKE_WORD     = "hey pa"
SAMPLE_RATE   = 16000          # Hz — microphone sample rate
CHANNELS      = 1              # mono
DTYPE         = 'int16'        # 16-bit PCM
CHUNK_MS      = 30             # milliseconds per audio chunk
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_MS / 1000)

# Voice activity detection tuning
WAIT_FOR_SPEECH_SEC = 8        # max seconds to wait for speech to start
SILENCE_DURATION_MS = 800      # ms of consecutive silence that ends recording
WAKE_SCAN_SEC       = 3        # seconds to listen for wake word
WAKE_SILENCE_MS     = 600      # ms of silence that ends wake-word capture
COMMAND_DURATION_SEC = 6       # max seconds for command audio capture
CALIBRATION_SEC     = 2        # seconds of silence for mic calibration

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"
IS_MAC     = platform.system() == "Darwin"

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename='pa_assistant.log',
    level=logging.WARNING,
    format='%(asctime)s %(levelname)s %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('PA')

C = {
    'bg0':'#070B14','bg1':'#0C1220','bg2':'#111827','bg3':'#192338','bg4':'#1F2D47',
    'gold':'#F5C518','gold_dim':'#8A6C0A','teal':'#00E5CC','violet':'#9B59FF',
    'coral':'#FF5C5C','mint':'#39FF85','txt0':'#F0F6FF','txt1':'#8DA4C8',
    'txt2':'#3D566E','border':'#1E3054','orange':'#FF8C30',
}
FNT_BTN  = ("Helvetica Neue", 9, "bold")
FNT_MONO = ("Courier New", 10)

# ── GUI QUEUE ─────────────────────────────────────────────────────────────────
gui_queue = queue.Queue()

def q(fn, *args):
    gui_queue.put((fn, args))

def flush_gui():
    try:
        while True:
            fn, args = gui_queue.get_nowait()
            fn(*args)
    except queue.Empty:
        pass
    ROOT.after(40, flush_gui)

# ── TTS WORKER ────────────────────────────────────────────────────────────────
_tts_q = queue.Queue()

def _tts_worker():
    engine = None
    if TTS_AVAILABLE:
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 165)
            engine.setProperty('volume', 1.0)
            if TTS_VOICE_ID:
                engine.setProperty('voice', TTS_VOICE_ID)
        except Exception as e:
            logger.error("TTS engine init failed: %s", e, exc_info=True)
            engine = None
    while True:
        text = _tts_q.get()
        if text is None:
            break
        if engine:
            try:
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                logger.warning("TTS speak failed, reinitialising engine: %s", e)
                try:
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 165)
                    engine.setProperty('volume', 1.0)
                    if TTS_VOICE_ID:
                        engine.setProperty('voice', TTS_VOICE_ID)
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e2:
                    logger.error("TTS reinit failed: %s", e2, exc_info=True)
        _tts_q.task_done()

threading.Thread(target=_tts_worker, daemon=True).start()

# ── OUTPUT ────────────────────────────────────────────────────────────────────
def speak(text, tts=True):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    q(_console_write, f"[{ts}] PA: {text}\n", "pa")
    if tts and TTS_AVAILABLE:
        _tts_q.put(text)

def user_echo(text):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    q(_console_write, f"[{ts}] You: {text}\n", "user")

def info(text):    q(_console_write, f"  i  {text}\n", "info")
def warn(text):    q(_console_write, f"  !  {text}\n", "warn")
def err(text):     q(_console_write, f"  x  {text}\n", "err")
def success(text): q(_console_write, f"  ok  {text}\n", "ok")

def _console_write(text, tag="normal"):
    console.config(state=tk.NORMAL)
    console.insert(tk.END, text, tag)
    console.see(tk.END)
    console.config(state=tk.DISABLED)

def set_status(text, color=None):
    q(_do_set_status, text, color or C['teal'])

def _do_set_status(text, color):
    status_var.set(text)
    status_lbl.config(fg=color)

def set_wake_led(state):
    q(_do_wake_led, state)

def _do_wake_led(state):
    styles = {
        'idle':      ("IDLE",      C['txt2']),
        'scanning':  ("SCANNING",  C['gold']),
        'heard':     ("WAKE!",     C['mint']),
        'listening': ("LISTENING", C['coral']),
    }
    txt, col = styles.get(state, styles['idle'])
    wake_led.config(text=txt, fg=col)

# ══════════════════════════════════════════════════════════════════════════════
#  CALIBRATION — called ONCE at startup, no duplicate calls
# ══════════════════════════════════════════════════════════════════════════════
_NOISE_RMS          = 100
_SPEECH_THRESHOLD   = 200
_AMBIENT_CALIBRATED = False

def _calibrate_sounddevice():
    """
    Record 2 seconds of silence to measure background noise.
    Sets _NOISE_RMS and _SPEECH_THRESHOLD.
    Called exactly ONCE from _main_loop at startup.
    """
    global _NOISE_RMS, _SPEECH_THRESHOLD, _AMBIENT_CALIBRATED
    if _AMBIENT_CALIBRATED or not SOUNDDEVICE_AVAILABLE:
        return
    try:
        info("Calibrating mic — stay quiet for 2 seconds...")
        data = sd.rec(int(CALIBRATION_SEC * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                      channels=CHANNELS, dtype=DTYPE)
        sd.wait()
        _NOISE_RMS        = max(30, float(np.sqrt(np.mean(data.astype(np.float32) ** 2))))
        _SPEECH_THRESHOLD = max(100, int(_NOISE_RMS * 2.5))
        _AMBIENT_CALIBRATED = True
        info(f"Calibrated. Noise RMS={_NOISE_RMS:.0f}  Speech threshold={_SPEECH_THRESHOLD}")
    except Exception as e:
        warn(f"Calibration failed ({e}) — using defaults.")
        _NOISE_RMS        = 100
        _SPEECH_THRESHOLD = 200
        _AMBIENT_CALIBRATED = True

# ══════════════════════════════════════════════════════════════════════════════
#  VAD RECORDING — fixed, no silent audio sent to Google
# ══════════════════════════════════════════════════════════════════════════════
def _rms(chunk):
    return float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2)))

def _record_until_silence(max_seconds=10):
    """
    Phase 1 — wait until mic RMS exceeds _SPEECH_THRESHOLD (real speech).
    Phase 2 — record until 0.8s consecutive silence OR max_seconds reached.
    Returns numpy int16 array of ONLY the spoken audio, or None if nothing heard.

    FIX: This function is called correctly — calibration runs separately
         before this, not inside this function.
    """
    if not SOUNDDEVICE_AVAILABLE:
        return None

    wait_chunks    = int(WAIT_FOR_SPEECH_SEC * 1000 / CHUNK_MS)
    max_chunks     = int(max_seconds * 1000 / CHUNK_MS)
    silence_needed = int(SILENCE_DURATION_MS / CHUNK_MS)

    frames        = []
    silent_streak = 0
    speech_count  = 0

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                dtype=DTYPE, blocksize=CHUNK_SAMPLES)
        stream.start()

        # ── Phase 1: wait for speech ──────────────────────────────────────
        for _ in range(wait_chunks):
            chunk, _ = stream.read(CHUNK_SAMPLES)
            if _rms(chunk) > _SPEECH_THRESHOLD:
                frames.append(chunk.copy())
                speech_count = 1
                break   # speech detected, move to phase 2

        if speech_count == 0:
            stream.stop()
            stream.close()
            return None   # nothing spoken within wait time

        # ── Phase 2: record until silence ────────────────────────────────
        for _ in range(max_chunks):
            chunk, _ = stream.read(CHUNK_SAMPLES)
            frames.append(chunk.copy())
            if _rms(chunk) > _SPEECH_THRESHOLD:
                silent_streak = 0
                speech_count += 1
            else:
                silent_streak += 1
                if silent_streak >= silence_needed:
                    break

        stream.stop()
        stream.close()

        if speech_count < 2:
            return None   # too short, likely noise

        return np.concatenate(frames, axis=0)

    except Exception as e:
        logger.error("VAD recording error: %s", e, exc_info=True)
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        err(f"Recording error: {e}")
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  WAKE WORD — pvporcupine (offline) with strict Google Speech fallback
# ══════════════════════════════════════════════════════════════════════════════

# ── CHANGE 1: strict _is_wake_phrase — no false triggers on just "pa" or "hey"
def _is_wake_phrase(text: str) -> bool:
    """
    Returns True if the recognised text contains the wake phrase.
    Supports "hey pa" and its common mishearings, plus the simple
    word "wake" so the user can just say "wake" to activate PA.
    """
    if not text:
        return False
    t = text.lower().strip()

    wake_phrases = [
        # Primary wake word
        "hey pa", "hey p a", "heypa",
        # Mishearings of "hey pa"
        "okay pa", "ok pa", "hey pee ay",
        "hay pa",  "aye pa", "hey par",
        "a pa",    "hey pea", "hey pie",
        "hey pas", "hepa",
        # Simple single-word trigger — user can just say "wake"
        "wake",
    ]
    for phrase in wake_phrases:
        if phrase in t:
            logger.info("Wake phrase matched '%s' in: %s", phrase, t)
            return True

    logger.debug("Wake scan heard '%s' — no match", text)
    return False

# ── CHANGE 2: pvporcupine offline wake word engine ────────────────────────────
_porcupine_handle = None

def _init_porcupine():
    """
    Try to initialise pvporcupine with the built-in 'porcupine' keyword
    (says "porcupine" to wake). For "hey pa" you need a custom keyword file
    from https://console.picovoice.ai/ — free account required.

    Falls back to Google Speech wake word scanning if not available.
    """
    global _porcupine_handle
    if not PORCUPINE_AVAILABLE:
        return False
    try:
        # Uses built-in keyword 'porcupine' as demo.
        # Replace keyword_paths=['/path/to/hey-pa.ppn'] once you have
        # a custom keyword file from https://console.picovoice.ai/
        _porcupine_handle = pvporcupine.create(keywords=["porcupine"])
        info("pvporcupine loaded — say 'porcupine' to wake (or get a custom 'hey pa' keyword).")
        return True
    except Exception as e:
        logger.warning("pvporcupine init failed: %s", e)
        warn(f"pvporcupine init failed ({e}) — falling back to Google Speech wake word.")
        _porcupine_handle = None
        return False

def _porcupine_scan() -> bool:
    """
    Listen for one frame using pvporcupine.
    Returns True if wake word detected, False otherwise.
    pvporcupine is OFFLINE — no internet needed, near-zero CPU.
    """
    if _porcupine_handle is None or not PYAUDIO_AVAILABLE:
        return False
    try:
        pa  = pyaudio.PyAudio()
        stream = pa.open(
            rate=_porcupine_handle.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=_porcupine_handle.frame_length,
        )
        pcm = stream.read(_porcupine_handle.frame_length, exception_on_overflow=False)
        stream.stop_stream(); stream.close(); pa.terminate()

        import struct
        pcm_unpacked = struct.unpack_from("h" * _porcupine_handle.frame_length, pcm)
        result = _porcupine_handle.process(pcm_unpacked)
        return result >= 0  # >= 0 means wake word detected
    except Exception as e:
        logger.warning("pvporcupine scan error: %s", e)
        return False

def _google_wake_scan() -> str:
    """
    Single wake scan using sounddevice + Google Speech.
    Returns: 'woke' | 'nothing' | 'no_mic'
    """
    if not _mic_available():
        return "no_mic"
    if not SR_AVAILABLE:
        return "no_mic"

    if not SOUNDDEVICE_AVAILABLE:
        return "no_mic"

    wait_chunks    = int(WAKE_SCAN_SEC * 1000 / CHUNK_MS)
    silence_needed = int(WAKE_SILENCE_MS / CHUNK_MS)
    frames         = []
    silent_streak  = 0
    speech_count   = 0

    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                dtype=DTYPE, blocksize=CHUNK_SAMPLES)
        stream.start()

        for _ in range(wait_chunks):
            chunk, _ = stream.read(CHUNK_SAMPLES)
            if _rms(chunk) > _SPEECH_THRESHOLD:
                frames.append(chunk.copy())
                speech_count = 1
                break

        if speech_count > 0:
            for _ in range(int(WAKE_SCAN_SEC * 1000 / CHUNK_MS)):
                chunk, _ = stream.read(CHUNK_SAMPLES)
                frames.append(chunk.copy())
                if _rms(chunk) > _SPEECH_THRESHOLD:
                    silent_streak = 0
                    speech_count += 1
                else:
                    silent_streak += 1
                    if silent_streak >= silence_needed:
                        break

        stream.stop(); stream.close()

        if speech_count < 2 or not frames:
            return "nothing"

        audio = sr.AudioData(np.concatenate(frames, axis=0).tobytes(), SAMPLE_RATE, 2)
        r     = sr.Recognizer()
        text  = r.recognize_google(audio)

        # CHANGE 3: debug print for wake word heard
        print(f"[Wake scan] Heard: '{text}'")

        if _is_wake_phrase(text):
            return "woke"
        return "nothing"

    except sr.UnknownValueError:
        return "nothing"
    except sr.RequestError as e:
        logger.warning("Google Speech API error during wake scan: %s", e)
        err(f"Google Speech error: {e}")
        return "nothing"
    except Exception as e:
        logger.error("Wake scan unexpected error: %s", e, exc_info=True)
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        return "nothing"

def scan_once() -> str:
    """
    Unified wake word scan.
    Uses pvporcupine (offline) if available, else Google Speech.
    Returns: 'woke' | 'nothing' | 'no_mic'
    """
    # ── pvporcupine path (offline, preferred) ────────────────────────────
    if _porcupine_handle is not None:
        detected = _porcupine_scan()
        if detected:
            print("[Wake scan] pvporcupine detected wake word!")
            return "woke"
        return "nothing"

    # ── Google Speech path (fallback) ────────────────────────────────────
    return _google_wake_scan()

def _mic_available():
    return SOUNDDEVICE_AVAILABLE or PYAUDIO_AVAILABLE

# ── VOICE CAPTURE ─────────────────────────────────────────────────────────────
def capture_voice(duration=6, wake_scan=False):
    """Capture command audio and return recognised text."""
    if not SR_AVAILABLE:
        return None
    if not _mic_available():
        return "NO_MIC"

    set_wake_led('scanning' if wake_scan else 'listening')

    if SOUNDDEVICE_AVAILABLE:
        samples = _record_until_silence(max_seconds=duration + 4)
        if samples is None:
            set_wake_led('idle')
            return None
        try:
            audio = sr.AudioData(samples.tobytes(), SAMPLE_RATE, 2)
            text  = sr.Recognizer().recognize_google(audio)
            set_wake_led('idle')
            set_status("Command received", C['mint'])
            q(_console_write, f"  Heard: {text}\n", "heard")
            return text.lower()
        except sr.UnknownValueError:
            set_wake_led('idle')
            warn("Could not understand — please speak clearly.")
            return None
        except sr.RequestError as e:
            set_wake_led('idle')
            err(f"Google Speech API error: {e}")
            return None
        except Exception as e:
            set_wake_led('idle')
            err(f"Voice error: {e}")
            return None

    if PYAUDIO_AVAILABLE:
        try:
            r = sr.Recognizer()
            mic = sr.Microphone()
            with mic as src:
                r.adjust_for_ambient_noise(src, duration=0.3)
                audio = r.listen(src, timeout=8, phrase_time_limit=duration + 2)
            text = r.recognize_google(audio)
            set_wake_led('idle')
            set_status("Command received", C['mint'])
            q(_console_write, f"  Heard: {text}\n", "heard")
            return text.lower()
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            set_wake_led('idle'); return None
        except sr.RequestError as e:
            set_wake_led('idle'); err(f"Google Speech error: {e}"); return None
        except Exception as e:
            set_wake_led('idle'); err(f"Voice error: {e}"); return None

    set_wake_led('idle')
    return "NO_MIC"

# ── POPUP INPUT ───────────────────────────────────────────────────────────────
def ask_text(prompt, title="PA Input"):
    result = [None]
    ev = threading.Event()
    def _build():
        dlg = tk.Toplevel(ROOT)
        dlg.title(title); dlg.geometry("500x170")
        dlg.configure(bg=C['bg1']); dlg.attributes('-topmost', True)
        dlg.grab_set(); dlg.resizable(False, False)
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth()  - 500) // 2
        y = (dlg.winfo_screenheight() - 170) // 2
        dlg.geometry(f"500x170+{x}+{y}")
        tk.Label(dlg, text=prompt, font=("Helvetica Neue",11,"bold"),
                 fg=C['teal'], bg=C['bg1']).pack(pady=(16,6), padx=20, anchor='w')
        evar = tk.StringVar()
        ent = tk.Entry(dlg, textvariable=evar, width=52, font=FNT_MONO,
                       bg=C['bg2'], fg=C['txt0'], insertbackground=C['gold'],
                       relief='flat', bd=6, highlightthickness=1,
                       highlightcolor=C['teal'], highlightbackground=C['border'])
        ent.pack(padx=20, fill='x'); ent.focus()
        def submit(): result[0]=evar.get().strip(); dlg.destroy(); ev.set()
        def cancel(): dlg.destroy(); ev.set()
        ent.bind('<Return>', lambda _: submit())
        dlg.protocol("WM_DELETE_WINDOW", cancel)
        bf = tk.Frame(dlg, bg=C['bg1']); bf.pack(pady=12)
        _mk_btn(bf,"OK",    submit,C['teal'], C['bg0'],w=10).pack(side=tk.LEFT,padx=6)
        _mk_btn(bf,"Cancel",cancel,C['coral'],C['bg0'],w=10).pack(side=tk.LEFT,padx=6)
    ROOT.after(0, _build); ev.wait(60)
    return result[0]

# ── FEATURES ──────────────────────────────────────────────────────────────────
def feat_time():
    speak(f"The time is {datetime.datetime.now().strftime('%I:%M %p')}")

def feat_date():
    speak(f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}")

def feat_datetime():
    now = datetime.datetime.now()
    speak(f"It is {now.strftime('%A, %B %d, %Y')} at {now.strftime('%I:%M %p')}")

SITES = {
    "youtube":("YouTube","https://www.youtube.com"),
    "linkedin":("LinkedIn","https://www.linkedin.com"),
    "github":("GitHub","https://github.com"),
    "gmail":("Gmail","https://mail.google.com"),
    "email":("Gmail","https://mail.google.com"),
    "google":("Google","https://www.google.com"),
    "stackoverflow":("Stack Overflow","https://stackoverflow.com"),
    "twitter":("Twitter","https://twitter.com"),
    "reddit":("Reddit","https://www.reddit.com"),
    "amazon":("Amazon","https://www.amazon.in"),
    "netflix":("Netflix","https://www.netflix.com"),
    "wikipedia":("Wikipedia","https://www.wikipedia.org"),
    "maps":("Google Maps","https://maps.google.com"),
    "drive":("Google Drive","https://drive.google.com"),
    "meet":("Google Meet","https://meet.google.com"),
    "docs":("Google Docs","https://docs.google.com"),
    "sheets":("Google Sheets","https://sheets.google.com"),
    "instagram":("Instagram","https://www.instagram.com"),
    "whatsapp":("WhatsApp Web","https://web.whatsapp.com"),
    "spotify":("Spotify","https://open.spotify.com"),
    "discord":("Discord","https://discord.com/app"),
    "notion":("Notion","https://www.notion.so"),
    "chatgpt":("ChatGPT","https://chat.openai.com"),
    "gemini":("Gemini","https://gemini.google.com"),
}

def feat_open_site(cmd):
    clean = re.sub(r'\bopen\b','',cmd,flags=re.IGNORECASE).strip()
    for key,(name,url) in SITES.items():
        if key in clean or key in cmd:
            speak(f"Opening {name}!"); webbrowser.open(url); return
    m = re.search(r'open\s+([\w]+)',cmd)
    if m: speak(f"Opening {m.group(1)}."); webbrowser.open(f"https://www.{m.group(1)}.com")
    else: speak("Which website would you like me to open?")

def feat_google_search(cmd):
    qs = re.sub(r'\b(search|google|look up|find)\b','',cmd,flags=re.IGNORECASE).strip()
    if not qs: qs = ask_text("What should I search for?")
    if qs:
        speak(f"Searching Google for {qs}.")
        webbrowser.open(f"https://www.google.com/search?q={qs.replace(' ','+')}")

def feat_youtube_search(cmd):
    qs = re.sub(r'\b(youtube|play|search|find|watch|open)\b','',cmd,flags=re.IGNORECASE).strip()
    if not qs: qs = ask_text("What to search on YouTube?")
    if qs:
        speak(f"Searching YouTube for {qs}.")
        webbrowser.open(f"https://www.youtube.com/results?search_query={qs.replace(' ','+')}")

def feat_open_chrome():
    speak("Opening Chrome.")
    if IS_WINDOWS:
        for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]:
            if os.path.exists(p): subprocess.Popen([p]); return
        os.system("start chrome")
    elif IS_MAC: subprocess.Popen(["open","-a","Google Chrome"])
    elif IS_LINUX: subprocess.Popen(["google-chrome"])

def feat_open_email():
    speak("Opening Gmail."); webbrowser.open("https://mail.google.com")

# ── SAFE MATH EVALUATOR (replaces eval) ───────────────────────────────────────
_SAFE_OPS = {
    ast.Add:  op.add,   ast.Sub:  op.sub,
    ast.Mult: op.mul,   ast.Div:  op.truediv,
    ast.Pow:  op.pow,   ast.Mod:  op.mod,
    ast.USub: op.neg,   ast.UAdd: op.pos,
    ast.FloorDiv: op.floordiv,
}
_SAFE_MATH_FNS = {
    'sqrt': math.sqrt, 'floor': math.floor, 'ceil': math.ceil,
    'log':  math.log,  'log10': math.log10,
    'sin':  math.sin,  'cos':   math.cos,   'tan': math.tan,
    'fabs': math.fabs, 'abs':   abs,        'round': round,
}

def _safe_eval_node(node):
    """Recursively evaluate an AST node using only whitelisted operations."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.Num):          # Python < 3.8 compat
        return node.n
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        left  = _safe_eval_node(node.left)
        right = _safe_eval_node(node.right)
        return _SAFE_OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval_node(node.operand))
    if isinstance(node, ast.Call):
        fn_name = (node.func.id if isinstance(node.func, ast.Name)
                   else node.func.attr if isinstance(node.func, ast.Attribute)
                   else None)
        if fn_name in _SAFE_MATH_FNS:
            args = [_safe_eval_node(a) for a in node.args]
            return _SAFE_MATH_FNS[fn_name](*args)
    raise ValueError(f"Unsupported expression node: {ast.dump(node)}")

def _safe_calculate(expr: str):
    """Parse and evaluate a math expression with no use of eval()."""
    tree = ast.parse(expr, mode='eval')
    return _safe_eval_node(tree.body)

def feat_calculate(cmd):
    expr = re.sub(r'\b(calculate|compute|what is|whats|evaluate|solve)\b','',cmd,flags=re.IGNORECASE).strip()
    expr = (expr.replace("plus","+").replace("minus","-").replace("times","*")
               .replace("multiplied by","*").replace("divided by","/")
               .replace("mod","%").replace("power","**").replace("^","**")
               .replace("square root of","sqrt(").strip())
    if "sqrt(" in expr and not expr.endswith(")"): expr += ")"
    if not expr: speak("Please give me a math expression."); return
    try:
        res = _safe_calculate(expr)
        if isinstance(res, float) and res == int(res): res = int(res)
        speak(f"The result is {res}"); info(f"{expr} = {res}")
    except ZeroDivisionError: speak("Cannot divide by zero.")
    except ValueError as e:
        logger.warning("Calculator expression rejected: %s | expr: %s", e, expr)
        speak("Couldn't evaluate that.")
    except Exception as e:
        logger.error("Calculator unexpected error: %s | expr: %s", e, expr, exc_info=True)
        speak("Couldn't evaluate that.")

def feat_screenshot():
    if not PYAUTOGUI_AVAILABLE: speak("Run: pip install pyautogui"); return
    fname = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    try: pyautogui.screenshot().save(fname); speak(f"Screenshot saved as {fname}.")
    except Exception as e:
        logger.error("Screenshot failed: %s", e)
        speak(f"Screenshot failed: {e}")

def feat_system_info():
    if not PSUTIL_AVAILABLE: speak("Run: pip install psutil"); return
    cpu=psutil.cpu_percent(interval=1); mem=psutil.virtual_memory()
    disk=psutil.disk_usage('/'); cores=psutil.cpu_count(logical=True)
    speak(f"CPU at {cpu}% across {cores} cores. RAM {mem.percent}% used. Disk {disk.percent}% used.")

def feat_battery():
    if not PSUTIL_AVAILABLE: speak("Run: pip install psutil"); return
    b=psutil.sensors_battery()
    if b:
        st="charging" if b.power_plugged else "discharging"
        mins=int(b.secsleft/60) if b.secsleft!=psutil.POWER_TIME_UNLIMITED else -1
        speak(f"Battery at {b.percent:.0f}%, {st}" + (f", {mins} minutes remaining." if mins>0 else "."))
    else: speak("No battery — desktop system.")

def feat_cpu():
    if not PSUTIL_AVAILABLE: speak("Run: pip install psutil"); return
    speak(f"CPU at {psutil.cpu_percent(interval=0.5)}%, {psutil.cpu_freq().current:.0f} MHz.")

def feat_ram():
    if not PSUTIL_AVAILABLE: speak("Run: pip install psutil"); return
    m=psutil.virtual_memory()
    speak(f"RAM: {m.used//1024**2} MB used of {m.total//1024**2} MB. {m.percent}% used.")

def feat_disk():
    if not PSUTIL_AVAILABLE: speak("Run: pip install psutil"); return
    d=psutil.disk_usage('/')
    speak(f"Disk: {d.used//1024**3:.1f} GB used of {d.total//1024**3:.1f} GB. {d.percent}% full.")

def feat_processes():
    if not PSUTIL_AVAILABLE: speak("Run: pip install psutil"); return
    procs=sorted(psutil.process_iter(['pid','name','cpu_percent']),
                 key=lambda p:p.info['cpu_percent'] or 0,reverse=True)[:5]
    speak("Top 5 CPU processes:")
    for p in procs: info(f"  PID {p.info['pid']:5d}  {p.info['cpu_percent']:5.1f}%  {p.info['name']}")

def feat_network():
    try: host=socket.gethostname(); speak(f"Hostname: {host}, IP: {socket.gethostbyname(host)}")
    except Exception as e: speak(f"Network error: {e}")

def feat_public_ip():
    if not REQUESTS_AVAILABLE: speak("Run: pip install requests"); return
    try: speak(f"Your public IP is {requests.get('https://api.ipify.org?format=json',timeout=6).json()['ip']}")
    except Exception as e:
        logger.warning("Public IP fetch failed: %s", e)
        speak("Could not fetch public IP.")

def feat_ping():
    if not REQUESTS_AVAILABLE: speak("Run: pip install requests"); return
    try:
        t0=time.perf_counter(); requests.get("https://www.google.com",timeout=5)
        speak(f"Ping to Google: {int((time.perf_counter()-t0)*1000)} ms")
    except Exception as e:
        logger.warning("Ping failed: %s", e)
        speak("Ping failed.")

def feat_lock():
    speak("Locking screen."); time.sleep(1)
    if IS_WINDOWS: os.system("rundll32.exe user32.dll,LockWorkStation")
    elif IS_LINUX:
        for c in ["gnome-screensaver-command -l","xdg-screensaver lock","loginctl lock-session"]:
            if os.system(f"{c} 2>/dev/null")==0: break
    elif IS_MAC: os.system(r'/System/Library/CoreServices/Menu\ Extras/User.menu/Contents/Resources/CGSession -suspend')

def feat_sleep():
    speak("Going to sleep."); time.sleep(2)
    if IS_WINDOWS: os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    elif IS_LINUX: os.system("systemctl suspend")
    elif IS_MAC: os.system("pmset sleepnow")

def feat_shutdown():
    def _c():
        if msgbox.askyesno("Shutdown","Shut down now?",parent=ROOT):
            speak("Shutting down in 5 seconds.")
            def _d():
                time.sleep(5)
                if IS_WINDOWS: os.system("shutdown /s /t 1")
                elif IS_LINUX: os.system("shutdown -h now")
                elif IS_MAC: os.system("sudo shutdown -h now")
            threading.Thread(target=_d,daemon=True).start()
        else: speak("Shutdown cancelled.")
    ROOT.after(0,_c)

def feat_restart():
    def _c():
        if msgbox.askyesno("Restart","Restart now?",parent=ROOT):
            speak("Restarting in 5 seconds.")
            def _d():
                time.sleep(5)
                if IS_WINDOWS: os.system("shutdown /r /t 1")
                elif IS_LINUX: os.system("reboot")
                elif IS_MAC: os.system("sudo shutdown -r now")
            threading.Thread(target=_d,daemon=True).start()
        else: speak("Restart cancelled.")
    ROOT.after(0,_c)

def feat_logout():
    speak("Logging out."); time.sleep(1)
    if IS_WINDOWS: os.system("shutdown /l")
    elif IS_LINUX: os.system("pkill -KILL -u $USER")
    elif IS_MAC: os.system("osascript -e 'tell app \"System Events\" to log out'")

APP_MAP_WIN = {
    "notepad":"notepad","calculator":"calc","paint":"mspaint","explorer":"explorer",
    "task manager":"taskmgr","cmd":"start cmd","powershell":"start powershell",
    "word":"start winword","excel":"start excel","powerpoint":"start powerpnt",
    "vs code":"code","vscode":"code","spotify":"start spotify",
    "edge":"start msedge","firefox":"start firefox",
}
APP_MAP_LINUX = {
    "terminal":"x-terminal-emulator","files":"nautilus","gedit":"gedit",
    "calculator":"gnome-calculator","vs code":"code","vscode":"code",
    "firefox":"firefox","chrome":"google-chrome","vlc":"vlc","gimp":"gimp",
}

def feat_open_app(cmd):
    amap = APP_MAP_WIN if IS_WINDOWS else APP_MAP_LINUX
    for key,exe in amap.items():
        if key in cmd:
            speak(f"Opening {key}.")
            try:
                if IS_WINDOWS: os.system(exe)
                else: subprocess.Popen(exe.split())
            except Exception as e: err(f"Could not open {key}: {e}")
            return
    speak("App not found. Try: open notepad or open calculator.")

def feat_wikipedia(cmd):
    if not WIKI_AVAILABLE: speak("Run: pip install wikipedia"); return
    query=re.sub(r'\b(wikipedia|wiki|search|tell me about|who is|what is)\b','',cmd,flags=re.IGNORECASE).strip()
    if not query: query=ask_text("What to look up?")
    if not query: return
    speak(f"Looking up {query}.")
    try:
        wikipedia.set_lang("en")
        speak(wikipedia.summary(query,sentences=3,auto_suggest=False))
    except wikipedia.exceptions.DisambiguationError as e:
        speak(f"Too many results. Options: {', '.join(e.options[:3])}")
    except wikipedia.exceptions.PageError:
        try: speak(wikipedia.summary(query,sentences=3,auto_suggest=True))
        except Exception as e:
            logger.warning("Wikipedia fallback search failed for '%s': %s", query, e)
            speak(f"Couldn't find {query}.")
    except Exception as e:
        logger.warning("Wikipedia error for '%s': %s", query, e)
        speak(f"Wikipedia error: {e}")

def feat_define(cmd):
    word=re.sub(r'\b(define|definition|meaning of|what does|mean|dictionary)\b','',cmd,flags=re.IGNORECASE).strip()
    if not word: word=ask_text("Which word to define?")
    if not word: return
    if not REQUESTS_AVAILABLE: speak("Run: pip install requests"); return
    try:
        r=requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",timeout=6)
        if r.status_code==200: speak(f"{word}: {r.json()[0]['meanings'][0]['definitions'][0]['definition']}")
        else: speak(f"No definition found for {word}.")
    except Exception as e:
        logger.warning("Dictionary API error for '%s': %s", word, e)
        speak("Dictionary unavailable.")

def feat_weather(cmd=""):
    key=os.environ.get("OPENWEATHER_API_KEY","")
    if not key: speak("Needs OPENWEATHER_API_KEY env variable."); return
    city="Hyderabad"
    m=re.search(r'in\s+([A-Za-z ]+)$',cmd)
    if m: city=m.group(1).strip()
    try:
        d=requests.get(f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric",timeout=6).json()
        if d.get("cod")!=404:
            speak(f"{city}: {d['main']['temp']:.1f}°C, {d['weather'][0]['description']}, feels like {d['main']['feels_like']:.1f}°C, humidity {d['main']['humidity']}%.")
        else: speak(f"City {city} not found.")
    except Exception as e:
        logger.warning("Weather API error for '%s': %s", city, e)
        speak("Weather unavailable.")

def feat_news():
    key=os.environ.get("NEWS_API_KEY","")
    if not key: speak("Needs NEWS_API_KEY env variable."); return
    try:
        d=requests.get(f"https://newsapi.org/v2/top-headlines?country=in&apiKey={key}",timeout=6).json()
        if d.get("status")=="ok":
            speak("Top 3 headlines:")
            for i,a in enumerate(d.get("articles",[])[:3],1): speak(f"{i}: {a.get('title','No title')}")
        else: speak("Could not fetch news.")
    except Exception as e:
        logger.warning("News API error: %s", e)
        speak("News unavailable.")

def feat_joke():
    if JOKES_AVAILABLE:
        try: speak(pyjokes.get_joke()); return
        except Exception as e: logger.warning("pyjokes error: %s", e)
    speak(random.choice([
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "How many programmers to change a light bulb? None, that's a hardware problem.",
        "A SQL query walks into a bar and asks two tables: can I join you?",
        "Why did the developer go broke? He used up all his cache.",
        "I told my computer I needed a break. Now it keeps sending me Kit-Kat ads.",
    ]))

def feat_quote():
    if REQUESTS_AVAILABLE:
        try:
            r=requests.get("https://zenquotes.io/api/random",timeout=6)
            if r.status_code==200: d=r.json()[0]; speak(f"{d['q']} — {d['a']}"); return
        except Exception as e: logger.warning("Quote API error: %s", e)
    speak(random.choice([
        "The only way to do great work is to love what you do. — Steve Jobs",
        "In the middle of difficulty lies opportunity. — Albert Einstein",
        "It does not matter how slowly you go as long as you do not stop. — Confucius",
        "Code is like humour. When you have to explain it, it is bad. — Cory House",
    ]))

def feat_timer(cmd):
    m=re.search(r'(\d+)\s*(hour|hours|minute|minutes|second|seconds)',cmd)
    if not m:
        val=ask_text("Duration (e.g. 5 minutes):")
        if not val: return
        m=re.search(r'(\d+)\s*(hour|hours|minute|minutes|second|seconds)',val)
    if not m: speak("Specify a duration like 5 minutes."); return
    amount=int(m.group(1)); unit=m.group(2)
    secs=amount*3600 if 'hour' in unit else amount*60 if 'minute' in unit else amount
    speak(f"Timer set for {amount} {unit}.")
    def _r(): time.sleep(secs); speak(f"Timer done! {amount} {unit} passed.")
    threading.Thread(target=_r,daemon=True).start()

def feat_alarm(cmd):
    m=re.search(r'(\d{1,2})[:\s]?(\d{2})?\s*(am|pm)?',cmd,re.IGNORECASE)
    if not m:
        val=ask_text("Alarm time (e.g. 7 30 am):")
        if not val: return
        m=re.search(r'(\d{1,2})[:\s]?(\d{2})?\s*(am|pm)?',val,re.IGNORECASE)
    if not m: speak("Couldn't parse that time."); return
    hour=int(m.group(1)); minute=int(m.group(2) or 0); mer=(m.group(3) or '').lower()
    if mer=='pm' and hour!=12: hour+=12
    elif mer=='am' and hour==12: hour=0
    target=datetime.datetime.now().replace(hour=hour,minute=minute,second=0,microsecond=0)
    if target<=datetime.datetime.now(): target+=datetime.timedelta(days=1)
    speak(f"Alarm set for {target.strftime('%I:%M %p')}.")
    def _r(): time.sleep((target-datetime.datetime.now()).total_seconds()); speak(f"Alarm! It is {target.strftime('%I:%M %p')}!")
    threading.Thread(target=_r,daemon=True).start()

def feat_note():
    def _b():
        dlg=tk.Toplevel(ROOT); dlg.title("Quick Note"); dlg.geometry("520x340")
        dlg.configure(bg=C['bg1']); dlg.attributes('-topmost',True); dlg.grab_set()
        dlg.resizable(False,False); dlg.update_idletasks()
        x=(dlg.winfo_screenwidth()-520)//2; y=(dlg.winfo_screenheight()-340)//2
        dlg.geometry(f"520x340+{x}+{y}")
        tk.Label(dlg,text="Quick Note",font=("Helvetica Neue",13,"bold"),
                 fg=C['gold'],bg=C['bg1']).pack(pady=(14,6),anchor='w',padx=18)
        txt=tk.Text(dlg,height=10,width=58,font=FNT_MONO,bg=C['bg2'],fg=C['txt0'],
                    insertbackground=C['gold'],relief='flat',bd=4,padx=8,pady=6)
        txt.pack(padx=18,fill='both',expand=True); txt.focus()
        def save():
            content=txt.get("1.0",tk.END).strip()
            if content:
                fname=f"note_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                with open(fname,'w',encoding='utf-8') as f: f.write(content)
                speak(f"Note saved as {fname}")
            dlg.destroy()
        bf=tk.Frame(dlg,bg=C['bg1']); bf.pack(pady=10)
        _mk_btn(bf,"Save",save,C['gold'],C['bg0'],w=12).pack(side=tk.LEFT,padx=8)
        _mk_btn(bf,"Cancel",dlg.destroy,C['coral'],C['bg0'],w=12).pack(side=tk.LEFT,padx=8)
    ROOT.after(0,_b)

def feat_clipboard():
    try: c=ROOT.clipboard_get(); speak(f"Clipboard: {c[:100]}")
    except Exception: speak("Clipboard is empty.")

def feat_coin(): speak(f"Coin flip: {random.choice(['Heads','Tails'])}!")

def feat_dice(cmd):
    m=re.search(r'(\d+)',cmd); sides=max(2,int(m.group(1)) if m else 6)
    speak(f"Rolling a {sides}-sided die... you got {random.randint(1,sides)}!")

def feat_translate(cmd):
    text=re.sub(r'\b(translate|translation)\b','',cmd,flags=re.IGNORECASE).strip()
    speak("Opening Google Translate.")
    webbrowser.open(f"https://translate.google.com/?text={text}" if text else "https://translate.google.com")

def feat_list_files():
    items=os.listdir('.')
    files=[f for f in items if os.path.isfile(f)]; dirs=[f for f in items if os.path.isdir(f)]
    speak(f"{len(files)} files, {len(dirs)} folders.")
    info("Files: "+", ".join(files[:8])); info("Folders: "+", ".join(dirs[:6]))

def feat_volume(cmd):
    if not IS_WINDOWS: speak("Volume control is Windows only."); return
    try:
        from ctypes import cast,POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities,IAudioEndpointVolume
        devices=AudioUtilities.GetSpeakers()
        vol_ctrl=cast(devices.Activate(IAudioEndpointVolume._iid_,CLSCTX_ALL,None),POINTER(IAudioEndpointVolume))
        if "up" in cmd or "louder" in cmd:
            v=min(1.0,vol_ctrl.GetMasterVolumeLevelScalar()+0.1); vol_ctrl.SetMasterVolumeLevelScalar(v,None); speak(f"Volume: {int(v*100)}%.")
        elif "down" in cmd or "quieter" in cmd:
            v=max(0.0,vol_ctrl.GetMasterVolumeLevelScalar()-0.1); vol_ctrl.SetMasterVolumeLevelScalar(v,None); speak(f"Volume: {int(v*100)}%.")
        elif "mute"   in cmd: vol_ctrl.SetMute(1,None); speak("Muted.")
        elif "unmute" in cmd: vol_ctrl.SetMute(0,None); speak("Unmuted.")
        else: speak(f"Volume is {int(vol_ctrl.GetMasterVolumeLevelScalar()*100)}%.")
    except ImportError: speak("Run: pip install pycaw")
    except Exception as e: speak(f"Volume error: {e}")

def feat_help():
    q(_console_write,"""
PA COMMANDS
====================================================
WAKE        : say "hey pa" or "wake" → PA says "Hello Rushindhra!" → speak
             (if pvporcupine installed, say "porcupine")
TIME / DATE : what time is it / what is the date
OPEN SITES  : open youtube / gmail / github / reddit
SEARCH      : search python tutorials
YOUTUBE     : youtube lo-fi music
WIKIPEDIA   : wikipedia Elon Musk
DICTIONARY  : define serendipity
CALCULATOR  : calculate 25 times 4
SCREENSHOT  : take a screenshot
SYSTEM INFO : system info / cpu / ram / disk / battery
NETWORK     : network info / my ip / ping
LOCK/SLEEP  : lock screen / sleep
SHUTDOWN    : shutdown / restart / log out
APPS        : open notepad / calculator / vscode
VOLUME      : volume up / down / mute / unmute
TIMER       : set timer for 10 minutes
ALARM       : set alarm for 7 30 am
NOTE        : create note
CLIPBOARD   : clipboard
JOKE        : tell me a joke
QUOTE       : give me a quote
COIN / DICE : flip a coin / roll a dice
TRANSLATE   : translate hello world
FILES       : list files
EXIT        : goodbye / exit / quit
====================================================
""","info")
    speak("Commands shown in the console.")

def feat_greet():
    h=datetime.datetime.now().hour
    g="Good morning" if h<12 else "Good afternoon" if h<18 else "Good evening"
    if PORCUPINE_AVAILABLE and _porcupine_handle:
        speak(f"{g}! I am PA v{VERSION}. Say 'porcupine' to activate me, or type below.")
    else:
        speak(f"{g}! I am PA v{VERSION}. Say 'hey pa' to activate me, or type below.")

# ── DISPATCHER ────────────────────────────────────────────────────────────────
def dispatch(cmd):
    c=cmd.lower().strip()
    set_status(f"Processing: {c[:38]}...",C['violet'])
    T=threading.Thread
    if   re.search(r'\b(time|clock)\b',c) and 'timer' not in c: feat_time()
    elif re.search(r'\bdate\b',c):           feat_date()
    elif 'chrome' in c and 'open' in c:      T(target=feat_open_chrome,daemon=True).start();return
    elif re.search(r'\bopen\b',c):
        is_site=any(k in c for k in SITES); is_app=any(k in c for k in (APP_MAP_WIN if IS_WINDOWS else APP_MAP_LINUX))
        if is_site:  T(target=feat_open_site,args=(c,),daemon=True).start();return
        elif is_app: T(target=feat_open_app,args=(c,),daemon=True).start();return
        else: feat_open_site(c)
    elif re.search(r'\b(email|gmail)\b',c):  T(target=feat_open_email,daemon=True).start();return
    elif re.search(r'\byoutube\b',c):        feat_youtube_search(c)
    elif re.search(r'\b(search|google|look up|find)\b',c): feat_google_search(c)
    elif re.search(r'\b(calculate|compute|evaluate|solve)\b',c): feat_calculate(c)
    elif 'screenshot' in c:                  T(target=feat_screenshot,daemon=True).start();return
    elif re.search(r'\bsystem info\b',c):    T(target=feat_system_info,daemon=True).start();return
    elif re.search(r'\b(battery|power)\b',c) and 'lock' not in c: T(target=feat_battery,daemon=True).start();return
    elif re.search(r'\bcpu\b',c):            T(target=feat_cpu,daemon=True).start();return
    elif re.search(r'\b(ram|memory)\b',c):   T(target=feat_ram,daemon=True).start();return
    elif re.search(r'\bdisk\b',c):           T(target=feat_disk,daemon=True).start();return
    elif re.search(r'\bprocess',c):          T(target=feat_processes,daemon=True).start();return
    elif re.search(r'\b(network info|hostname|local ip)\b',c): T(target=feat_network,daemon=True).start();return
    elif re.search(r'\b(my ip|public ip)\b',c): T(target=feat_public_ip,daemon=True).start();return
    elif re.search(r'\bping\b',c):           T(target=feat_ping,daemon=True).start();return
    elif re.search(r'\b(lock screen|lock computer|lock pc)\b',c): T(target=feat_lock,daemon=True).start();return
    elif re.search(r'\b(sleep|hibernate)\b',c): T(target=feat_sleep,daemon=True).start();return
    elif re.search(r'\b(shutdown|shut down)\b',c): feat_shutdown();return
    elif re.search(r'\b(restart|reboot)\b',c):     feat_restart();return
    elif re.search(r'\b(log out|logout|sign out)\b',c): T(target=feat_logout,daemon=True).start();return
    elif re.search(r'\b(wikipedia|wiki)\b',c): T(target=feat_wikipedia,args=(c,),daemon=True).start();return
    elif re.search(r'\b(define|definition|meaning|dictionary)\b',c): T(target=feat_define,args=(c,),daemon=True).start();return
    elif re.search(r'\b(weather|temperature)\b',c): T(target=feat_weather,args=(c,),daemon=True).start();return
    elif re.search(r'\b(news|headlines)\b',c): T(target=feat_news,daemon=True).start();return
    elif re.search(r'\bvolume\b',c):         T(target=feat_volume,args=(c,),daemon=True).start();return
    elif re.search(r'\b(alarm|set alarm)\b',c): T(target=feat_alarm,args=(c,),daemon=True).start();return
    elif re.search(r'\b(timer|remind me|countdown)\b',c): T(target=feat_timer,args=(c,),daemon=True).start();return
    elif re.search(r'\b(note|create note|new note)\b',c): ROOT.after(0,feat_note);return
    elif re.search(r'\b(clipboard|paste)\b',c): feat_clipboard()
    elif re.search(r'\bjoke\b',c):           T(target=feat_joke,daemon=True).start();return
    elif re.search(r'\b(quote|inspire)\b',c):T(target=feat_quote,daemon=True).start();return
    elif re.search(r'\b(flip|coin)\b',c):    feat_coin()
    elif re.search(r'\b(roll|dice)\b',c):    feat_dice(c)
    elif re.search(r'\btranslate\b',c):      T(target=feat_translate,args=(c,),daemon=True).start();return
    elif re.search(r'\b(list files|show files|files)\b',c): T(target=feat_list_files,daemon=True).start();return
    elif re.search(r'\b(hello|hi)\b',c):     speak("Hello! How can I help you?")
    elif re.search(r'\bhow are you\b',c):    speak("Running perfectly! What can I do for you?")
    elif re.search(r'\b(who are you|your name)\b',c): speak(f"I am PA v{VERSION}.")
    elif re.search(r'\b(thank|thanks)\b',c): speak("You are welcome! Anything else?")
    elif re.search(r'\b(help|what can you do|commands)\b',c): feat_help()
    elif re.search(r'\b(bye|exit|quit|goodbye|close)\b',c):
        speak("Goodbye! Have a wonderful day!"); ROOT.after(2200,ROOT.quit)
    else: speak("I did not understand. Say help to see all commands.")
    set_status("Waiting for wake word...",C['txt2'])

# ── CONTROLLER ────────────────────────────────────────────────────────────────
_running      = False
_running_lock = threading.Lock()   # protects _running across threads
_loop_thr     = None

def _is_running() -> bool:
    with _running_lock:
        return _running

def _set_running(value: bool) -> None:
    global _running
    with _running_lock:
        _running = value

def start_pa():
    global _loop_thr
    with _running_lock:
        global _running
        if _running:
            return
        _running = True
    q(start_btn.config, state=tk.DISABLED, bg=C['txt2'])
    q(stop_btn.config,  state=tk.NORMAL,   bg=C['coral'])
    _loop_thr = threading.Thread(target=_main_loop, daemon=True)
    _loop_thr.start()

def stop_pa():
    _set_running(False)
    start_btn.config(state=tk.NORMAL,   bg=C['mint'])
    stop_btn.config( state=tk.DISABLED, bg=C['txt2'])
    set_wake_led('idle')
    set_status("Stopped", C['gold'])
    warn("PA stopped. Click Start to resume.")

def _main_loop():
    feat_greet()

    if not _mic_available():
        warn("No mic. Run: pip install sounddevice numpy")
        set_status("No mic — use text input", C['orange'])
        q(start_btn.config, state=tk.NORMAL,   bg=C['mint'])
        q(stop_btn.config,  state=tk.DISABLED, bg=C['txt2'])
        _set_running(False)
        return

    # Calibrate ONCE here — not inside any recording function
    if SOUNDDEVICE_AVAILABLE:
        _calibrate_sounddevice()

    # Try to load pvporcupine offline wake word engine
    if PORCUPINE_AVAILABLE:
        _init_porcupine()

    if _porcupine_handle:
        info("pvporcupine active — say 'porcupine' to wake PA.")
    else:
        info('Google Speech wake word active — say "hey pa" to wake PA.')

    while _is_running():
        set_status("Waiting for wake word...", C['txt2'])
        set_wake_led('scanning')
        q(_console_write, "\n  Listening for wake word...\n", "dim")

        woke = False
        while _is_running():
            result = scan_once()
            if result == "no_mic":
                warn("Microphone disconnected.")
                _set_running(False)
                q(start_btn.config, state=tk.NORMAL,   bg=C['mint'])
                q(stop_btn.config,  state=tk.DISABLED, bg=C['txt2'])
                break
            if result == "woke":
                set_wake_led('heard')
                q(_console_write, "  Wake word detected!\n", "ok")
                _tts_q.put("Hello Rushindhra!")
                q(_console_write, "[PA] Hello Rushindhra!\n", "pa")
                woke = True; break

        if not _is_running(): break
        if not woke: continue

        _tts_q.join()
        set_status("Listening for command...", C['coral'])
        set_wake_led('listening')
        q(_console_write, "  Listening for command...\n", "dim")

        command = capture_voice(duration=COMMAND_DURATION_SEC, wake_scan=False)
        if not _is_running(): break

        if command and command != "NO_MIC":
            user_echo(command); dispatch(command)
        elif command == "NO_MIC":
            warn("Microphone unavailable.")
        else:
            speak("I did not catch that. Please try again.")

    set_wake_led('idle')
    set_status("PA stopped.", C['gold'])

# ── GUI HELPERS ───────────────────────────────────────────────────────────────
def _mk_btn(parent, text, cmd, bg, fg=None, w=20):
    return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg or C['bg0'],
                     font=FNT_BTN, relief='flat', width=w, height=1, cursor='hand2',
                     activebackground=C['bg4'], activeforeground=C['txt0'], bd=0, padx=4)

def _section_label(parent, text):
    frm=tk.Frame(parent,bg=C['bg1']); frm.pack(fill='x',padx=10,pady=(10,2))
    tk.Label(frm,text=f"  {text}",font=("Helvetica Neue",7,"bold"),
             fg=C['txt2'],bg=C['bg1'],anchor='w').pack(fill='x')
    tk.Frame(frm,bg=C['border'],height=1).pack(fill='x',pady=(2,0))

def _side_btn(parent, text, cmd, color=None):
    b=tk.Button(parent,text=text,command=cmd,bg=color or C['bg3'],fg=C['txt1'],
                font=("Helvetica Neue",8,"bold"),relief='flat',anchor='w',
                cursor='hand2',width=24,padx=10,pady=3,
                activebackground=C['bg4'],activeforeground=C['txt0'])
    b.pack(fill='x',padx=10,pady=1); return b

def qr(fn, *args): threading.Thread(target=fn, args=args, daemon=True).start()

def _do_oneshot_voice():
    def _r():
        if not _mic_available(): err("Run: pip install sounddevice numpy"); return
        set_status("Listening...", C['coral'])
        result = capture_voice(duration=6, wake_scan=False)
        if result and result != "NO_MIC": user_echo(result); dispatch(result)
        elif result == "NO_MIC": err("No mic backend.")
        else: warn("Nothing heard."); set_status("Ready", C['mint'])
    threading.Thread(target=_r, daemon=True).start()

def _do_text_input():
    def _r():
        cmd=ask_text("Enter your command:")
        if cmd and cmd.strip(): user_echo(cmd); dispatch(cmd.lower().strip())
    threading.Thread(target=_r, daemon=True).start()

def _do_calc_prompt():
    def _r():
        expr=ask_text("Enter expression (e.g. 25 * 4 + 10):","Calculator")
        if expr and expr.strip(): feat_calculate(f"calculate {expr}")
    threading.Thread(target=_r, daemon=True).start()

def _do_wiki_prompt():
    def _r():
        query=ask_text("Search Wikipedia:","Wikipedia")
        if query and query.strip(): feat_wikipedia(f"wikipedia {query}")
    threading.Thread(target=_r, daemon=True).start()

def _do_define_prompt():
    def _r():
        word=ask_text("Define which word?","Dictionary")
        if word and word.strip(): feat_define(f"define {word}")
    threading.Thread(target=_r, daemon=True).start()

def _do_timer_prompt():
    def _r():
        val=ask_text("Timer duration (e.g. 5 minutes):","Timer")
        if val and val.strip(): feat_timer(f"set timer for {val}")
    threading.Thread(target=_r, daemon=True).start()

def _do_alarm_prompt():
    def _r():
        val=ask_text("Alarm time (e.g. 7 30 am):","Alarm")
        if val and val.strip(): feat_alarm(f"set alarm for {val}")
    threading.Thread(target=_r, daemon=True).start()

def _do_youtube_search():
    def _r():
        qs=ask_text("Search YouTube for:","YouTube")
        if qs: feat_youtube_search(f"youtube {qs}")
    threading.Thread(target=_r, daemon=True).start()

def _do_google_search():
    def _r():
        qs=ask_text("Search Google for:","Google Search")
        if qs: feat_google_search(f"search {qs}")
    threading.Thread(target=_r, daemon=True).start()

# ── BUILD GUI ─────────────────────────────────────────────────────────────────
ROOT=tk.Tk()
ROOT.title(f"PA — Personal Assistant v{VERSION}")
ROOT.geometry("1060x760"); ROOT.configure(bg=C['bg0']); ROOT.resizable(True,True)
ROOT.update_idletasks()
sw,sh=ROOT.winfo_screenwidth(),ROOT.winfo_screenheight()
ROOT.geometry(f"1060x760+{(sw-1060)//2}+{(sh-760)//2}")

tk.Frame(ROOT,bg=C['gold'],height=3).pack(fill='x',side='top')
hdr=tk.Frame(ROOT,bg=C['bg0']); hdr.pack(fill='x')
hdr_left=tk.Frame(hdr,bg=C['bg0']); hdr_left.pack(side=tk.LEFT,padx=20,pady=10)
tk.Label(hdr_left,text="PA",font=("Helvetica Neue",36,"bold"),fg=C['gold'],bg=C['bg0']).pack(side=tk.LEFT)
tk.Label(hdr_left,text=f"  Personal Assistant  v{VERSION}",font=("Helvetica Neue",11),fg=C['txt2'],bg=C['bg0']).pack(side=tk.LEFT,pady=(12,0))
hdr_right=tk.Frame(hdr,bg=C['bg0']); hdr_right.pack(side=tk.RIGHT,padx=20)
wake_led=tk.Label(hdr_right,text="IDLE",font=("Helvetica Neue",9,"bold"),fg=C['txt2'],bg=C['bg0'])
wake_led.pack(anchor='e')
clock_var=tk.StringVar(value="")
tk.Label(hdr_right,textvariable=clock_var,font=("Courier New",9),fg=C['txt2'],bg=C['bg0']).pack(anchor='e')
tk.Label(hdr,text='Say "hey pa" or "wake" to activate  |  or type below',font=("Helvetica Neue",9,"italic"),fg=C['gold_dim'],bg=C['bg0']).pack(side=tk.LEFT,padx=6)
def _tick(): clock_var.set(datetime.datetime.now().strftime("  %a %b %d  %H:%M:%S")); ROOT.after(1000,_tick)
_tick()

tk.Frame(ROOT,bg=C['border'],height=1).pack(fill='x')
sbar=tk.Frame(ROOT,bg=C['bg1'],height=24); sbar.pack(fill='x')
status_var=tk.StringVar(value="Initialising...")
status_lbl=tk.Label(sbar,textvariable=status_var,font=("Helvetica Neue",8),fg=C['teal'],bg=C['bg1'],anchor='w',padx=14)
status_lbl.pack(side=tk.LEFT)
for label,ok in [("TTS",TTS_AVAILABLE),("Porc",PORCUPINE_AVAILABLE),("SD",SOUNDDEVICE_AVAILABLE),
                 ("SR",SR_AVAILABLE),("psutil",PSUTIL_AVAILABLE),("wiki",WIKI_AVAILABLE)]:
    tk.Label(sbar,text=label,font=("Helvetica Neue",7,"bold"),
             fg=C['mint'] if ok else C['coral'],bg=C['bg1']).pack(side=tk.RIGHT,padx=4)
tk.Label(sbar,text="  libs: ",font=("Helvetica Neue",7),fg=C['txt2'],bg=C['bg1']).pack(side=tk.RIGHT)
tk.Frame(ROOT,bg=C['border'],height=1).pack(fill='x')

body=tk.Frame(ROOT,bg=C['bg0']); body.pack(fill='both',expand=True)
sidebar=tk.Frame(body,bg=C['bg1'],width=220); sidebar.pack(side=tk.LEFT,fill='y'); sidebar.pack_propagate(False)
sb_canvas=tk.Canvas(sidebar,bg=C['bg1'],highlightthickness=0,bd=0); sb_canvas.pack(side=tk.LEFT,fill='both',expand=True)
sb_scroll=tk.Scrollbar(sidebar,orient='vertical',command=sb_canvas.yview); sb_scroll.pack(side=tk.RIGHT,fill='y')
sb_canvas.configure(yscrollcommand=sb_scroll.set)
sb_inner=tk.Frame(sb_canvas,bg=C['bg1'])
sb_win=sb_canvas.create_window((0,0),window=sb_inner,anchor='nw')
def _sb_cfg(e): sb_canvas.configure(scrollregion=sb_canvas.bbox("all")); sb_canvas.itemconfig(sb_win,width=e.width)
sb_inner.bind('<Configure>',_sb_cfg)
sb_canvas.bind('<Configure>',lambda e:sb_canvas.itemconfig(sb_win,width=e.width))
sb_canvas.bind_all("<MouseWheel>",lambda e:sb_canvas.yview_scroll(int(-1*(e.delta/120)),"units"))

_section_label(sb_inner,"CONTROL")
start_btn=_mk_btn(sb_inner,"  Start PA",start_pa,C['mint'],C['bg0'],w=22); start_btn.pack(fill='x',padx=10,pady=2)
stop_btn =_mk_btn(sb_inner,"  Stop PA", stop_pa, C['txt2'],'white',  w=22); stop_btn.pack(fill='x',padx=10,pady=2)
stop_btn.config(state=tk.DISABLED)
voice_row=tk.Frame(sb_inner,bg=C['bg1']); voice_row.pack(fill='x',padx=10,pady=2)
for txt,cmd,bg in [("Mic Voice",_do_oneshot_voice,C['coral']),("Text Input",_do_text_input,C['teal'])]:
    tk.Button(voice_row,text=txt,command=cmd,bg=bg,fg=C['bg0'],font=("Helvetica Neue",8,"bold"),
              relief='flat',cursor='hand2',padx=6,pady=4,activebackground=C['bg4'],
              activeforeground=C['txt0']).pack(side=tk.LEFT,expand=True,fill='x',padx=1)
_side_btn(sb_inner,"Test Voice",lambda:qr(lambda:speak("Hello! PA voice is working perfectly.")),C['bg3'])

_section_label(sb_inner,"TIME & DATE")
_side_btn(sb_inner,"Current Time",lambda:qr(feat_time))
_side_btn(sb_inner,"Current Date",lambda:qr(feat_date))
_side_btn(sb_inner,"Date & Time", lambda:qr(feat_datetime))

_section_label(sb_inner,"WEB & SOCIAL")
_side_btn(sb_inner,"Google Search",  _do_google_search)
_side_btn(sb_inner,"YouTube Search", _do_youtube_search)
_side_btn(sb_inner,"Open YouTube",   lambda:qr(lambda:(speak("Opening YouTube."),webbrowser.open("https://www.youtube.com"))))
_side_btn(sb_inner,"LinkedIn",       lambda:qr(lambda:(speak("Opening LinkedIn."),webbrowser.open("https://linkedin.com"))))
_side_btn(sb_inner,"GitHub",         lambda:qr(lambda:(speak("Opening GitHub."),webbrowser.open("https://github.com"))))
_side_btn(sb_inner,"Gmail / Email",  lambda:qr(feat_open_email))
_side_btn(sb_inner,"Chrome",         lambda:qr(feat_open_chrome))
_side_btn(sb_inner,"WhatsApp Web",   lambda:qr(lambda:(speak("Opening WhatsApp."),webbrowser.open("https://web.whatsapp.com"))))
_side_btn(sb_inner,"Spotify",        lambda:qr(lambda:(speak("Opening Spotify."),webbrowser.open("https://open.spotify.com"))))
_side_btn(sb_inner,"Discord",        lambda:qr(lambda:(speak("Opening Discord."),webbrowser.open("https://discord.com/app"))))
_side_btn(sb_inner,"Instagram",      lambda:qr(lambda:(speak("Opening Instagram."),webbrowser.open("https://instagram.com"))))

_section_label(sb_inner,"SYSTEM INFO")
_side_btn(sb_inner,"System Info",  lambda:qr(feat_system_info))
_side_btn(sb_inner,"Battery",      lambda:qr(feat_battery))
_side_btn(sb_inner,"CPU Usage",    lambda:qr(feat_cpu))
_side_btn(sb_inner,"RAM Usage",    lambda:qr(feat_ram))
_side_btn(sb_inner,"Disk Usage",   lambda:qr(feat_disk))
_side_btn(sb_inner,"Processes",    lambda:qr(feat_processes))
_side_btn(sb_inner,"Network Info", lambda:qr(feat_network))
_side_btn(sb_inner,"Public IP",    lambda:qr(feat_public_ip))
_side_btn(sb_inner,"Ping Test",    lambda:qr(feat_ping))

_section_label(sb_inner,"POWER")
_side_btn(sb_inner,"Lock Screen",     lambda:qr(feat_lock),  C['bg3'])
_side_btn(sb_inner,"Sleep / Suspend", lambda:qr(feat_sleep), C['bg3'])
_side_btn(sb_inner,"Restart",         feat_restart,          C['bg3'])
_side_btn(sb_inner,"Log Out",         lambda:qr(feat_logout),C['bg3'])
_side_btn(sb_inner,"Shutdown",        feat_shutdown,         C['bg3'])

_section_label(sb_inner,"TOOLS")
_side_btn(sb_inner,"Calculator",_do_calc_prompt)
_side_btn(sb_inner,"Screenshot", lambda:qr(feat_screenshot))
_side_btn(sb_inner,"Set Timer",  _do_timer_prompt)
_side_btn(sb_inner,"Set Alarm",  _do_alarm_prompt)
_side_btn(sb_inner,"Quick Note", lambda:ROOT.after(0,feat_note))
_side_btn(sb_inner,"Clipboard",  feat_clipboard)
_side_btn(sb_inner,"Volume",     lambda:qr(lambda:feat_volume("status")))

_section_label(sb_inner,"KNOWLEDGE")
_side_btn(sb_inner,"Wikipedia",  _do_wiki_prompt)
_side_btn(sb_inner,"Dictionary", _do_define_prompt)
_side_btn(sb_inner,"Weather",    lambda:qr(feat_weather))
_side_btn(sb_inner,"News",       lambda:qr(feat_news))
_side_btn(sb_inner,"Translate",  lambda:(lambda t:feat_translate(f"translate {t}") if t else None)(ask_text("Text to translate:","Translate")))

_section_label(sb_inner,"FUN")
_side_btn(sb_inner,"Tell a Joke",lambda:qr(feat_joke))
_side_btn(sb_inner,"Inspire Me", lambda:qr(feat_quote))
_side_btn(sb_inner,"Flip a Coin",feat_coin)
_side_btn(sb_inner,"Roll a Dice",lambda:feat_dice("6"))

_section_label(sb_inner,"ACTIONS")
_side_btn(sb_inner,"List Files",      lambda:qr(feat_list_files))
_side_btn(sb_inner,"Help / Commands", feat_help,C['violet'])
_side_btn(sb_inner,"Clear Console",
          lambda:(console.config(state=tk.NORMAL),console.delete('1.0',tk.END),console.config(state=tk.DISABLED)),C['bg3'])

tk.Frame(body,bg=C['border'],width=1).pack(side=tk.LEFT,fill='y')
right=tk.Frame(body,bg=C['bg0']); right.pack(side=tk.LEFT,fill='both',expand=True)
con_hdr=tk.Frame(right,bg=C['bg1'],height=30); con_hdr.pack(fill='x'); con_hdr.pack_propagate(False)
tk.Label(con_hdr,text="  PA CONSOLE",font=("Helvetica Neue",9,"bold"),fg=C['teal'],bg=C['bg1']).pack(side=tk.LEFT,padx=4,pady=5)
tk.Label(con_hdr,text=f"{platform.system()} {platform.release()} · Python {platform.python_version()}  ",
         font=("Helvetica Neue",8),fg=C['txt2'],bg=C['bg1']).pack(side=tk.RIGHT,pady=5)
con_frame=tk.Frame(right,bg=C['bg0']); con_frame.pack(fill='both',expand=True)
console=tk.Text(con_frame,font=FNT_MONO,bg=C['bg0'],fg=C['txt1'],insertbackground=C['gold'],
                relief='flat',bd=0,wrap=tk.WORD,padx=16,pady=10,
                selectbackground=C['gold'],selectforeground=C['bg0'],state=tk.DISABLED)
console.pack(side=tk.LEFT,fill='both',expand=True)
con_scroll=tk.Scrollbar(con_frame,orient='vertical',command=console.yview,bg=C['bg1'],troughcolor=C['bg0'])
con_scroll.pack(side=tk.RIGHT,fill='y'); console.configure(yscrollcommand=con_scroll.set)
for tag,fg in [("pa",C['teal']),("user",C['gold']),("heard",C['violet']),("info",C['txt2']),
               ("warn",C['orange']),("err",C['coral']),("ok",C['mint']),("dim",C['bg4']),("normal",C['txt1'])]:
    console.tag_configure(tag,foreground=fg)

ibar=tk.Frame(right,bg=C['bg1'],height=44); ibar.pack(fill='x',side='bottom'); ibar.pack_propagate(False)
tk.Frame(right,bg=C['border'],height=1).pack(fill='x',side='bottom')
tk.Label(ibar,text="  >",font=("Courier New",16,"bold"),fg=C['gold'],bg=C['bg1']).pack(side=tk.LEFT,padx=(8,2))
PLACEHOLDER="Type a command and press Enter..."
ivar=tk.StringVar()
ientry=tk.Entry(ibar,textvariable=ivar,font=("Courier New",10),bg=C['bg2'],fg=C['txt0'],
                insertbackground=C['gold'],relief='flat',bd=4,highlightthickness=1,
                highlightcolor=C['teal'],highlightbackground=C['border'])
ientry.pack(side=tk.LEFT,fill='both',expand=True,padx=4,pady=7)
ientry.insert(0,PLACEHOLDER); ientry.config(fg=C['txt2'])
ientry.bind('<FocusIn>',  lambda e:(ientry.delete(0,tk.END),ientry.config(fg=C['txt0'])) if ientry.get()==PLACEHOLDER else None)
ientry.bind('<FocusOut>', lambda e:(ientry.insert(0,PLACEHOLDER),ientry.config(fg=C['txt2'])) if not ientry.get() else None)
def _submit(e=None):
    cmd=ivar.get().strip()
    if cmd and cmd!=PLACEHOLDER:
        ientry.delete(0,tk.END); user_echo(cmd)
        threading.Thread(target=dispatch,args=(cmd.lower(),),daemon=True).start()
ientry.bind('<Return>',_submit)
_mk_btn(ibar,"Send",_submit,C['gold'],C['bg0'],w=9).pack(side=tk.RIGHT,padx=8,pady=7)

# ── BOOT MESSAGE ──────────────────────────────────────────────────────────────
def _boot_msg():
    _console_write("╔══════════════════════════════════════════════════╗\n","ok")
    _console_write("║      PA — Personal Assistant  v2.3               ║\n","ok")
    _console_write("║      Wake: pvporcupine (offline) + Google fallback║\n","ok")
    _console_write("╚══════════════════════════════════════════════════╝\n\n","ok")
    _console_write(f"  Platform : {platform.system()} {platform.release()}\n","info")
    _console_write(f"  Python   : {platform.python_version()}\n\n","info")
    for label,ok,fix in [
        ("SR",           SR_AVAILABLE,           "pip install SpeechRecognition"),
        ("sounddevice",  SOUNDDEVICE_AVAILABLE,   "pip install sounddevice numpy"),
        ("pvporcupine",  PORCUPINE_AVAILABLE,     "pip install pvporcupine  (optional offline wake word)"),
        ("TTS",          TTS_AVAILABLE,           "pip install pyttsx3"),
        ("psutil",       PSUTIL_AVAILABLE,        "pip install psutil"),
        ("wikipedia",    WIKI_AVAILABLE,          "pip install wikipedia"),
        ("pyautogui",    PYAUTOGUI_AVAILABLE,     "pip install pyautogui"),
        ("requests",     REQUESTS_AVAILABLE,      "pip install requests"),
    ]:
        _console_write(f"  {label:<16}: {'Ready' if ok else ('optional — '+fix if 'optional' in fix else 'MISSING — '+fix)}\n",
                       "ok" if ok else ("info" if "optional" in fix else "warn"))
    if not SOUNDDEVICE_AVAILABLE:
        _console_write("\n  VOICE DISABLED — run: pip install sounddevice numpy\n","err")
    elif PORCUPINE_AVAILABLE:
        _console_write('\n  Say "porcupine" → PA says "Hello Rushindhra!" → speak your command\n',"normal")
        _console_write('  (For custom "hey pa" keyword: https://console.picovoice.ai)\n',"info")
    else:
        _console_write('\n  Say "hey pa" or "wake" → PA says "Hello Rushindhra!" → speak\n',"normal")
    _console_write("  Or type in the bar below and press Enter\n","normal")
    _console_write("  Click Help / Commands to see all commands\n\n","normal")

_boot_msg()
set_status("Ready", C['mint'])
ROOT.after(40, flush_gui)
ROOT.mainloop()
_tts_q.put(None)