# GENERIC AUDIO, VOICE & LIP-SYNC SYSTEM SPECIFICATION

## 1. Overview

The Audio & Voice subsystem is responsible for speech synthesis, background score ducking, audio performance envelope extraction, and phoneme-accurate lip-sync cue generation.

```
                  ┌──────────────────────┐
                  │    Dialogue Text     │
                  └──────────┬───────────┘
                             ▼
                  ┌──────────────────────┐
                  │  TTS Speech Engine   │ (edge-tts / wav files)
                  └──────────┬───────────┘
                             ▼
             ┌───────────────┴───────────────┐
             ▼                               ▼
    [Lip-Sync Engine]            [Audio Performance Analyzer]
    - Energy envelope            - Syllabic stress peaks
    - Zero-crossing rate         - Attack intervals
    - 6 Phoneme Visemes          - Acting gesture strike beats
             │                               │
             └───────────────┬───────────────┘
                             ▼
                  ┌──────────────────────┐
                  │   Audio Mix Engine   │
                  │ (BGM -20dB Ducking)  │
                  └──────────────────────┘
```

---

## 2. Universal Visemes

The engine extracts 6 universal viseme states:
- `mouth_closed`: Neutral resting closed lips.
- `mouth_open_a`: Open jaw for vowels like /a/, /aa/.
- `mouth_open_e`: Horizontally stretched jaw for vowels like /e/, /i/.
- `mouth_open_o`: Rounded lips for vowels like /o/, /u/.
- `mouth_teeth`: Clenched teeth for dental/sibilant consonants /s/, /t/, /d/.
- `mouth_wide`: Energetic wide opening on shouting or stress peaks.

---

## 3. Multilingual Support

The engine supports any language available via Edge TTS or external WAV audio recordings. Phoneme extraction is audio-signal based (waveform analysis) rather than language-text dependent, ensuring 100% compatibility across English, Telugu, Hindi, Tamil, Spanish, and other languages.
