# Manhwa Recap Video Generator

An automated system that transforms manhwa chapters into professional recap videos with minimal human intervention.

## 🚀 Quick Start

### 1. Start the Server
Double-click `run.bat` or run in terminal:
```bash
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Open the App
Go to: **http://localhost:8000/app**

### 3. Create Your First Recap
1. Paste a manhwa chapter URL (e.g., from Asura Scans)
2. Click "Start Processing"
3. Wait for the magic! ✨

## ✨ Features

- **🔍 Auto Image Extraction** - Scrapes manhwa panels from popular sites
- **✍️ AI Script Generation** - Gemini AI creates engaging narration
- **🎙️ Natural Voiceover** - Edge-TTS generates human-like speech
- **🎬 Video Assembly** - MoviePy creates professional videos with effects
- **📊 Ken Burns Effect** - Subtle zoom/pan for visual interest
- **🎨 Premium UI** - Beautiful dark-themed dashboard

## � Processing Pipeline

The system transforms a manhwa chapter URL into a finished video through five distinct stages:

### Stage 1: Image Extraction (Scraping)
**Module:** `app/scraper.py`

1. **Web Navigation**: Selenium loads the chapter URL
2. **Smart Detection**: Automatically identifies image containers (e.g., `.cha-words`, `.read-container`)
3. **Image Collection**: Downloads all panel images in sequential order
4. **Storage**: Saves to `temp/{manga_name}_{id}/chapter_{n}/images/`

**Output:** Directory of manhwa panel images (PNG/JPG)

### Stage 2: Script Generation (AI Narration)
**Module:** `app/script_generator.py`

1. **Image Batching**: Divides panels into batches (default: 8-10 panels per batch)
2. **Gemini Vision API**: Sends each batch to Gemini AI with a custom prompt
3. **Image-Level Narration**: Gemini analyzes each panel and generates:
   - Engaging narration text (40-60 words)
   - Estimated display duration
   - Dramatic, present-tense storytelling
4. **JSON Output**: Saves structured data to `script_segments.json`

**Key Features:**
- **Smart Batching**: Processes large chapters in manageable chunks
- **API Rotation**: Cycles through multiple Gemini API keys for quota management
- **Error Recovery**: Automatic retry with exponential backoff

**Output:** 
- `script.txt` - Human-readable full script
- `script_segments.json` - Structured JSON with per-image narrations

### Stage 3: Voiceover Generation (TTS)
**Module:** `app/tts_generator.py`

#### Optimized Sync Pipeline (Default)
1. **Segment Processing**: Iterates through each image narration from `script_segments.json`
2. **Parallel Generation**: Uses `asyncio.gather()` with `Semaphore(5)` to generate 5 audio clips simultaneously
3. **Edge-TTS Synthesis**: Converts text to natural speech using Microsoft Edge TTS
4. **Duration Extraction**: Analyzes each audio file to get exact duration
5. **Sync Map Creation**: Builds `sync_map.json` linking audio files to specific images

**Output:**
- `audio_segments/segment_000.mp3`, `segment_001.mp3`, etc.
- `sync_map.json` - Maps each audio file to its corresponding image

**Speed Optimization:** Parallel processing reduces voiceover generation time by ~70%

### Stage 4: Video Assembly (Rendering)
**Module:** `app/video_editor.py`

#### Image Processing
1. **Panel Slicing**: Long vertical panels are intelligently split into 16:9 chunks
2. **Crop-to-Fill**: Each image is resized and center-cropped to fill the frame without distortion
3. **Minimum Duration**: Each visual stays on screen for at least 2.0 seconds (prevents rapid flashing)

#### Video Composition
1. **Load Sync Data**: Reads `sync_map.json` to understand audio-image pairings
2. **Create Clips**: For each segment:
   - Loads the audio file
   - Loads corresponding image(s)
   - Calculates `slice_duration = audio_duration / num_images`
   - Applies `max(2.0s, slice_duration)` to prevent fast transitions
   - Applies crop-to-fill transformation
   - Adds optional Ken Burns effect (slow zoom)
3. **Concatenation**: Combines all clips using `concatenate_videoclips(method="compose")`
4. **Audio Sync**: Merges all audio segments into final soundtrack
5. **Rendering**: Encodes video with optimized settings:
   - Resolution: 720p (1280x720)
   - FPS: 30
   - Codec: H.264 (libx264)
   - Preset: `ultrafast` for speed
   - Audio: AAC, 128kbps

**Output:** Final MP4 video in `output/` directory

### Stage 5: Thumbnail Generation
**Module:** `video_editor.py::generate_thumbnail()`

1. Selects a visually striking panel from the middle of the chapter
2. Overlays manga name and chapter number
3. Saves as `{video_name}_thumb.jpg`

## 🎯 Pipeline Optimizations

### Speed Improvements
- **Parallel TTS**: 5 concurrent audio generations
- **Optimized Batching**: Reduced Gemini API delays (2s between calls)
- **Fast Encoding**: `ultrafast` preset with lower resolution (720p)
- **Total Time**: ~20-30 minutes for a full chapter (previously 60+ minutes)

### Quality Enhancements
- **Crop-to-Fill**: No more stretched/flattened images
- **Minimum Display Time**: Prevents jarring fast cuts
- **Smart Pacing**: Longer narrations (40-60 words) ensure visuals have time to breathe
- **Adaptive Zoom**: Slower Ken Burns effect for short clips

### Reliability Features
- **API Key Rotation**: Automatically cycles through 11 Gemini API keys
- **Model Fallback**: Tries multiple Gemini models (`2.0-flash`, `2.5-flash`, `2.5-pro`)
- **Retry Logic**: Exponential backoff for rate limits
- **Error Handling**: Graceful degradation if individual components fail

## 📊 Data Flow Diagram

```
URL Input
   ↓
