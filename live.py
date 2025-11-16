import numpy as np
import sounddevice as sd
import librosa

### LOAD REFERENCE HIT ###

ref, sr = librosa.load("Jump_hit.wav.m4a", sr=None)
ref_mfcc = librosa.feature.mfcc(y=ref, sr=sr, n_mfcc=13)
ref_vec = np.mean(ref_mfcc, axis=1)  # <-- FIXED

### REAL-TIME SETTINGS ###

FRAME_DURATION = 0.15   # seconds of audio per analysis frame
FRAME_SIZE = int(sr * FRAME_DURATION)

threshold = 0.75
cooldown_time = 0.25  # seconds
cooldown_frames = int(cooldown_time / FRAME_DURATION)

jump_count = 0
cooldown_counter = 0

print("🎧 Listening for jumps... (Ctrl+C to stop)")

### CALLBACK: RUNS FOR EACH AUDIO CHUNK ###

def audio_callback(indata, frames, time, status):
    global jump_count, cooldown_counter

    if status:
        print(status)

    audio_chunk = indata[:, 0]
    GAIN = 5.0   # try between 3.0 and 10.0
    audio_chunk = audio_chunk * GAIN

    ### 1. RMS ENERGY FILTER (rope hits are LOUD)
    rms = np.sqrt(np.mean(audio_chunk**2))
    if rms < 0.03:   # increase this if still too sensitive
        return
    
    ### 2. SPECTRAL CENTROID (rope hits are bright + sharp)
    centroid = librosa.feature.spectral_centroid(y=audio_chunk, sr=sr)[0].mean()
    if centroid < 3000:     # rope hits typically over 4k but adjust later
        return

    ### 3. MFCC SIMILARITY
    chunk_mfcc = librosa.feature.mfcc(y=audio_chunk, sr=sr, n_mfcc=13)
    chunk_vec = np.mean(chunk_mfcc, axis=1)

    corr_value = np.dot(chunk_vec, ref_vec) / (
        np.linalg.norm(chunk_vec) * np.linalg.norm(ref_vec)
    )

    # Cooldown so 1 hit = 1 jump
    if cooldown_counter > 0:
        cooldown_counter -= 1
        return

    ### FINAL DETECTION
    if corr_value > threshold:
        jump_count += 1
        cooldown_counter = cooldown_frames
        print(f"Jump Count: {jump_count}")


### START STREAM ###

with sd.InputStream(callback=audio_callback, channels=1, samplerate=sr, blocksize=FRAME_SIZE):
    print("🔥 Live Jump Counter Active!")
    print("Start jumping...")
    import time
    while True:
        time.sleep(0.1)