"""
Lip-Sync Engine for Telugu Animated Stories
Analyzes audio waveform energy, envelope, and spectral features to output
frame-accurate mouth-shape phoneme cues at specified FPS (default 24 FPS).
"""

import os
import sys
import wave
import numpy as np

# Fix Windows console UTF-8 printing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Supported mouth shape cue names
MOUTH_CLOSED = "mouth_closed"
MOUTH_OPEN_A = "mouth_open_a"
MOUTH_OPEN_E = "mouth_open_e"
MOUTH_OPEN_O = "mouth_open_o"
MOUTH_TEETH  = "mouth_teeth"
MOUTH_WIDE   = "mouth_wide"

def extract_telugu_phonemes(text: str) -> list:
    """
    Parses Telugu text into frame-distributable mouth viseme cues.
    Maps vowels, matras, labials, and sibilants to viseme names.
    """
    if not text:
        return []
        
    phonemes = []
    # Telugu Unicode ranges: \u0C00 - \u0C7F
    for ch in text:
        # 1. Open vowels / broad Aa
        if ch in ['అ', 'ఆ', '\u0c3e', 'హ', 'ా']:
            phonemes.append(MOUTH_OPEN_A)
        # 2. Spread vowels / Ee / E
        elif ch in ['ఇ', 'ఈ', '\u0c3f', '\u0c40', 'ఎ', 'ఏ', 'ఐ', '\u0c46', '\u0c47', '\u0c48', 'య', 'ి', 'ీ', 'ె', 'ే', 'ై']:
            phonemes.append(MOUTH_OPEN_E)
        # 3. Rounded vowels / Oo / U
        elif ch in ['ఉ', 'ఊ', '\u0c41', '\u0c42', 'ఒ', 'ఓ', 'ఔ', '\u0c4a', '\u0c4b', '\u0c4c', 'ు', 'ూ', 'ొ', 'ో', 'ౌ']:
            phonemes.append(MOUTH_OPEN_O)
        # 4. Labials (lips close)
        elif ch in ['ప', 'ఫ', 'బ', 'భ', 'మ', '\u0c02', 'ం']:
            phonemes.append(MOUTH_CLOSED)
        # 5. Sibilants / Dentals (teeth visible)
        elif ch in ['స', 'ష', 'శ', 'త', 'థ', 'ద', 'ధ', 'చ', 'జ', 'స్', 'త్']:
            phonemes.append(MOUTH_TEETH)
        # 6. Spaces / punctuation
        elif ch in [' ', ',', '.', '!', '?', '\n']:
            phonemes.append(MOUTH_CLOSED)
        else:
            # Consonants with implicit vowel 'a'
            if '\u0c15' <= ch <= '\u0c39':
                phonemes.append(MOUTH_OPEN_A)
                
    return phonemes

