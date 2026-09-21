# 🎬 Telugu Animated Stories Generator (Atha vs Kodalu Pipeline)

An automated 2D cartoon video production pipeline that converts Telugu dialogue scripts directly into rendered animated videos (with character puppets, dynamic lip-sync, idle animations, background music, and subtitles).

Inspired by viral South Indian YouTube animated channels like **Anamika TV (Atha vs Kodalu)**.

---

## 🚀 Quick Start

### 1. Prerequisites
* Python 3.10+
* FFmpeg (must be in system PATH)

### 2. Generate Your First Animated Video
Run the main script with the sample *Atha vs Kodalu Chepala Pachadi* story:

```powershell
python generate.py --script examples/sample_atha_kodalu.json --output output/atha_kodalu_animated.mp4
```

The output video will be exported to `output/atha_kodalu_animated.mp4`.

---

## 📂 Project Structure

```
D:\telugu-animated-stories\
├── assets/
│   ├── characters/
│   │   ├── atha/         # Base body, eyes_open/blink, 6 mouth shapes
│   │   ├── kodalu/       # Base body, eyes_open/blink, 6 mouth shapes
│   │   └── narrator/     # Base body, eyes_open/blink, 6 mouth shapes
│   ├── backgrounds/      # village_kitchen.png, village_porch.png
│   └── audio/            # village_bgm.wav (Village acoustic folk loop)
├── src/
│   ├── asset_generator.py # Procedural generation of starter puppets & backgrounds
│   ├── tts_engine.py      # Microsoft Neural Telugu voice synthesis (edge-tts)
│   ├── lipsync_engine.py  # Audio waveform energy & phoneme analyzer
│   ├── script_parser.py   # Script parser for JSON & text formats
│   └── compositor.py      # 1080p video rendering engine with OpenCV & FFmpeg
├── examples/
│   └── sample_atha_kodalu.json # Authentic Telugu comedy dialogue script
├── generate.py            # Main CLI entry point
└── requirements.txt
```

---

## 📝 How to Write a Custom Story Script

Create a JSON file (e.g., `my_story.json`) with this structure:

```json
{
  "title": "My Telugu Story",
  "scenes": [
    {
      "scene_id": 1,
      "background": "village_kitchen",
      "dialogues": [
        {
          "character": "atha",
          "text": "ఏమే కోడలా! నేను చెప్పిన పని ఎంతవరకు వచ్చింది?",
          "action": "question"
        },
        {
          "character": "kodalu",
          "text": "ఇదిగో అత్తయ్య గారు, ఇప్పుడే పూర్తి చేస్తున్నాను!",
          "action": "answer"
        }
      ]
    }
  ]
}
```

Then generate:
```powershell
python generate.py --script my_story.json --output output/my_story.mp4
```

---

## 🎨 Customizing Characters & Backgrounds

You can replace any of the starter images with your own custom illustrations:
* Simply place your artist-drawn PNGs into `assets/characters/<character_name>/`:
  * `base.png` (transparent body + head without mouth/eyes)
  * `eyes_open.png` & `eyes_blink.png`
  * `mouth_closed.png`, `mouth_open_a.png`, `mouth_open_e.png`, `mouth_open_o.png`, `mouth_teeth.png`, `mouth_wide.png`
* Add your own backgrounds into `assets/backgrounds/`.
