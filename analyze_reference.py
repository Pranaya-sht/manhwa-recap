"""
Analyze reference video to understand quality benchmarks
"""
from moviepy.editor import VideoFileClip, AudioFileClip
import json
from pathlib import Path

def analyze_video(video_path):
    """Extract detailed metadata from reference video"""
    print(f"Analyzing: {video_path}")
    
    clip = VideoFileClip(video_path)
    
    analysis = {
        "video": {
            "duration": clip.duration,
            "fps": clip.fps,
            "size": clip.size,  # (width, height)
            "aspect_ratio": f"{clip.size[0]}:{clip.size[1]}",
            "total_frames": int(clip.fps * clip.duration)
        },
        "audio": {
            "fps": clip.audio.fps if clip.audio else None,
            "nchannels": clip.audio.nchannels if clip.audio else None,
            "duration": clip.audio.duration if clip.audio else None
        }
    }
    
    # Extract sample frames
    print("\nExtracting sample frames...")
    frame_times = [0, clip.duration * 0.25, clip.duration * 0.5, clip.duration * 0.75]
    
    for i, t in enumerate(frame_times):
        if t < clip.duration:
            frame = clip.get_frame(t)
            from PIL import Image
            img = Image.fromarray(frame)
            img.save(f"temp_reference_frame_{i}.jpg", quality=95)
            print(f"  Saved frame at {t:.1f}s")
    
    clip.close()
    
    # Print analysis
    print("\n" + "="*60)
    print("REFERENCE VIDEO ANALYSIS")
    print("="*60)
    print(f"\nVideo Properties:")
    print(f"  Resolution: {analysis['video']['size'][0]}x{analysis['video']['size'][1]}")
    print(f"  FPS: {analysis['video']['fps']}")
    print(f"  Duration: {analysis['video']['duration']:.2f}s ({analysis['video']['duration']/60:.1f}m)")
    print(f"  Total Frames: {analysis['video']['total_frames']}")
    
    if analysis['audio']['fps']:
        print(f"\nAudio Properties:")
        print(f"  Sample Rate: {analysis['audio']['fps']} Hz")
        print(f"  Channels: {analysis['audio']['nchannels']}")
        print(f"  Duration: {analysis['audio']['duration']:.2f}s")
    
    # Calculate average seconds per frame visible
    avg_frame_display = analysis['video']['duration'] / analysis['video']['total_frames']
    print(f"\nPacing:")
    print(f"  Average display per frame: {avg_frame_display:.3f}s")
    
    # Save to JSON
    with open("reference_video_analysis.json", "w") as f:
        json.dump(analysis, f, indent=2)
    
    print(f"\n✓ Analysis saved to reference_video_analysis.json")
    print("="*60)
    
    return analysis

if __name__ == "__main__":
    video_path = "recap.mp4"
    if Path(video_path).exists():
        analyze_video(video_path)
    else:
        print(f"Error: {video_path} not found!")
