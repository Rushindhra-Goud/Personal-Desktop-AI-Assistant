import speech_recognition as sr
import pyttsx3
import datetime
import webbrowser
import os
import wikipedia
import pywhatkit
import random
import tkinter as tk
import requests
import pyjokes
import threading
import psutil
import platform
import subprocess
import json
import socket
import urllib.request
import smtplib
from email.mime.text import MIMEText
import time
import winsound  # For Windows beep sounds

# Optional: alternative audio capture when PyAudio is unavailable
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Check if PyAudio is available
PYAUDIO_AVAILABLE = False
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False


# Voice engine setup
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    if voices:
        engine.setProperty('voice', voices[0].id)  # Use first available voice
    engine.setProperty('rate', 170)
    TTS_AVAILABLE = True
except Exception as e:
    print(f"TTS engine initialization failed: {e}")
    TTS_AVAILABLE = False
    engine = None

# Speak function
def speak(text):
    output_text.insert(tk.END, "Assistant: " + text + "\n")
    output_text.see(tk.END)  # Auto-scroll to bottom

    if TTS_AVAILABLE and engine:
        try:
            # Run TTS in a separate thread to avoid blocking GUI
            def tts_thread():
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    output_text.insert(tk.END, f"[TTS Error: {e}]\n")
                    output_text.see(tk.END)

            threading.Thread(target=tts_thread, daemon=True).start()
        except Exception as e:
            output_text.insert(tk.END, f"[TTS Error: {e}]\n")
            output_text.see(tk.END)
    else:
        output_text.insert(tk.END, "[Text-to-speech not available]\n")
        output_text.see(tk.END)


# Greeting
def greet():
    hour = datetime.datetime.now().hour

    if hour < 12:
        speak("Good Morning")
    elif hour < 18:
        speak("Good Afternoon")
    else:
        speak("Good Evening")

    speak("I am your personal desktop assistant.")

# Voice recognition (with GUI text input fallback)
def take_command():
    """Get command from user - voice first, then GUI text input"""
    try:
        # Try voice input with sounddevice
        if SOUNDDEVICE_AVAILABLE:
            output_text.insert(tk.END, "🎤 Listening... (3 seconds)\n")
            output_text.see(tk.END)

            # Record for 3 seconds
            recording = sd.rec(int(3 * 16000), samplerate=16000, channels=1, dtype='int16')
            sd.wait()

            # Convert to speech recognition format
            audio_data = sr.AudioData(recording.tobytes(), 16000, 2)
            command = sr.Recognizer().recognize_google(audio_data)

            output_text.insert(tk.END, f"🎯 Heard: {command}\n")
            output_text.see(tk.END)
            return command.lower()

    except Exception as e:
        # Voice failed, show error and use text input
        output_text.insert(tk.END, f"🎤 Audio failed: {str(e)[:50]}...\n")
        output_text.insert(tk.END, "✍️ Opening text input dialog...\n")
        output_text.see(tk.END)

    # Use GUI text input dialog
    command = gui_text_input()
    if command:
        output_text.insert(tk.END, f"✍️ You typed: {command}\n")
        output_text.see(tk.END)
        return command.lower()

    return "none"

