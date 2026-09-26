"""
Lip-Sync Engine for Telugu Animated Stories
Analyzes audio waveform energy, envelope, and spectral features to output
frame-accurate mouth-shape phoneme cues at specified FPS (default 24 FPS).
Uses word-timing-based speech alignment (Synctoon Reference Principle).
"""

import os
import sys
import wave
import math
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
    Analyzes audio waveform and dialogue text to produce frame-accurate mouth visemes.
    Implements Synctoon Reference Principle:
    Audio waveform energy + dialogue text -> word/syllable timing -> viseme hold cues.
    """
    with wave.open(wav_path, 'rb') as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw_data = wf.readframes(n_frames)
        
    duration = n_frames / float(framerate)
    total_video_frames = int(math.ceil(duration * fps))
    
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
        zcr = np.sum(np.abs(np.diff(np.sign(chunk)))) / (2.0 * len(chunk))
        
        energies.append(rms)
        zcrs.append(zcr)
        
    energies = np.array(energies)
    zcrs = np.array(zcrs)
    
    # Dynamic silence threshold
    silence_thresh = max(0.02, np.percentile(energies, 20) * 1.2)
    loud_thresh = np.percentile(energies, 85)
    
    # Split text into words
    clean_text = text.replace(",", " ").replace(".", " ").replace("!", " ").replace("?", " ")
    words = [w.strip() for w in clean_text.split() if w.strip()]
    
    # Find contiguous voiced regions (speech bursts)
    voiced_mask = (energies >= silence_thresh)
    speech_bursts = []
    in_burst = False
    burst_start = 0
    
    for idx, is_v in enumerate(voiced_mask):
        if is_v and not in_burst:
            in_burst = True
            burst_start = idx
        elif not is_v and in_burst:
            in_burst = False
            if idx - burst_start >= 2: # At least 2 frames
                speech_bursts.append((burst_start, idx - 1))
    if in_burst:
        speech_bursts.append((burst_start, len(voiced_mask) - 1))
        
    raw_cues = [MOUTH_CLOSED] * total_video_frames
    
    if words and speech_bursts:
        # Synctoon principle: Map words to speech bursts proportionally
        num_words = len(words)
        num_bursts = len(speech_bursts)
        
        # Build list of all voiced frames across all bursts
        all_voiced_frames = []
        for b_start, b_end in speech_bursts:
            all_voiced_frames.extend(range(b_start, b_end + 1))
            
        total_voiced = len(all_voiced_frames)
        
        # Extract phonemes per word
        word_phoneme_lists = []
        for w in words:
            phs = extract_telugu_phonemes(w)
            if not phs:
                phs = [MOUTH_OPEN_A]
            word_phoneme_lists.append(phs)
            
        # Distribute word bursts along the timeline
        frames_per_word = max(2, total_voiced // max(1, num_words))
        
        v_ptr = 0
        for w_idx, ph_list in enumerate(word_phoneme_lists):
            w_frame_count = frames_per_word
            if w_idx == num_words - 1:
                w_frame_count = max(len(ph_list) * 2, total_voiced - v_ptr)
                
            w_frames = all_voiced_frames[v_ptr : v_ptr + w_frame_count]
            v_ptr += w_frame_count
            
            if not w_frames:
                continue
                
            # Distribute phonemes inside this word's frame allocation
            num_ph = len(ph_list)
            for p_rank, f_num in enumerate(w_frames):
                e = energies[f_num]
                z = zcrs[f_num]
                if e > loud_thresh and loud_thresh > silence_thresh * 1.5:
                    raw_cues[f_num] = MOUTH_WIDE
                elif z > 0.28:
                    raw_cues[f_num] = MOUTH_TEETH
                else:
                    ph_i = min(num_ph - 1, int((p_rank / float(len(w_frames))) * num_ph))
                    raw_cues[f_num] = ph_list[ph_i]
    elif voiced_mask.any():
        telugu_phonemes = extract_telugu_phonemes(text) or [MOUTH_OPEN_A, MOUTH_OPEN_E, MOUTH_OPEN_O]
        voiced_indices = [idx for idx, is_v in enumerate(voiced_mask) if is_v]
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
                raw_cues[v_idx] = telugu_phonemes[ph_idx]
                
    # 2-Pass Hold Filter: Enforce 2-3 frame holds, strictly closed during silence
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
