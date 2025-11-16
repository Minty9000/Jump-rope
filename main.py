import numpy as np
import librosa

# Load both sounds
ref, sr = librosa.load("Jump_hit.wav.m4a", sr=None)
test, _ = librosa.load("Test_session.wav.m4a", sr=sr)

# Compute MFCC
ref_mfcc = librosa.feature.mfcc(y=ref, sr=sr, n_mfcc=13)
test_mfcc = librosa.feature.mfcc(y=test, sr=sr, n_mfcc=13)

# Cross-correlation
corr = np.correlate(
    np.mean(test_mfcc, axis=0),
    np.mean(ref_mfcc, axis=0),
    mode="valid"
)

corr = corr / np.max(corr)
threshold = 0.76  # slightly lower or higher depending on your audio

# Raw hits
raw_hits = np.where(corr > threshold)[0]

# --- FIX: consolidate hits ---
jump_count = 0
cooldown = int(0.2 * sr / 512)  
# 0.2 seconds converted into MFCC frames
# (512 is the default hop_length used by librosa for MFCC)

last_hit = -cooldown

for h in raw_hits:
    if h - last_hit > cooldown:
        jump_count += 1
        last_hit = h

print(f"Detected jumps: {jump_count}")