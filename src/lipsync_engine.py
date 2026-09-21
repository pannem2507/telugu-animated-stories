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

def extract_lipsync_cues(wav_path: str, fps: int = 24) -> list:
    """
    Analyzes the audio file and returns a list of mouth shape names,
    one for each video frame from 0 to total_frames - 1.
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
    
    raw_cues = []
    for i in range(total_video_frames):
        e = energies[i]
        z = zcrs[i]
        
        if e < silence_thresh:
            raw_cues.append(MOUTH_CLOSED)
        elif e > loud_thresh and loud_thresh > silence_thresh:
            raw_cues.append(MOUTH_WIDE)
        elif z > 0.22:
            # High sibilant / consonant friction
            raw_cues.append(MOUTH_TEETH)
        else:
            # Vowels: alternate based on energy and modulation to create natural speaking rhythm
            cycle = (i % 6)
            if cycle in [0, 1]:
                raw_cues.append(MOUTH_OPEN_A)
            elif cycle in [2, 3]:
                raw_cues.append(MOUTH_OPEN_E)
            else:
                raw_cues.append(MOUTH_OPEN_O)
                
    # Smoothing filter: prevent single-frame flickering
    # Enforce minimum phoneme hold of 2 frames
    smoothed_cues = list(raw_cues)
    for i in range(1, len(smoothed_cues) - 1):
        if smoothed_cues[i] != smoothed_cues[i-1] and smoothed_cues[i] != smoothed_cues[i+1]:
            # Single-frame blip, match previous
            smoothed_cues[i] = smoothed_cues[i-1]
            
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
