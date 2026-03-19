#!/usr/bin/env python3
"""
Microphone test utility.
Records 5 seconds of audio and reports whether sound was detected.
Run with: python testmic.py
"""

import sys

try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    print("ERROR: sounddevice or numpy not installed.")
    print("Run: pip install sounddevice numpy")
    sys.exit(1)

DURATION    = 5       # seconds to record
SAMPLE_RATE = 44100   # Hz

print(f"[MIC TEST] Recording {DURATION} seconds — speak now...")

try:
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1)
    sd.wait()
except Exception as e:
    print(f"ERROR: Could not access microphone: {e}")
    sys.exit(1)

volume_norm = float(np.linalg.norm(recording))

if volume_norm > 0:
    print(f"[MIC TEST] PASS — Microphone is working! (signal level: {volume_norm:.2f})")
else:
    print("[MIC TEST] FAIL — No sound detected. Check microphone connection and permissions.")
    sys.exit(1)
