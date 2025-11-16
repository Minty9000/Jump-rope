import numpy as np
import sounddevice as sd
import librosa
from flask import Flask, jsonify, send_from_directory, request
import threading
import time

### LOAD REFERENCE HIT ###

ref, sr = librosa.load("Jump_hit.wav.m4a", sr=None)
ref_mfcc = librosa.feature.mfcc(y=ref, sr=sr, n_mfcc=13)
ref_vec = np.mean(ref_mfcc, axis=1)

### REAL-TIME SETTINGS ###

FRAME_DURATION = 0.15
FRAME_SIZE = int(sr * FRAME_DURATION)

threshold = 0.87
cooldown_time = 0.25
cooldown_frames = int(cooldown_time / FRAME_DURATION)
counting_enabled = False
jump_count = 0
cooldown_counter = 0


### AUDIO CALLBACK ###

def audio_callback(indata, frames, time_info, status):
    global jump_count, cooldown_counter
    if not counting_enabled:
        return
    if status:
        print(status)
    audio_chunk = indata[:, 0]

    # Gain
    GAIN = 7.0
    audio_chunk = audio_chunk * GAIN

    # 1. RMS
    rms = np.sqrt(np.mean(audio_chunk**2))
    if rms < 0.03:
        return

    # 2. Centroid
    centroid = librosa.feature.spectral_centroid(y=audio_chunk, sr=sr)[0].mean()
    if centroid < 3000:
        return

    # 3. MFCC sim
    chunk_mfcc = librosa.feature.mfcc(y=audio_chunk, sr=sr, n_mfcc=13)
    chunk_vec = np.mean(chunk_mfcc, axis=1)

    corr_value = np.dot(chunk_vec, ref_vec) / (
        np.linalg.norm(chunk_vec) * np.linalg.norm(ref_vec)
    )

    if cooldown_counter > 0:
        cooldown_counter -= 1
        return

    if corr_value > threshold:
        jump_count += 1
        cooldown_counter = cooldown_frames
        print(f"Jump Count: {jump_count}")


### START AUDIO STREAM ###

def start_audio_stream():
    with sd.InputStream(
        callback=audio_callback,
        channels=1,
        samplerate=sr,
        blocksize=FRAME_SIZE
    ):
        print("🔥 Audio thread running...")
        while True:
            time.sleep(0.1)


### FLASK APP ###

app = Flask(__name__, static_folder="static")

is_running = False
start_time = None
elapsed_time = 0
laps = []


def get_elapsed_time():
    if not is_running:
        return elapsed_time
    return elapsed_time + (time.time() - start_time)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/jump_count")
def get_jump():
    return jsonify({"count": jump_count})


@app.route("/timer")
def timer():
    return jsonify({"time": get_elapsed_time()})


@app.route("/laps")
def get_laps():
    return jsonify({"laps": laps})


@app.route("/start", methods=["POST"])
def start_timer():
    global is_running, start_time, counting_enabled
    if not is_running:
        is_running = True
        counting_enabled = True
        start_time = time.time()
        print("START pressed → counting_enabled = True")
    return jsonify({"status": "started"})


@app.route("/stop", methods=["POST"])
def stop_timer():
    global is_running, elapsed_time,counting_enabled
    if is_running:
        elapsed_time = get_elapsed_time()
        is_running = False
        counting_enabled = False  
    return jsonify({"status": "stopped"})


@app.route("/reset", methods=["POST"])
def reset_timer():
    global elapsed_time, is_running, laps, jump_count,counting_enabled
    elapsed_time = 0
    is_running = False
    counting_enabled = False
    laps = []
    jump_count = 0
    return jsonify({"status": "reset"})


@app.route("/lap", methods=["POST"])
def lap():
    laps.append({
        "time": get_elapsed_time(),
        "jumps": jump_count
    })
    return jsonify({"status": "lap_added"})


### RUN EVERYTHING ###

if __name__ == "__main__":
    audio_thread = threading.Thread(target=start_audio_stream, daemon=True)
    audio_thread.start()
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) 

    print("🎧 Listening for jumps... Backend + Web UI running")

    app.run(host="0.0.0.0", port=5001, debug=True)