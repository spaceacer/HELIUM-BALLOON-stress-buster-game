# sound.py
import math
import random
from array import array
import pygame

_cache = {}
_enabled = True
_hiss_channel = None  # Dedicated channel for the looping gas flow

def init(frequency=44100, size=-16, channels=1, buffer=512):
    """Adaptive mixer initialization targeting native modern hardware alignment."""
    global _enabled
    try:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
    except Exception:
        pass
        
    try:
        pygame.mixer.pre_init(frequency, size, channels, buffer)
        pygame.mixer.init()
        _enabled = True
    except Exception:
        try:
            pygame.mixer.init(44100, -16, 2, 512)
            _enabled = True
        except Exception:
            _enabled = False
    return _enabled

def _sample_rate():
    init_info = pygame.mixer.get_init()
    return init_info[0] if init_info else 44100

def _make_looping_hiss(volume=0.35):
    """Generates a perfectly seamless, looping air-flow texture using deep LPF filtering."""
    rate = _sample_rate()
    duration = 1.0  # 1 second loop container
    n = max(1, int(rate * duration))
    
    max_amp = 32767 * volume
    sample_array = array('h', [0] * n)
    filter_state = 0.0
    
    for i in range(n):
        raw_noise = random.uniform(-1.0, 1.0)
        # Deep low-pass dampener (0.93 history) to emulate soft, structural pneumatic air pressure
        filter_state = 0.07 * raw_noise + 0.93 * filter_state
        
        sample_val = int(filter_state * max_amp)
        sample_array[i] = max(-32768, min(32767, sample_val))
        
    return pygame.mixer.Sound(buffer=sample_array.tobytes())

def _make_pop_sound(volume=0.45):
    """Synthesizes the burst transient using native array buffers to keep it loud and crisp."""
    rate = _sample_rate()
    duration = 0.14
    n = max(1, int(rate * duration))
    
    max_amp = 32767 * volume
    sample_array = array('h', [0] * n)
    
    for i in range(n):
        decay = math.exp(-i / (n * 0.15))
        raw_noise = random.uniform(-1.0, 1.0)
        sample_val = int(max_amp * decay * raw_noise)
        sample_array[i] = max(-32768, min(32767, sample_val))
        
    return pygame.mixer.Sound(buffer=sample_array.tobytes())

def start_inflate():
    """Starts playing the continuous gas flow hiss seamlessly on loop if not already running."""
    global _hiss_channel
    if not _enabled:
        return
        
    # If already playing, do nothing to prevent multi-trigger stuttering
    if _hiss_channel and _hiss_channel.get_busy():
        return
        
    try:
        if 'hiss_loop' not in _cache:
            _cache['hiss_loop'] = _make_looping_hiss()
            
        # Loops=-1 tells Pygame to play the sound infinitely until told to halt
        _hiss_channel = _cache['hiss_loop'].play(loops=-1)
    except Exception:
        pass

def stop_inflate():
    """Instantly kills or fades out the gas hiss channel when spacebar is released."""
    global _hiss_channel
    if not _enabled or not _hiss_channel:
        return
        
    try:
        if _hiss_channel.get_busy():
            # A rapid 45ms fadeout eliminates abrupt click/pop hardware artifacts
            _hiss_channel.fadeout(45)
    except Exception:
        pass
    _hiss_channel = None

def play_pop():
    """Triggers the burst transient instantly on a clean audio lane."""
    if not _enabled:
        return
    try:
        if 'pop' not in _cache:
            _cache['pop'] = _make_pop_sound()
        _cache['pop'].play()
    except Exception:
        pass