[Scraper] → images/panel_001.jpg, panel_002.jpg...
   ↓
[Script Generator] → script_segments.json
   ↓                  (narration + duration per image)
[TTS Generator] → audio_segments/segment_000.mp3...
   ↓              + sync_map.json
[Video Editor] → Final MP4
   ↓
Output Video + Thumbnail
```

## 🔍 File Structure During Processing

```
temp/
└── {Manga_Name}_{ID}/
    └── chapter_{N}/
        ├── images/
        │   ├── panel_001.jpg
        │   ├── panel_002.jpg
        │   └── ...
        ├── audio_segments/
        │   ├── segment_000.mp3
        │   ├── segment_001.mp3
        │   └── ...
        ├── script.txt
        ├── script_segments.json
        └── sync_map.json

output/
├── {Manga_Name}_Chapter_{N}.mp4
└── {Manga_Name}_Chapter_{N}_thumb.jpg
```

## �📁 Project Structure

```
manhwa-recap/
├── app/
│   ├── main.py              # FastAPI server
│   ├── scraper.py           # Web scraping
│   ├── script_generator.py  # Gemini AI
│   ├── tts_generator.py     # Edge-TTS
│   └── video_editor.py      # MoviePy
├── frontend/
│   ├── index.html           # Dashboard UI
│   ├── styles.css           # Styling
│   └── app.js               # JavaScript
├── config/
│   └── settings.json        # Configuration
├── temp/                    # Processing files
├── output/                  # Final videos
├── requirements.txt         # Dependencies
└── run.bat                  # Start script
```

## ⚙️ Configuration

Edit `config/settings.json`:
```json
{
  "gemini_api_key": "YOUR_API_KEY",
  "default_voice": "en-US-GuyNeural",
  "speech_rate": 1.0,
  "ken_burns_enabled": true
}
```

## 🎤 Available Voices

| Voice | Description |
|-------|-------------|
| en-US-GuyNeural | American Male |
| en-US-ChristopherNeural | American Male |
| en-US-JennyNeural | American Female |
| en-US-AriaNeural | American Female |
| en-GB-RyanNeural | British Male |
| en-GB-SoniaNeural | British Female |

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scrape` | POST | Extract images from URL |
| `/api/generate-script` | POST | Generate narration |
| `/api/generate-voice` | POST | Create voiceover |
| `/api/create-video` | POST | Render video |
| `/api/process` | POST | Full automation |
| `/api/projects` | GET | List all projects |

## 🔧 Requirements

- Python 3.10+
- Chrome/Chromium (for Selenium)
- FFmpeg (included with MoviePy)

## 📝 Supported Websites

- Asura Scans
- Reaper Scans
- Flame Scans
- And many more...

## ⚠️ Disclaimer

This tool is for educational purposes. Please support official releases and respect copyright laws.

---

Made with ❤️ for Manhwa Fans
