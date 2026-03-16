# 🤖 Advanced AI Desktop Voice Assistant

A powerful, feature-rich desktop voice assistant built with Python, featuring a modern GUI interface and extensive command capabilities.

## ✨ Features

### 🎤 Voice Recognition
- Advanced voice input using sounddevice library
- Automatic fallback to text input if voice fails
- 3-second recording duration for optimal recognition

### 🖥️ Modern GUI Interface
- Dark theme with professional styling
- Quick action buttons for common commands
- Real-time output display with scrollable text area
- Status indicators and visual feedback

### 🧠 Smart Command Processing
- Natural language command recognition
- Extensive command library with 25+ features
- Intelligent command routing and error handling

## 📋 Available Commands

### ⏰ Time & Date
- "time" - Get current time
- "date" - Get current date

### 🌤️ Information & Search
- "weather" - Get weather information
- "wikipedia [topic]" - Search Wikipedia
- "search [query]" - Google search
- "news" - Get top news headlines
- "define [word]" - Get word definition

### 🎵 Entertainment
- "play [song/video]" - Play on YouTube
- "joke" - Tell a random joke
- "open youtube/google/gmail" - Open websites

### 💻 System Control
- "system info" - CPU, memory, disk usage
- "battery" - Battery status
- "network" - Network information
- "volume up/down/mute/unmute" - Audio control
- "screenshot" - Take screenshot
- "lock screen" - Lock computer
- "empty recycle bin" - Clear recycle bin

### 🛠️ Utilities
- "calculate [expression]" - Calculator (e.g., "calculate 2+2*3")
- "set timer for [time]" - Set timer (e.g., "set timer for 5 minutes")
- "create note" - Create and save text notes
- "list files" - List files in current directory

### ⚙️ System Management
- "open notepad/calculator/chrome" - Launch applications
- "shutdown" - Shutdown computer
- "restart" - Restart computer

### 💬 Conversation
- "who are you" - Assistant introduction
- "how are you" - Status check
- "what can you do" - List capabilities
- "exit/bye/quit" - Close assistant

## 🚀 Quick Start

1. **Run the Assistant:**
   ```bash
   python assistant.py
   ```

2. **GUI Controls:**
   - 🎤 Voice Command - Start voice recognition
   - ✍️ Text Command - Type commands manually
   - ▶️ Start Assistant - Begin continuous listening
   - 🔊 Test Voice - Test text-to-speech
   - 🗑️ Clear Output - Clear the output area

3. **Quick Action Buttons:**
   - Direct access to common commands
   - One-click execution without voice/text input

## 📦 Dependencies

Install required packages:
```bash
pip install speech_recognition pyttsx3 sounddevice numpy tkinter requests wikipedia pywhatkit pyjokes psutil
```

### Optional Packages (for enhanced features):
```bash
pip install pyautogui  # For screenshots
pip install pycaw      # For volume control
```

## 🔧 Configuration

### Weather API
Replace `YOUR_API_KEY` in the code with your OpenWeatherMap API key:
1. Sign up at [OpenWeatherMap](https://openweathermap.org/api)
2. Get your free API key
3. Replace `YOUR_API_KEY` in the `weather()` function

### News API (Optional)
For news headlines, get a free API key from [NewsAPI](https://newsapi.org):
1. Sign up for free tier
2. Replace `YOUR_NEWS_API_KEY` in the `get_news()` function

## 🎨 GUI Features

- **Dark Professional Theme:** Modern color scheme with blue and gray tones
- **Responsive Layout:** Adapts to different window sizes
- **Visual Feedback:** Status indicators and colored buttons
- **Organized Button Groups:** Logical grouping of related functions
- **Scrollable Output:** Large text area with scrollbar for long conversations

## 🔊 Voice Features

- **Multi-Engine Support:** Primary sounddevice, fallback to PyAudio
- **Smart Fallback:** Automatic text input when voice fails
- **Background Processing:** Non-blocking voice synthesis
- **Microsoft Voices:** High-quality TTS using system voices

## 🛡️ Error Handling

- Graceful degradation when features are unavailable
- Clear error messages in the output area
- Automatic fallback mechanisms
- Thread-safe operations to prevent GUI freezing

## 📝 Notes

- The assistant runs in a GUI window that stays on top initially for 2 seconds
- Voice recognition works best in quiet environments
- Some features require internet connection (weather, news, search)
- System control features are Windows-specific
- All text input supports both voice and manual typing

## 🐛 Troubleshooting

- **Voice not working:** Check microphone permissions and try text input
- **GUI not visible:** The window centers on screen and stays on top briefly
- **Package errors:** Ensure all dependencies are installed
- **TTS not working:** Check system audio settings

## 🔄 Updates

The assistant is designed to be easily extensible. Add new commands by:
1. Creating a new function for the feature
2. Adding command recognition in `process_command()`
3. Optionally adding a GUI button

---

**Enjoy your advanced AI desktop assistant! 🚀**

This project is for educational purposes. Feel free to modify and improve!