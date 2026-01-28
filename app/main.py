"""
FastAPI Backend Server for Manhwa Recap Generator
Main API endpoints for the automation pipeline
"""

import os
import json
import uuid
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import our modules
from app.scraper import scrape_chapter
from app.script_generator import ScriptGenerator
from app.tts_generator import TTSGenerator, AVAILABLE_VOICES
from app.video_editor import VideoEditor
from app.image_filter import ImageFilter

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Manhwa Recap Generator",
    description="Automated manhwa chapter to video recap generator",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directories
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_PATH = BASE_DIR / "config" / "settings.json"

# Create directories
TEMP_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Load config
def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    return {}

config = load_config()

import hashlib

# In-memory project storage
projects = {}

def scan_local_projects():
    """Scan temp directory for existing projects"""
    logger.info("Scanning for local projects...")
    count = 0
    
    if not TEMP_DIR.exists():
        return count
        
    # Walk through temp dir
    # Structure: temp/MangaName/chapter_X/images
    for manga_dir in TEMP_DIR.iterdir():
        if not manga_dir.is_dir():
            continue
            
        for chapter_dir in manga_dir.iterdir():
            if not chapter_dir.is_dir() or not chapter_dir.name.startswith('chapter_'):
                continue
                
            # Check for images dir
            images_dir = chapter_dir / "images"
            if not images_dir.exists() or not any(images_dir.iterdir()):
                continue
                
            # Found a valid project structure
            manga_name = manga_dir.name
            # Try to restore original name from directory name (usually Safe Name)
            # We'll just use the directory name as a fallback or prettify it
            display_name = manga_name.replace('_', ' ')
            
            chapter = chapter_dir.name.replace('chapter_', '')
            
            # Generate consistent ID based on path
            unique_str = f"{manga_name}_{chapter}"
            project_id = hashlib.md5(unique_str.encode()).hexdigest()[:8]
            
            # Check what steps are done
            steps_completed = ["scrape"]
            status = "scraped"
            
            project_data = {
                "id": project_id,
                "url": "local_restored", # We don't know the original URL
                "manga_name": display_name,
                "chapter": chapter,
                "images_dir": str(images_dir),
                "image_count": len(list(images_dir.glob('*.*'))),
                "created_at": datetime.fromtimestamp(chapter_dir.stat().st_mtime).isoformat(),
                "steps_completed": steps_completed,
                "status": status
            }
            
            # Check for script
            script_path = chapter_dir / "script.txt"
            if script_path.exists():
                with open(script_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                project_data['script_path'] = str(script_path)
                project_data['script'] = content
                project_data['word_count'] = len(content.split())
                project_data['estimated_duration'] = project_data['word_count'] / 150
                project_data['steps_completed'].append("script")
                project_data['status'] = "script_generated"
                
                # Check for segments
                segments_path = chapter_dir / "script_segments.json"
                if segments_path.exists():
                    try:
                        with open(segments_path, 'r', encoding='utf-8') as f:
                            project_data['segments'] = json.load(f)
                    except:
                        pass
            
            # Check for audio
            # Voiceover might be in the chapter dir or images parent?
            # Script generator saves script in chapter dir. TTS saves in script dir by default.
            voice_path = chapter_dir / "voiceover.mp3"
            if voice_path.exists():
                project_data['audio_path'] = str(voice_path)
                project_data['steps_completed'].append("voiceover")
                project_data['status'] = "voiceover_generated"
                
            # Check for sync map
            sync_map_path = chapter_dir / "sync_map.json"
            if sync_map_path.exists():
                try:
                    with open(sync_map_path, 'r', encoding='utf-8') as f:
                        project_data['sync_data'] = json.load(f)
                except:
                    pass
            
            # Check for video
            # Video is saved to OUTPUT_DIR, filename depends on safe name
            safe_name = manga_name.replace(' ', '_') # Directory name is already "safe-ish"
            video_name = f"{manga_name}_Chapter_{chapter}.mp4"
            # Directory name might differ slightly from safe_name logic used in create_video
            # But let's try to find it in OUTPUT_DIR matching pattern
            
            # Simple check in output dir
            for vid in OUTPUT_DIR.glob(f"*{chapter}.mp4"):
                if manga_name.lower().replace(' ', '') in vid.name.lower().replace('_', '').replace(' ', ''):
                    project_data['video_path'] = str(vid)
                    project_data['steps_completed'].append("video")
                    project_data['status'] = "completed"
                    break
            
            projects[project_id] = project_data
            count += 1
            
    logger.info(f"Restored {count} projects")
    return count

# Initial scan
scan_local_projects()


# Request models
class ScrapeRequest(BaseModel):
    url: str
    project_name: Optional[str] = None

class ScriptRequest(BaseModel):
    project_id: str
    custom_intro: Optional[str] = None
    custom_outro: Optional[str] = None

class VoiceoverRequest(BaseModel):
    project_id: str
    voice: Optional[str] = "en-US-GuyNeural"
    rate: Optional[float] = 1.0

class VideoRequest(BaseModel):
    project_id: str
    ken_burns: Optional[bool] = True
    transition_duration: Optional[float] = 0.5

class FullProcessRequest(BaseModel):
    url: str
    voice: Optional[str] = "en-US-GuyNeural"
    rate: Optional[float] = 1.0
    ken_burns: Optional[bool] = True

class UpdateScriptRequest(BaseModel):
    project_id: str
    script: str


# API Endpoints

@app.get("/")
async def root():
    return {"message": "Manhwa Recap Generator API", "version": "1.0.0"}


@app.get("/api/voices")
async def get_voices():
    """Get available TTS voices"""
    return AVAILABLE_VOICES


@app.get("/api/projects")
async def get_projects():
    """Get all projects"""
    return list(projects.values())


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return projects[project_id]


@app.post("/api/scrape")
async def scrape_images(request: ScrapeRequest):
    """Step 1: Scrape images from manhwa chapter URL"""
    try:
        # Create project ID
        project_id = str(uuid.uuid4())[:8]
        
        logger.info(f"Starting scrape for project {project_id}: {request.url}")
        
        # Scrape chapter
        result = scrape_chapter(request.url, str(TEMP_DIR))
        
        # Create project entry
        projects[project_id] = {
            "id": project_id,
            "url": request.url,
            "manga_name": result['manga_info']['manga_name'],
            "chapter": result['manga_info']['chapter'],
            "images_dir": result['images_dir'],
            "image_count": result['image_count'],
            "status": "scraped",
            "created_at": datetime.now().isoformat(),
            "steps_completed": ["scrape"]
        }
        
        return {
            "project_id": project_id,
            "manga_name": result['manga_info']['manga_name'],
            "chapter": result['manga_info']['chapter'],
            "image_count": result['image_count'],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate-script")
async def generate_script(request: ScriptRequest):
    """Step 2: Generate narration script using Gemini AI"""
    if request.project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[request.project_id]
    
    try:
        logger.info(f"Generating script for project {request.project_id}")
        
        # Reload config from disk to pick up any changes
        fresh_config = load_config()
        
        # Prepare API keys
        keys = fresh_config.get('gemini_api_keys')
        if not keys and fresh_config.get('gemini_api_key'):
            keys = [fresh_config.get('gemini_api_key')]

        # Initialize generator
        generator = ScriptGenerator(
            api_keys=keys,
            config_path=str(CONFIG_PATH)
        )
        
        # Generate script
        result = generator.generate_script(
            project['images_dir'],
            project['manga_name'],
            project['chapter']
        )
        
        # Update project
        project['script_path'] = result['script_path']
        project['script'] = result['full_script']
        project['word_count'] = result['word_count']
        project['estimated_duration'] = result['estimated_duration']
        # Store segments if present
        if 'segments' in result:
             project['segments'] = result['segments']

        project['status'] = "script_generated"
        if "script" not in project['steps_completed']:
            project['steps_completed'].append("script")
        
        return {
            "project_id": request.project_id,
            "script": result['full_script'],
            "word_count": result['word_count'],
            "estimated_duration": result['estimated_duration'],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Script generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/update-script")
async def update_script(request: UpdateScriptRequest):
    """Update the script for a project"""
    if request.project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[request.project_id]
    
    # Update script in memory and file
    project['script'] = request.script
    project['word_count'] = len(request.script.split())
    project['estimated_duration'] = project['word_count'] / 150
    
    # Save to file
    if 'script_path' in project:
        with open(project['script_path'], 'w', encoding='utf-8') as f:
            f.write(request.script)
    
    return {"status": "success", "message": "Script updated"}


@app.post("/api/generate-voice")
async def generate_voiceover(request: VoiceoverRequest):
    """Step 3: Generate TTS voiceover"""
    if request.project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[request.project_id]
    
    if 'script_path' not in project:
        raise HTTPException(status_code=400, detail="Script not generated yet")
    
    try:
        logger.info(f"Generating voiceover for project {request.project_id}")
        
        # Initialize TTS
        tts = TTSGenerator(voice=request.voice, rate=request.rate)
        
        # Check for segments to do PERFECT SYNC
        segments_path = Path(project['script_path']).parent / "script_segments.json"
        
        if segments_path.exists():
            logger.info("Found segments file, using Optimized Sync Pipeline")
            with open(segments_path, 'r', encoding='utf-8') as f:
                segments = json.load(f)
                
            # Create audio dir
            audio_dir = Path(project['script_path']).parent / "audio_segments"
            
            # Generate sync audio
            audio_results = await tts.generate_sync_audio(segments, str(audio_dir))
            
            # Create Sync Map (merging images from segments and audio from results)
            # Both lists should be sorted by batch_index
            sync_map = []
            
            # Index segments by batch_index
            seg_map = {s['batch_index']: s for s in segments}
            
            for aud in audio_results:
                batch_idx = aud['batch_index']
                if batch_idx in seg_map:
                    sync_map.append({
                        'audio_path': aud['audio_path'],
                        'images': seg_map[batch_idx]['images'],
                        'batch_index': batch_idx
                    })
            
            # Save sync map
            sync_map_path = Path(project['script_path']).parent / "sync_map.json"
            with open(sync_map_path, 'w', encoding='utf-8') as f:
                json.dump(sync_map, f, indent=2)
                
            project['sync_data'] = sync_map
            project['audio_path'] = str(audio_dir) # Just placeholder or dir
            # We still need a full audio path for the legacy or just fallback?
            # Let's generate a full one too for simple playback if needed?
        
            # Update project
            project['voice'] = request.voice
            project['status'] = "voiceover_generated"
            if "voiceover" not in project['steps_completed']:
                project['steps_completed'].append("voiceover")
                
            return {
                "project_id": request.project_id,
                "audio_path": "Optimized Sync Audio Generated",
                "file_size": 0,
                "voice": request.voice,
                "status": "success",
                "sync_mode": True
            }
            
        else:
            # LEGACY FLOW
            result = await tts.generate_from_file(project['script_path'])
            
            # Update project
            project['audio_path'] = result['audio_path']
            project['voice'] = request.voice
            project['status'] = "voiceover_generated"
            if "voiceover" not in project['steps_completed']:
                project['steps_completed'].append("voiceover")
            
            return {
                "project_id": request.project_id,
                "audio_path": result['audio_path'],
                "file_size": result['file_size'],
                "voice": request.voice,
                "status": "success",
                "sync_mode": False
            }
        
    except Exception as e:
        logger.error(f"Voiceover generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/create-video")
async def create_video(request: VideoRequest):
    """Step 4: Create final video"""
    if request.project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[request.project_id]
    
    # Relaxed check: if sync_data exists, we don't strictly need audio_path?
    if 'audio_path' not in project and 'sync_data' not in project:
        raise HTTPException(status_code=400, detail="Voiceover not generated yet")
    
    try:
        logger.info(f"Creating video for project {request.project_id}")
        
        # Prepare output path
        safe_name = project['manga_name'].replace(' ', '_')
        output_filename = f"{safe_name}_Chapter_{project['chapter']}.mp4"
        output_path = str(OUTPUT_DIR / output_filename)
        
        # Initialize editor with config
        video_config = {
            **config,
            'ken_burns_enabled': request.ken_burns,
            'transition_duration': request.transition_duration
        }
        editor = VideoEditor(video_config)
        
        # Filter images logic (kept same as before)
        # Image filtering disabled per user request to match README flow
        # Use all images found in the directory
        selected_images = None

        
        # Create video
        result = editor.create_video(
            project['images_dir'],
            project.get('audio_path'), # Can be None if using sync_data
            output_path,
            project['manga_name'],
            project['chapter'],
            audio_segments=None, # Deprecated in favor of sync_data
            selected_images=selected_images,
            sync_data=project.get('sync_data') # PASS SYNC DATA
        )
        
        if not result:
            raise ValueError("Video creation failed (no result returned)")
        
        # Generate thumbnail
        thumb_path = output_path.replace('.mp4', '_thumb.jpg')
        editor.generate_thumbnail(
            project['images_dir'],
            thumb_path,
            project['manga_name'],
            project['chapter']
        )
        
        # Update project
        project['video_path'] = result['video_path']
        project['thumbnail_path'] = thumb_path
        project['duration'] = result['duration']
        project['video_size'] = result['file_size']
        project['status'] = "completed"
        project['completed_at'] = datetime.now().isoformat()
        if "video" not in project['steps_completed']:
            project['steps_completed'].append("video")
        
        return {
            "project_id": request.project_id,
            "video_path": result['video_path'],
            "thumbnail_path": thumb_path,
            "duration": result['duration'],
            "file_size": result['file_size'],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Video creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process")
async def full_process(request: FullProcessRequest, background_tasks: BackgroundTasks):
    """Full automation: URL to finished video"""
    try:
        project_id = str(uuid.uuid4())[:8]
        
        logger.info(f"Starting full process for project {project_id}")
        
        # Initialize project
        projects[project_id] = {
            "id": project_id,
            "url": request.url,
            "status": "processing",
            "created_at": datetime.now().isoformat(),
            "steps_completed": [],
            "current_step": "scraping"
        }
        
        # Step 1: Scrape
        projects[project_id]["current_step"] = "scraping"
        scrape_result = scrape_chapter(request.url, str(TEMP_DIR))
        
        projects[project_id].update({
            "manga_name": scrape_result['manga_info']['manga_name'],
            "chapter": scrape_result['manga_info']['chapter'],
            "images_dir": scrape_result['images_dir'],
            "image_count": scrape_result['image_count'],
        })
        projects[project_id]["steps_completed"].append("scrape")
        
        # Step 2: Image Filtering (SKIPPED per user request)
        # projects[project_id]["current_step"] = "filtering_images"
        # We skip filtering and proceed directly to script generation with ALL images


        # Step 3: Generate Script (Now on filtered images)
        projects[project_id]["current_step"] = "generating_script"
        
        # Reload config from disk to pick up any changes
        fresh_config = load_config()
        
        # Prepare API keys
        keys = fresh_config.get('gemini_api_keys')
        if not keys and fresh_config.get('gemini_api_key'):
            keys = [fresh_config.get('gemini_api_key')]

        generator = ScriptGenerator(
            api_keys=keys,
            config_path=str(CONFIG_PATH)
        )
        script_result = generator.generate_script(
            scrape_result['images_dir'],
            scrape_result['manga_info']['manga_name'],
            scrape_result['manga_info']['chapter']
        )
        
        projects[project_id].update({
            "script_path": script_result['script_path'],
            "script": script_result['full_script'],
            "word_count": script_result['word_count'],
        })
        if 'segments' in script_result:
             projects[project_id]['segments'] = script_result['segments']
        projects[project_id]["steps_completed"].append("script")
        
        # Step 4: Generate Voiceover (Sync)
        projects[project_id]["current_step"] = "generating_voiceover"
        tts = TTSGenerator(voice=request.voice, rate=request.rate)
        
        # Check for segments to do PERFECT SYNC
        segments_path = Path(script_result['script_path']).parent / "script_segments.json"
        voice_result = {}
        
        if segments_path.exists():
            # Sync Logic
            with open(segments_path, 'r', encoding='utf-8') as f:
                segments = json.load(f)
            audio_dir = Path(script_result['script_path']).parent / "audio_segments"
            audio_results = await tts.generate_sync_audio(segments, str(audio_dir))
            
            sync_map = []
            seg_map = {s['batch_index']: s for s in segments}
            for aud in audio_results:
                batch_idx = aud['batch_index']
                if batch_idx in seg_map:
                    sync_map.append({
                        'audio_path': aud['audio_path'],
                        'images': seg_map[batch_idx]['images'],
                        'batch_index': batch_idx
                    })
                    
            sync_map_path = Path(script_result['script_path']).parent / "sync_map.json"
            with open(sync_map_path, 'w', encoding='utf-8') as f:
                json.dump(sync_map, f, indent=2)
                
            projects[project_id]['sync_data'] = sync_map
            projects[project_id]['audio_path'] = str(audio_dir)
            voice_result = {'audio_path': str(audio_dir), 'segments': segments} # Pseudo result
        else:
            # Legacy
            voice_result = await tts.generate_from_file(script_result['script_path'])
            projects[project_id]["audio_path"] = voice_result['audio_path']

        projects[project_id]["voice"] = request.voice
        projects[project_id]["steps_completed"].append("voiceover")
        
        # Step 5: Create Video
        projects[project_id]["current_step"] = "creating_video"
        safe_name = scrape_result['manga_info']['manga_name'].replace(' ', '_')
        output_filename = f"{safe_name}_Chapter_{scrape_result['manga_info']['chapter']}.mp4"
        output_path = str(OUTPUT_DIR / output_filename)
        
        video_config = {
            **config,
            'ken_burns_enabled': request.ken_burns,
        }
        editor = VideoEditor(video_config)
        video_result = editor.create_video(
            scrape_result['images_dir'],
            projects[project_id].get('audio_path'),
            output_path,
            scrape_result['manga_info']['manga_name'],
            scrape_result['manga_info']['chapter'],
            audio_segments=voice_result.get('segments'), # Legacy
            selected_images=None, # Already filtered at step 2
            sync_data=projects[project_id].get('sync_data')
        )
        
        thumb_path = output_path.replace('.mp4', '_thumb.jpg')
        editor.generate_thumbnail(
            scrape_result['images_dir'],
            thumb_path,
            scrape_result['manga_info']['manga_name'],
            scrape_result['manga_info']['chapter']
        )
        
        projects[project_id].update({
            "video_path": video_result['video_path'],
            "thumbnail_path": thumb_path,
            "duration": video_result['duration'],
            "video_size": video_result['file_size'],
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "current_step": "completed"
        })
        projects[project_id]["steps_completed"].append("video")
        
        return {
            "project_id": project_id,
            "manga_name": scrape_result['manga_info']['manga_name'],
            "chapter": scrape_result['manga_info']['chapter'],
            "video_path": video_result['video_path'],
            "thumbnail_path": thumb_path,
            "duration": video_result['duration'],
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Full process failed: {e}")
        if project_id in projects:
            projects[project_id]["status"] = "failed"
            projects[project_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and its files"""
    if project_id not in projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = projects[project_id]
    
    # Clean up files
    if 'images_dir' in project:
        shutil.rmtree(os.path.dirname(project['images_dir']), ignore_errors=True)
    
    if 'video_path' in project and os.path.exists(project['video_path']):
        os.remove(project['video_path'])
    
    if 'thumbnail_path' in project and os.path.exists(project['thumbnail_path']):
        os.remove(project['thumbnail_path'])
    
    del projects[project_id]
    
    return {"status": "success", "message": "Project deleted"}


@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    # Return config without sensitive data
    safe_config = {k: v for k, v in config.items() if 'key' not in k.lower()}
    safe_config['has_gemini_key'] = bool(config.get('gemini_api_key') or config.get('gemini_api_keys'))
    return safe_config


@app.post("/api/config")
async def update_config(new_config: dict):
    """Update configuration"""
    global config
    config.update(new_config)
    
    # Save to file
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    return {"status": "success", "message": "Configuration updated"}


# Serve static files for frontend
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
    
    @app.get("/app")
    async def serve_frontend():
        return FileResponse(str(frontend_dir / "index.html"))
    
    @app.get("/styles.css")
    async def serve_css():
        return FileResponse(str(frontend_dir / "styles.css"), media_type="text/css")
    
    @app.get("/app.js")
    async def serve_js():
        return FileResponse(str(frontend_dir / "app.js"), media_type="application/javascript")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