def extract_lipsync_cues(wav_path: str, fps: int = 24, text: str = "") -> list:
    """
    Analyzes the audio file and returns a list of mouth shape names,
    one for each video frame from 0 to total_frames - 1.
    If dialogue text is provided, aligns Telugu phonemes to voiced audio frames.
    """
    with wave.open(wav_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_data = wf.readframes(n_frames)
        
    duration = n_frames / float(framerate)
    total_video_frames = int(math_ceil(duration * fps))
    
    # Convert raw PCM bytes to float numpy array
    if sampwidth == 2:
        dtype = np.int16
    elif sampwidth == 4:
        dtype = np.int32
    else:
        dtype = np.uint8
        
    audio = np.frombuffer(raw_data, dtype=dtype).astype(np.float32)
    if n_channels > 1:
        audio = audio.reshape(-1, n_channels).mean(axis=1)
        
    # Normalize
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        audio = audio / max_val
        
    samples_per_video_frame = framerate / fps
    frame_cues = []
    
    # Compute RMS energy & zero-crossing rate per frame
    energies = []
    zcrs = []
    
    for i in range(total_video_frames):
        start_sample = int(i * samples_per_video_frame)
        end_sample = min(len(audio), int((i + 1) * samples_per_video_frame))
        
        if start_sample >= len(audio):
            energies.append(0.0)
            zcrs.append(0.0)
            continue
            
        chunk = audio[start_sample:end_sample]
        if len(chunk) == 0:
            energies.append(0.0)
            zcrs.append(0.0)
            continue
            
        rms = np.sqrt(np.mean(chunk**2))
        # Zero crossing rate
        zcr = np.sum(np.abs(np.diff(np.sign(chunk)))) / (2.0 * len(chunk))
        
        energies.append(rms)
        zcrs.append(zcr)
        
    energies = np.array(energies)
    zcrs = np.array(zcrs)
    
    # Dynamic silence threshold (bottom 15% energy or baseline)
    silence_thresh = max(0.02, np.percentile(energies, 20) * 1.2)
    loud_thresh = np.percentile(energies, 85)
    
    telugu_phonemes = extract_telugu_phonemes(text)
    
    # Find all voiced frames (speech activity)
    voiced_indices = [idx for idx, e in enumerate(energies) if e >= silence_thresh]
    
    raw_cues = [MOUTH_CLOSED] * total_video_frames
    
    if telugu_phonemes and voiced_indices:
        # Distribute Telugu phonemes proportionally across voiced speech frames
        num_voiced = len(voiced_indices)
        num_ph = len(telugu_phonemes)
        for rank, v_idx in enumerate(voiced_indices):
            e = energies[v_idx]
            z = zcrs[v_idx]
            if e > loud_thresh and loud_thresh > silence_thresh * 1.5:
                raw_cues[v_idx] = MOUTH_WIDE
            elif z > 0.26:
                raw_cues[v_idx] = MOUTH_TEETH
            else:
                ph_idx = min(num_ph - 1, int((rank / float(num_voiced)) * num_ph))
                ph = telugu_phonemes[ph_idx]
                raw_cues[v_idx] = ph
    else:
        for i in range(total_video_frames):
            e = energies[i]
            z = zcrs[i]
            
            if e < silence_thresh:
                raw_cues[i] = MOUTH_CLOSED
            elif e > loud_thresh and loud_thresh > silence_thresh:
                raw_cues[i] = MOUTH_WIDE
            elif z > 0.22:
                raw_cues[i] = MOUTH_TEETH
            else:
                cycle = (i % 6)
                if cycle in [0, 1]:
                    raw_cues[i] = MOUTH_OPEN_A
                elif cycle in [2, 3]:
                    raw_cues[i] = MOUTH_OPEN_E
                else:
                    raw_cues[i] = MOUTH_OPEN_O
                    
    # Smoothing filter: enforce stable 2-3 frame viseme holds (Adobe Animate lip-sync principle)
    # Prevents single-frame flickering/chatter while ensuring resting closed lips during silence
    smoothed_cues = list(raw_cues)
    n_c = len(smoothed_cues)
    
    # Pass 1: Eliminate isolated 1-frame spikes (except silence)
    for i in range(1, n_c - 1):
        if smoothed_cues[i] != smoothed_cues[i-1] and smoothed_cues[i] != smoothed_cues[i+1]:
            if smoothed_cues[i-1] != MOUTH_CLOSED:
                smoothed_cues[i] = smoothed_cues[i-1]
            elif smoothed_cues[i+1] != MOUTH_CLOSED:
                smoothed_cues[i] = smoothed_cues[i+1]
            else:
                smoothed_cues[i] = MOUTH_CLOSED
                
    # Pass 2: Quantize short voiced runs to at least 2 frames
    i = 0
    while i < n_c:
        if smoothed_cues[i] != MOUTH_CLOSED:
            run_start = i
            while i < n_c and smoothed_cues[i] != MOUTH_CLOSED:
                i += 1
            run_len = i - run_start
            if run_len == 1 and i < n_c:
                smoothed_cues[i] = smoothed_cues[run_start]
                i += 1
        else:
            i += 1
            
    return smoothed_cues

def math_ceil(x):
    import math
    return math.ceil(x)

if __name__ == "__main__":
    test_wav = "D:/telugu-animated-stories/output/test_atha.wav"
    if os.path.exists(test_wav):
        cues = extract_lipsync_cues(test_wav, fps=24)
        print(f"Generated {len(cues)} lipsync frames for {test_wav}")
        print("Sample first 24 frames (1 second):", cues[:24])
    else:
        print(f"File not found: {test_wav}")
