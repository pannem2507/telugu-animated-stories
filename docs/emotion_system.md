# GENERIC EMOTION & ACTING SYSTEM SPECIFICATION

## 1. Multi-Channel Acting Architecture

When a character performs an emotion, the engine coordinates six distinct physical channels simultaneously:

1. **Brows & Forehead**: Radial pull vectors modify brow height, arch, and furrow angle.
2. **Eyelids & Blink**: Periodic organic blinking with dynamic landmark anchoring.
3. **Mouth & Lips**: Phoneme visemes blend with emotion mouth corners (downturn for sadness, upturn for joy).
4. **Tears**: Four-stage organic tear progression (`accumulate`, `form`, `flow`, `wipe`).
5. **Head & Neck**: Nodding, tilting, and accent nods triggered by speech audio stress peaks.
6. **Torso & Stance**: Forward lean in anger, slumping in sorrow, trembling in cold, or energetic bounce in joy.

---

## 2. Supported Emotion Primitives

| Emotion | Brow Action | Eye Action | Mouth Action | Posture / Torso |
| :--- | :--- | :--- | :--- | :--- |
| **`neutral`** | Relaxed | Normal blink | Closed / visemes | Idle breathing |
| **`angry`** / **`scold`** | Inner brows pull down & in | Squint | Tight pursed / wide | Aggressive forward lean |
| **`sad`** / **`cry`** | Inner brows lift in grief arch | Drooping eyelids | Downturned sorrow seam | Slumped posture, sobbing tremor |
| **`fear`** / **`cower`** | Arched high | Wide eyes | Quivering lips | Stiffened retreat away from speaker |
| **`happy`** / **`joy`** | Softened | Pleasant squint | Upturned corners | Upright energetic bounce |
| **`surprise`** | High arched | Maximum opening | Wide round opening | Sudden vertical pop |
| **`relief`** | Softened brow | Calm gaze | Subtle smile | Relaxed exhale |

---

## 3. Reaction Latency for Listeners

Non-speaking interlocutors do not instantly freeze or instantly react. The `ListenerReactionController` introduces a configurable latency (150ms–300ms) before the listener registers an emotional shock or scolding, then applies a cubic Hermite ease curve to transition smoothly into defensive cowering or sympathetic weeping.
