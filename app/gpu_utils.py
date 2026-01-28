"""
GPU Detection and Configuration Utilities
Detects NVIDIA GPU availability and returns optimal encoding settings
"""
import subprocess
import logging

logger = logging.getLogger(__name__)

def detect_nvidia_gpu():
    """
    Detect if NVIDIA GPU with NVENC support is available
    Returns: (has_gpu, gpu_name)
    """
    try:
        # Try nvidia-smi command
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            gpu_name = result.stdout.strip().split('\n')[0]
            logger.info(f"✓ NVIDIA GPU detected: {gpu_name}")
            return True, gpu_name
        
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.debug(f"NVIDIA GPU detection failed: {e}")
    
    return False, None


def get_optimal_codec():
    """
    Returns optimal video codec based on GPU availability
    Returns: (codec, preset, description)
    """
    has_gpu, gpu_name = detect_nvidia_gpu()
    
    if has_gpu:
        # NVENC available - use GPU encoding
        return {
            'codec': 'h264_nvenc',
            'preset': 'p7',  # Highest quality preset for NVENC (p1-p7)
            'gpu_name': gpu_name,
            'description': f'GPU-accelerated encoding with {gpu_name}'
        }
    else:
        # Fallback to CPU encoding
        return {
            'codec': 'libx264',
            'preset': 'medium',  # Balanced preset for CPU
            'gpu_name': None,
            'description': 'CPU encoding (no GPU detected)'
        }


def get_encoding_params(use_gpu=True, bitrate='4500k'):
    """
    Get complete encoding parameters
    """
    codec_info = get_optimal_codec() if use_gpu else {
        'codec': 'libx264',
        'preset': 'medium',
        'gpu_name': None,
        'description': 'CPU encoding (user preference)'
    }
    
    params = {
        'codec': codec_info['codec'],
        'preset': codec_info['preset'],
        'bitrate': bitrate,
        'audio_codec': 'aac',
        'audio_bitrate': '192k',
        'threads': 8,
        'description': codec_info['description']
    }
    
    logger.info(f"Encoding config: {params['description']}")
    logger.info(f"  Codec: {params['codec']}, Preset: {params['preset']}")
    logger.info(f"  Video bitrate: {params['bitrate']}, Audio: {params['audio_bitrate']}")
    
    return params


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n" + "="*60)
    print("GPU Detection Test")
    print("="*60)
    
    has_gpu, gpu_name = detect_nvidia_gpu()
    print(f"\nNVIDIA GPU: {'Yes' if has_gpu else 'No'}")
    if has_gpu:
        print(f"GPU Name: {gpu_name}")
    
    print("\nOptimal Encoding Settings:")
    params = get_encoding_params()
    for key, value in params.items():
        if key != 'description':
            print(f"  {key}: {value}")
    
    print("="*60)