def gui_text_input(prompt="🎤 Voice failed - please type your command:"):
    """Create a GUI dialog for text input"""
    dialog = tk.Toplevel(window)
    dialog.title("Enter Command")
    dialog.geometry("400x140")
    dialog.attributes('-topmost', True)
    dialog.resizable(False, False)
    dialog.configure(bg='#34495E')

    # Center the dialog
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - (400 // 2)
    y = (dialog.winfo_screenheight() // 2) - (140 // 2)
    dialog.geometry(f"400x140+{x}+{y}")

    tk.Label(dialog, text=prompt, font=("Arial", 11), fg='white', bg='#34495E').pack(pady=10)

    entry_var = tk.StringVar()
    entry = tk.Entry(dialog, textvariable=entry_var, width=40, font=("Arial", 10),
                    bg='#ECF0F1', fg='#2C3E50', insertbackground='#2C3E50')
    entry.pack(pady=5)
    entry.focus()

    result = [None]

    def on_submit():
        result[0] = entry_var.get().strip()
        dialog.destroy()

    def on_cancel():
        result[0] = None
        dialog.destroy()

    # Bind Enter key to submit
    entry.bind('<Return>', lambda e: on_submit())

    button_frame = tk.Frame(dialog, bg='#34495E')
    button_frame.pack(pady=10)

    tk.Button(button_frame, text="Submit", command=on_submit, width=10, bg='#27AE60', fg='white').pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Cancel", command=on_cancel, width=10, bg='#E74C3C', fg='white').pack(side=tk.RIGHT, padx=5)

    # Wait for dialog
    window.wait_window(dialog)

    return result[0]

# Time
def tell_time():
    time = datetime.datetime.now().strftime("%H:%M")
    speak("The current time is " + time)

# Date
def tell_date():
    today = datetime.date.today()
    speak("Today's date is " + str(today))

# Wikipedia
def search_wikipedia(command):

    speak("Searching Wikipedia")

    command = command.replace("wikipedia", "")

    try:
        result = wikipedia.summary(command, sentences=2)
        speak(result)
    except:
        speak("Sorry I couldn't find information")

# Google Search
def google_search(command):

    speak("Searching Google")

    command = command.replace("search", "")

    webbrowser.open("https://www.google.com/search?q=" + command)

# Open Websites
def open_website(command):

    if "youtube" in command:
        speak("Opening YouTube")
        webbrowser.open("https://youtube.com")

    elif "google" in command:
        speak("Opening Google")
        webbrowser.open("https://google.com")

    elif "gmail" in command:
        speak("Opening Gmail")
        webbrowser.open("https://mail.google.com")

# Play Video
def play_video(command):

    command = command.replace("play", "")
    speak("Playing " + command)

    pywhatkit.playonyt(command)

# Tell Joke
def tell_joke():

    joke = pyjokes.get_joke()
    speak(joke)

# Weather
def weather():

    city = "Hyderabad"
    api = "https://api.openweathermap.org/data/2.5/weather?q="+city+"&appid=YOUR_API_KEY"

    try:
        data = requests.get(api).json()

        temp = int(data["main"]["temp"] - 273)

        speak("Current temperature is " + str(temp) + " degree celsius")

    except:
        speak("Weather information not available")

# Open Applications
def open_app(command):

    if "notepad" in command:
        os.system("notepad")

    elif "calculator" in command:
        os.system("calc")

    elif "chrome" in command:
        os.system("start chrome")

# Shutdown
def shutdown():

    speak("Shutting down the computer")
    os.system("shutdown /s /t 1")

# Restart
def restart():

    speak("Restarting the computer")
    os.system("shutdown /r /t 1")

# System Information
def system_info():
    """Get system information"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        info = f"CPU Usage: {cpu_percent}%. Memory: {memory.percent}%. Disk: {disk.percent}%."
        speak(info)
    except:
        speak("Unable to retrieve system information")

# Battery Status
def battery_status():
    """Get battery information"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            plugged = "plugged in" if battery.power_plugged else "not plugged in"
            speak(f"Battery is at {percent} percent and {plugged}")
        else:
            speak("No battery detected")
    except:
        speak("Unable to check battery status")

# Network Information
def network_info():
    """Get network information"""
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        speak(f"Your computer name is {hostname} and IP address is {ip_address}")
    except:
        speak("Unable to retrieve network information")

# Calculator
def calculate(command):
    """Simple calculator function"""
    try:
        # Remove calculator keywords
        expression = command.replace("calculate", "").replace("compute", "").replace("what is", "").strip()

        # Basic safety check
        if any(char in expression for char in ['import', 'exec', 'eval', '__']):
            speak("Sorry, I cannot execute that calculation for security reasons")
            return

        result = eval(expression)
        speak(f"The result of {expression} is {result}")
    except:
        speak("Sorry, I couldn't calculate that. Please try a simple mathematical expression")

# Screenshot
def take_screenshot():
    """Take a screenshot"""
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        screenshot.save(filename)
        speak(f"Screenshot saved as {filename}")
    except ImportError:
        speak("Screenshot feature requires pyautogui. Please install it to use this feature")
    except:
        speak("Unable to take screenshot")

# Volume Control
def volume_control(command):
    """Control system volume"""
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        if "up" in command or "increase" in command:
            current_volume = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(min(1.0, current_volume + 0.1), None)
            speak("Volume increased")
        elif "down" in command or "decrease" in command:
            current_volume = volume.GetMasterVolumeLevelScalar()
            volume.SetMasterVolumeLevelScalar(max(0.0, current_volume - 0.1), None)
            speak("Volume decreased")
        elif "mute" in command:
            volume.SetMute(1, None)
            speak("Volume muted")
        elif "unmute" in command:
            volume.SetMute(0, None)
            speak("Volume unmuted")
        else:
            current_volume = int(volume.GetMasterVolumeLevelScalar() * 100)
            speak(f"Current volume is {current_volume} percent")

    except ImportError:
        speak("Volume control requires pycaw. Please install it to use this feature")
    except:
        speak("Unable to control volume")

# News Headlines
def get_news():
    """Get top news headlines"""
    try:
        # Using NewsAPI (you'll need to get a free API key from newsapi.org)
        api_key = "YOUR_NEWS_API_KEY"  # Replace with actual API key
        url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"

        response = requests.get(url)
        data = response.json()

        if data.get("status") == "ok":
            articles = data.get("articles", [])[:3]  # Get top 3 headlines
            speak("Here are the top news headlines:")
            for i, article in enumerate(articles, 1):
                title = article.get("title", "No title")
                speak(f"News {i}: {title}")
        else:
            speak("Unable to fetch news at the moment")
    except:
        speak("News service is not available. Please check your internet connection")

# Dictionary
def dictionary(command):
    """Get definition of a word"""
    try:
        word = command.replace("define", "").replace("definition", "").replace("meaning", "").strip()

        if not word:
            speak("Please specify a word to define")
            return

        # Using a free dictionary API
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                definition = data[0]["meanings"][0]["definitions"][0]["definition"]
                speak(f"The definition of {word} is: {definition}")
            else:
                speak(f"Sorry, I couldn't find the definition of {word}")
        else:
            speak(f"Sorry, I couldn't find the definition of {word}")
    except:
        speak("Dictionary service is not available")

# Timer
def set_timer(command):
    """Set a timer"""
    try:
        # Extract time from command (e.g., "set timer for 5 minutes")
        import re
        time_match = re.search(r'(\d+)\s*(minute|minutes|second|seconds|hour|hours)', command)

        if time_match:
            amount = int(time_match.group(1))
            unit = time_match.group(2)

            # Convert to seconds
            if 'hour' in unit:
                seconds = amount * 3600
            elif 'minute' in unit:
                seconds = amount * 60
            else:  # seconds
                seconds = amount

            speak(f"Setting timer for {amount} {unit}")

            def timer_thread():
                time.sleep(seconds)
                # Play beep sound multiple times
                for _ in range(3):
                    winsound.Beep(1000, 500)
                    time.sleep(0.5)
                speak(f"Timer finished! {amount} {unit} have passed")

            threading.Thread(target=timer_thread, daemon=True).start()
        else:
            speak("Please specify timer duration like 'set timer for 5 minutes'")
    except:
        speak("Unable to set timer")

# Lock Screen
def lock_screen():
    """Lock the computer screen"""
    try:
        if platform.system() == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            speak("Screen locked")
        else:
            speak("Screen lock is only available on Windows")
    except:
        speak("Unable to lock screen")

# Empty Recycle Bin
def empty_recycle_bin():
    """Empty the recycle bin"""
    try:
        if platform.system() == "Windows":
            # Use Windows API to empty recycle bin
            import ctypes
            result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 1)
            if result == 0:
                speak("Recycle bin emptied successfully")
            else:
                speak("Unable to empty recycle bin")
        else:
            speak("Recycle bin management is only available on Windows")
    except:
        speak("Unable to empty recycle bin")

# File Operations
def list_files():
    """List files in current directory"""
    try:
        files = os.listdir('.')
        file_count = len([f for f in files if os.path.isfile(f)])
        dir_count = len([f for f in files if os.path.isdir(f)])

        speak(f"Current directory has {file_count} files and {dir_count} folders")
        if len(files) <= 10:
            speak("Files and folders: " + ", ".join(files[:10]))
        else:
            speak("Too many files to list. Use 'list files in [folder]' for specific directories")
    except:
        speak("Unable to list files")

# Create Note/Reminder
def create_note():
    """Create a simple note"""
    try:
        dialog = tk.Toplevel(window)
        dialog.title("Create Note")
        dialog.geometry("400x200")
        dialog.attributes('-topmost', True)

        tk.Label(dialog, text="Enter your note:", font=("Arial", 12)).pack(pady=10)

        text_area = tk.Text(dialog, height=6, width=40)
        text_area.pack(pady=5)

        def save_note():
            note_content = text_area.get("1.0", tk.END).strip()
            if note_content:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"note_{timestamp}.txt"
                with open(filename, 'w') as f:
                    f.write(note_content)
                speak(f"Note saved as {filename}")
            dialog.destroy()

        tk.Button(dialog, text="Save Note", command=save_note).pack(pady=10)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack()

    except:
        speak("Unable to create note")

# Command processor
def process_command(command):

    if "time" in command:
        tell_time()

    elif "date" in command:
        tell_date()

    elif "wikipedia" in command:
        search_wikipedia(command)

    elif "search" in command and "google" not in command:
        google_search(command)

    elif "open youtube" in command or "open google" in command or "open gmail" in command:
        open_website(command)

    elif "play" in command and "video" not in command:
        play_video(command)

    elif "joke" in command:
        tell_joke()

    elif "weather" in command:
        weather()

    elif "open" in command and any(app in command for app in ["notepad", "calculator", "chrome"]):
        open_app(command)

    elif "shutdown" in command:
        shutdown()

    elif "restart" in command:
        restart()

    elif "system info" in command or "cpu" in command or "memory" in command:
        system_info()

    elif "battery" in command:
        battery_status()

    elif "network" in command or "ip address" in command:
        network_info()

    elif "calculate" in command or "compute" in command or "what is" in command:
        calculate(command)

    elif "screenshot" in command:
        take_screenshot()

    elif "volume" in command:
        volume_control(command)

    elif "news" in command:
        get_news()

    elif "define" in command or "definition" in command or "meaning" in command:
        dictionary(command)

    elif "timer" in command or "remind me" in command:
        set_timer(command)

    elif "lock screen" in command or "lock computer" in command:
        lock_screen()

    elif "empty recycle bin" in command or "clear recycle bin" in command:
        empty_recycle_bin()

    elif "list files" in command:
        list_files()

    elif "create note" in command or "make note" in command:
        create_note()

    elif "who are you" in command:
        speak("I am your advanced artificial intelligence desktop assistant with enhanced capabilities")

    elif "how are you" in command:
        speak("I am functioning optimally and ready to assist you")

    elif "what can you do" in command:
        speak("I can help with time, date, weather, web search, playing videos, system information, calculations, screenshots, volume control, news, dictionary, timers, and much more")

    elif "exit" in command or "bye" in command or "quit" in command:
        speak("Goodbye! Have a great day")
        window.quit()

    else:
        speak("Command not recognized. Try saying 'what can you do' to see available commands")

# Start assistant (simplified - no threading)
def start_assistant():
    output_text.insert(tk.END, "Assistant started! Say your commands...\n")
    output_text.see(tk.END)

    # Simple greeting
    speak("Hello! I am your personal desktop assistant. How can I help you today?")

    # Start the listening loop
    window.after(1000, listen_continuous)

def listen_continuous():
    """Continuous listening loop using tkinter's after() method"""
    try:
        command = take_command()
        if command and command != "none":
            process_command(command)
        # Schedule next listen after a short delay
        window.after(500, listen_continuous)
    except Exception as e:
        output_text.insert(tk.END, f"Listening error: {e}\n")
        output_text.see(tk.END)
        # Try again after error
        window.after(2000, listen_continuous)


# Test TTS function
def test_tts():
    speak("Hello! This is a test of the text to speech system. If you can hear this, the voice output is working correctly.")

# GUI Window
window = tk.Tk()
window.title("🤖 Advanced AI Desktop Assistant")
window.geometry("800x700")
window.configure(bg='#2C3E50')  # Dark blue background

print("🎯 Advanced AI Assistant GUI Window Opening...")
print("Look for the window titled 'Advanced AI Desktop Assistant'")
print("It should appear in the center of your screen and stay on top for 2 seconds")

# Make window more visible
window.attributes('-topmost', True)  # Always on top initially
window.focus_force()  # Force focus
window.lift()  # Bring to front

# Center the window on screen
window.update_idletasks()
width = window.winfo_width()
height = window.winfo_height()
x = (window.winfo_screenwidth() // 2) - (width // 2)
y = (window.winfo_screenheight() // 2) - (height // 2)
window.geometry(f'{width}x{height}+{x}+{y}')

# Remove always-on-top after 2 seconds
def remove_topmost():
    window.attributes('-topmost', False)
    print("Window is now ready for use!")
window.after(2000, remove_topmost)

# Title with better styling
title_frame = tk.Frame(window, bg='#2C3E50')
title_frame.pack(pady=10)

title = tk.Label(title_frame, text="🤖 Advanced AI Desktop Assistant",
                font=("Arial", 24, "bold"), fg='#ECF0F1', bg='#2C3E50')
title.pack()

subtitle = tk.Label(title_frame, text="Your Intelligent Voice Assistant",
                   font=("Arial", 12), fg='#BDC3C7', bg='#2C3E50')
subtitle.pack(pady=(0, 10))

# Status indicator
status_frame = tk.Frame(window, bg='#2C3E50')
status_frame.pack(pady=5)

status_label = tk.Label(status_frame, text="● Ready", font=("Arial", 10, "bold"),
                       fg='#27AE60', bg='#2C3E50')
status_label.pack()

# Quick action buttons frame
button_frame = tk.Frame(window, bg='#34495E', relief='raised', bd=2)
button_frame.pack(pady=10, padx=20, fill='x')

# Row 1: Voice and Text Input
voice_frame = tk.Frame(button_frame, bg='#34495E')
voice_frame.pack(pady=5)

voice_button = tk.Button(voice_frame, text="🎤 Voice Command", font=("Arial", 11, "bold"),
                        bg='#E74C3C', fg='white', width=15, height=2,
                        relief='raised', bd=3, command=lambda: threading.Thread(target=voice_command_thread, daemon=True).start())
voice_button.pack(side=tk.LEFT, padx=5)

text_button = tk.Button(voice_frame, text="✍️ Text Command", font=("Arial", 11, "bold"),
                       bg='#3498DB', fg='white', width=15, height=2,
                       relief='raised', bd=3, command=lambda: threading.Thread(target=text_command_thread, daemon=True).start())
text_button.pack(side=tk.LEFT, padx=5)

# Row 2: Quick Actions
quick_frame = tk.Frame(button_frame, bg='#34495E')
quick_frame.pack(pady=5)

time_btn = tk.Button(quick_frame, text="🕐 Time", font=("Arial", 9), bg='#9B59B6', fg='white',
                    width=10, height=1, command=lambda: tell_time())
time_btn.pack(side=tk.LEFT, padx=3)

date_btn = tk.Button(quick_frame, text="📅 Date", font=("Arial", 9), bg='#9B59B6', fg='white',
                    width=10, height=1, command=lambda: tell_date())
date_btn.pack(side=tk.LEFT, padx=3)

weather_btn = tk.Button(quick_frame, text="🌤️ Weather", font=("Arial", 9), bg='#F39C12', fg='white',
                       width=10, height=1, command=lambda: weather())
weather_btn.pack(side=tk.LEFT, padx=3)

joke_btn = tk.Button(quick_frame, text="😄 Joke", font=("Arial", 9), bg='#E67E22', fg='white',
                    width=10, height=1, command=lambda: tell_joke())
joke_btn.pack(side=tk.LEFT, padx=3)

# Row 3: System Actions
system_frame = tk.Frame(button_frame, bg='#34495E')
system_frame.pack(pady=5)

sysinfo_btn = tk.Button(system_frame, text="💻 System Info", font=("Arial", 9), bg='#16A085', fg='white',
                       width=12, height=1, command=lambda: system_info())
sysinfo_btn.pack(side=tk.LEFT, padx=3)

battery_btn = tk.Button(system_frame, text="🔋 Battery", font=("Arial", 9), bg='#16A085', fg='white',
                       width=10, height=1, command=lambda: battery_status())
battery_btn.pack(side=tk.LEFT, padx=3)

calc_btn = tk.Button(system_frame, text="🧮 Calculator", font=("Arial", 9), bg='#2980B9', fg='white',
                    width=12, height=1, command=lambda: threading.Thread(target=calc_thread, daemon=True).start())
calc_btn.pack(side=tk.LEFT, padx=3)

# Row 4: Utility Actions
utility_frame = tk.Frame(button_frame, bg='#34495E')
utility_frame.pack(pady=5)

note_btn = tk.Button(utility_frame, text="📝 Create Note", font=("Arial", 9), bg='#8E44AD', fg='white',
                    width=12, height=1, command=lambda: create_note())
note_btn.pack(side=tk.LEFT, padx=3)

timer_btn = tk.Button(utility_frame, text="⏰ Set Timer", font=("Arial", 9), bg='#8E44AD', fg='white',
                     width=12, height=1, command=lambda: threading.Thread(target=timer_thread, daemon=True).start())
timer_btn.pack(side=tk.LEFT, padx=3)

screenshot_btn = tk.Button(utility_frame, text="📸 Screenshot", font=("Arial", 9), bg='#D35400', fg='white',
                          width=12, height=1, command=lambda: take_screenshot())
screenshot_btn.pack(side=tk.LEFT, padx=3)

# Output text area with better styling
output_frame = tk.Frame(window, bg='#2C3E50')
output_frame.pack(pady=10, padx=20, fill='both', expand=True)

output_label = tk.Label(output_frame, text="Assistant Output:", font=("Arial", 12, "bold"),
                       fg='#ECF0F1', bg='#2C3E50')
output_label.pack(anchor='w')

output_text = tk.Text(output_frame, height=15, font=("Consolas", 10),
                     bg='#1A252F', fg='#ECF0F1', insertbackground='white',
                     relief='sunken', bd=3)
output_text.pack(fill=tk.BOTH, expand=True)

# Add scrollbar with styling
scrollbar = tk.Scrollbar(output_text, bg='#34495E', troughcolor='#2C3E50')
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
output_text.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=output_text.yview)

# Bottom control buttons
control_frame = tk.Frame(window, bg='#2C3E50')
control_frame.pack(pady=10)

start_button = tk.Button(control_frame, text="▶️ Start Assistant", font=("Arial", 11, "bold"),
                        bg='#27AE60', fg='white', width=15, height=2,
                        relief='raised', bd=3, command=start_assistant)
start_button.pack(side=tk.LEFT, padx=10)

test_tts_button = tk.Button(control_frame, text="🔊 Test Voice", font=("Arial", 11, "bold"),
                           bg='#F1C40F', fg='black', width=15, height=2,
                           relief='raised', bd=3, command=test_tts)
test_tts_button.pack(side=tk.LEFT, padx=10)

clear_button = tk.Button(control_frame, text="🗑️ Clear Output", font=("Arial", 11, "bold"),
                        bg='#95A5A6', fg='white', width=15, height=2,
                        relief='raised', bd=3, command=lambda: output_text.delete(1.0, tk.END))
clear_button.pack(side=tk.LEFT, padx=10)

# Thread functions for button commands
def voice_command_thread():
    try:
        command = take_command()
        if command and command != "none":
            process_command(command)
    except Exception as e:
        output_text.insert(tk.END, f"Voice command error: {e}\n")
        output_text.see(tk.END)

def text_command_thread():
    try:
        command = gui_text_input()
        if command:
            output_text.insert(tk.END, f"✍️ You typed: {command}\n")
            output_text.see(tk.END)
            process_command(command.lower())
    except Exception as e:
        output_text.insert(tk.END, f"Text command error: {e}\n")
        output_text.see(tk.END)

def calc_thread():
    calc_input = gui_text_input("Enter calculation (e.g., 2+2*3):")
    if calc_input:
        command = f"calculate {calc_input}"
        process_command(command)

def timer_thread():
    timer_input = gui_text_input("Set timer (e.g., 5 minutes):")
    if timer_input:
        command = f"set timer for {timer_input}"
        process_command(command)

window.mainloop()
