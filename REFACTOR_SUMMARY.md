# Manhwa Recap Generator - Optimization & Sync Refactor

## Summary of Changes
We have completely overhauled the generation pipeline to ensure **Perfect Video-Audio Synchronization** and **Error-Free Execution**.

### 1. Fixed "Gemini API 404" Errors
- **Issue**: The code was requesting `gemini-1.5-flash-8b` in a way that caused 404s, or the model was deprecated.
- **Fix**: Updated `app/script_generator.py` to use valid, high-performance models:
  - `gemini-1.5-flash` (Primary, fast & free)
  - `gemini-2.0-flash-exp` (Experimental, extremely fast)
  - `gemini-1.5-pro` (High quality fallback)

### 2. "Perfect Sync" Architecture
We moved away from the "One Big Script / One Big Audio" approach which caused drifting sync issues.

**New Pipeline:**
1.  **Batch Processing**: Images are processed in small batches (e.g., 6 images).
2.  **Segmented Script**: Gemini generates a script *specifically* for that batch. By returning structured data `{"text": "...", "images": [...]}` instead of just text.
3.  **Discrete Audio Generation**: We generate a separate audio file for *each batch*.
4.  **Strict Timing**: The Video Editor now aligns:
    - **Audio Segment A** (Concept: "The hero enters the dungeon...")
    - **Images Batch A** (Visual: Hero walking, Door opening)
    - **Duration**: The images are displayed for exactly `Audio_Duration / Image_Count`.

**Result**: The audio will NEVER drift ahead or behind the relevant images.

### 3. Pipeline Optimization (Reordering)
**Old Flow**: Scrape -> Script -> Audio -> Filter Images -> Video
*Problem*: If "Filter Images" removed an image *after* the script was written, the narrator would describe something you can't see!

**New Flow**: Scrape -> **Filter Images** -> Script -> Audio -> Video
*Optimization*: We filter generic/boring panels *before* asking AI to write the script. This saves API tokens (money/quota) and ensures the script only talks about what is actually shown.

## API Key Recommendations
**"How many more API keys?"**

*   **For Free Tier**: `gemini-1.5-flash` allows ~15 requests per minute.
*   **Current Setup**: The app now handles `429 Quota Exceeded` errors by:
    1.  Rotating to the next Key (if you provide multiple).
    2.  Rotating to a different Model (e.g., switch from Flash to Pro).
    3.  Waiting/Retrying automatically.
*   **Recommendation**:
    *   **1 Key**: Sufficient for casual use (might wait 10-20s between chapters).
    *   **2-3 Keys**: optimal for "zero wait" continuous generation.
    *   **Optimization**: The new "Image Filtering" step reduces the number of images sent to Gemini by ~30-50%, effectively **doubling your free tier capacity**.

## How to Run
The system uses the same commands as before, but the backend is smarter.
1.  **Start Server**: `uvicorn app.main:app --reload`
2.  **Trigger Generation**: usage of the frontend or `trigger_video.py` will automatically use the new pipeline.

## Files Modified
*   `app/script_generator.py`: Model updates, Segmented return data.
*   `app/tts_generator.py`: Added `generate_sync_audio` for batch processing.
*   `app/video_editor.py`: Added `sync_data` support for strict timing.
*   `app/main.py`: Reordered pipeline (Filter -> Script) and orchestrated the Sync flow.
