"""
Telugu Neural TTS Engine using edge-tts
Supports character voice mapping, SSML pitch and rate modulation.
"""

import os
import sys
import asyncio

# Fix Windows console UTF-8 printing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
import edge_tts
import wave
import contextlib

# Predefined voice configurations for Telugu characters
VOICE_PROFILES = {
    "atha": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+12Hz",      # Sharp comedic tone for Mother-in-law
        "rate": "+8%",         # Assertive delivery
        "volume": "+0%"
    },
    "kodalu": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "-4Hz",       # Soft, sweet, polite tone for Daughter-in-law
        "rate": "-2%",
        "volume": "+0%"
    },
    "father_in_law": {
        "voice": "te-IN-MohanNeural",
        "pitch": "-12Hz",      # Deep, mature grandfather/elder patriarch tone
        "rate": "-8%",         # Dignified, calm pacing
        "volume": "+0%"
    },
    "mamagaru": {
        "voice": "te-IN-MohanNeural",
        "pitch": "-12Hz",
        "rate": "-8%",
        "volume": "+0%"
    },
    "gent": {
        "voice": "te-IN-MohanNeural",
        "pitch": "+4Hz",       # Active young working husband/man
        "rate": "+6%",
        "volume": "+0%"
    },
    "husband": {
        "voice": "te-IN-MohanNeural",
        "pitch": "+4Hz",
        "rate": "+6%",
        "volume": "+0%"
    },
    "son": {
        "voice": "te-IN-MohanNeural",
        "pitch": "+8Hz",       # Energetic young son
        "rate": "+10%",
        "volume": "+0%"
    },
    "kid": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+50Hz",      # High-pitched playful young child/girl
        "rate": "+12%",
        "volume": "+0%"
    },
    "kid_boy": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+42Hz",      # Playful young boy
        "rate": "+10%",
        "volume": "+0%"
    },
    "neighbor": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+16Hz",      # Inquisitive village neighbor woman
        "rate": "+15%",
        "volume": "+0%"
    },
    "neighbor_man": {
        "voice": "te-IN-MohanNeural",
        "pitch": "-4Hz",       # Casual village neighbor man
        "rate": "+4%",
        "volume": "+0%"
    },
    "kanthamma": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+22Hz",      # Sharp, high pitch, gossipy/scheming tone
        "rate": "+15%",        # Fast, impatient delivery
        "volume": "+0%"
    },
    "saroja": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+18Hz",      # Reluctant/irritable neighbor woman
        "rate": "+10%",
        "volume": "+0%"
    },
    "padma": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+14Hz",      # Cold neighbor woman
        "rate": "+8%",
        "volume": "+0%"
    },
    "sudhakar": {
        "voice": "te-IN-MohanNeural",
        "pitch": "-2Hz",       # Neighbor man
        "rate": "+5%",
        "volume": "+0%"
    },
    "maharshi": {
        "voice": "te-IN-MohanNeural",
        "pitch": "-10Hz",      # Resonant, calm, divine spiritual sage
        "rate": "-12%",        # Slow, peaceful, meditative tempo
        "volume": "+0%"
    },
    "ramesh": {
        "voice": "te-IN-MohanNeural",
        "pitch": "+4Hz",       # Modern working son/husband
        "rate": "+6%",
        "volume": "+0%"
    },
    "sharada": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+12Hz",      # Mother-in-law Sharada
        "rate": "+8%",
        "volume": "+0%"
    },
    "anamika": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "-4Hz",       # Heroine / Kodalu
        "rate": "-2%",
        "volume": "+0%"
    },
    "prasad": {
        "voice": "te-IN-MohanNeural",
        "pitch": "-12Hz",      # Grandfather Prasad
        "rate": "-8%",
        "volume": "+0%"
    },
    "harish": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+42Hz",      # Young grandson Harish
        "rate": "+10%",
        "volume": "+0%"
    },
    "bhavya": {
        "voice": "te-IN-ShrutiNeural",
        "pitch": "+50Hz",      # Young granddaughter Bhavya
        "rate": "+12%",
        "volume": "+0%"
    },
    "narrator": {
        "voice": "te-IN-MohanNeural",
        "pitch": "+0Hz",       # Deep, authoritative narrator tone
        "rate": "+0%",
        "volume": "+0%"
    }
}

def get_audio_duration(file_path: str) -> float:
    """Returns duration of a WAV or MP3 audio file in seconds."""
    try:
        with contextlib.closing(wave.open(file_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            return frames / float(rate)
    except Exception:
        # Fallback using mutagen or moviepy / pydub
        from pydub import AudioSegment
        seg = AudioSegment.from_file(file_path)
        return len(seg) / 1000.0

async def _synthesize_async(text: str, voice: str, pitch: str, rate: str, volume: str, output_path: str):
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        pitch=pitch,
        rate=rate,
        volume=volume
    )
    await communicate.save(output_path)

def synthesize_dialogue(text: str, character: str = "narrator", output_path: str = None, pitch_override: str = None, rate_override: str = None) -> dict:
    """
    Synthesizes Telugu speech from text for the given character.
    Returns dict with output_path and duration in seconds.
    """
    profile = VOICE_PROFILES.get(character.lower(), VOICE_PROFILES["narrator"])
    voice = profile["voice"]
    pitch = pitch_override or profile["pitch"]
    rate = rate_override or profile["rate"]
    volume = profile["volume"]
    
    if output_path is None:
        os.makedirs("output/temp_audio", exist_ok=True)
        import uuid
        output_path = os.path.abspath(f"output/temp_audio/{character}_{uuid.uuid4().hex[:8]}.mp3")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
    wav_path = output_path.rsplit(".", 1)[0] + ".wav"
    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 2000:
        duration = get_audio_duration(wav_path)
        return {
            "mp3_path": output_path,
            "wav_path": wav_path,
            "duration": duration,
            "character": character,
            "text": text
        }
        
    asyncio.run(_synthesize_async(text, voice, pitch, rate, volume, output_path))
    
    # Convert mp3 to wav if necessary for precise waveform lipsyncing
    from pydub import AudioSegment
    sound = AudioSegment.from_file(output_path)
    sound.export(wav_path, format="wav")
    
    duration = get_audio_duration(wav_path)
    
    return {
        "mp3_path": output_path,
        "wav_path": wav_path,
        "duration": duration,
        "character": character,
        "text": text
    }

if __name__ == "__main__":
    # Quick self-test
    test_line = "ఏమే కోడలా! చేపల పచ్చడి ఎంతవరకు వచ్చింది?"
    print(f"Synthesizing test Telugu dialogue: {test_line}")
    res = synthesize_dialogue(test_line, character="atha", output_path="D:/telugu-animated-stories/output/test_atha.mp3")
    print(f"Generated: {res['wav_path']} (Duration: {res['duration']:.2f}s)")
