import sounddevice as sd
import numpy as np

print("🎤 Testing microphone... Speak now")

duration = 5  # seconds
fs = 44100

recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
sd.wait()

volume_norm = np.linalg.norm(recording)

if volume_norm > 0:
    print("✅ Microphone is working!")
else:
    print("❌ No sound detected")