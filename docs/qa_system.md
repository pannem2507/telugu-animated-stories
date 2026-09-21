# AUTOMATED QA FRAMEWORK SPECIFICATION

## 1. Scope and Automated Quality Checks

The Automated QA Framework analyzes rendered production videos against strict technical, visual, and narrative standards before approving distribution.

---

## 2. Test Matrix

1. **Container & Codec Integrity**:
   - Resolution: Exactly 1920x1080 Full HD.
   - Frame Rate: Exactly 24.000 fps (+/- 0.01 fps).
   - Video Codec: H.264 (libx264, High Profile, yuv420p).
   - Audio Codec: AAC stereo, 44.1kHz or 48kHz, 192kbps.

2. **A/V Alignment**:
   - Video stream duration matches audio stream duration within 0.25 seconds.

3. **Defect Detection**:
   - **Black Frame Check**: Flags unexpected mid-sequence black frames (mean luminance < 2.0).
   - **Freeze Frame Check**: Detects frozen video segments where dialogue is actively playing.
   - **Actor Presence Check**: Confirms that characters marked `is_present: false` (after exiting) do not render on stage.
   - **Prop Attachment Verification**: Checks that carried props do not detach or float in empty space.

---

## 3. Automated QA CLI Usage

```bash
python -m src.qa_engine --video output/production.mp4 --script screenplay.json --report scratch/qa_report.json
```
