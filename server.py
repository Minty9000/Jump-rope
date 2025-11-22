import numpy as np
import os

USE_AUDIO = not os.environ.get("ON_RENDER", "false") == "true"
print("ON_RENDER:", os.environ.get("ON_RENDER"))
print("USE_AUDIO:", USE_AUDIO)

if USE_AUDIO:
    import sounddevice as sd
    import librosa
else:
    sd = None
    librosa = None
from flask import Flask, jsonify, send_from_directory, request
import threading
import time

### LOAD REFERENCE HIT ###

ref = None
sr = None
ref_vec = None

if USE_AUDIO:
    print("🎵 Loading reference jump sound...")
    try:
        ref, sr = librosa.load("Jump_hit.wav.m4a", sr=None)
        ref_mfcc = librosa.feature.mfcc(y=ref, sr=sr, n_mfcc=13)
        ref_vec = np.mean(ref_mfcc, axis=1)
    except Exception as e:
        print("❌ Error loading reference audio:", e)
else:
    print("🌐 Render environment detected — skipping audio load")

### REAL-TIME SETTINGS ###

if USE_AUDIO and sr is not None:
    FRAME_DURATION = 0.15
    FRAME_SIZE = int(sr * FRAME_DURATION)

    threshold = 0.87
    cooldown_time = 0.27
    cooldown_frames = int(cooldown_time / FRAME_DURATION)
else:
    FRAME_DURATION = 0
    FRAME_SIZE = 0
    threshold = 0
    cooldown_time = 0
    cooldown_frames = 0

counting_enabled = False
jump_count = 0
cooldown_counter = 0
last_jump_time = time.time()


### AUDIO CALLBACK ###

def audio_callback(indata, frames, time_info, status):
    global jump_count, cooldown_counter, counting_enabled

    if status:
        print(status)

    # If we’re not in “counting” mode (timer not running), ignore audio
    if not counting_enabled:
        return

    audio_chunk = indata[:, 0]

    # Gain
    GAIN = 7.0
    audio_chunk = audio_chunk * GAIN

    # 1. RMS energy filter (ignore very quiet chunks)
    rms = np.sqrt(np.mean(audio_chunk**2))
    if rms < 0.03:
        return

    # 2. Spectral centroid (sharp/high frequency impact)
    centroid = librosa.feature.spectral_centroid(y=audio_chunk, sr=sr)[0].mean()
    if centroid < 3000:
        return

    # 3. MFCC similarity
    chunk_mfcc = librosa.feature.mfcc(y=audio_chunk, sr=sr, n_mfcc=13)
    chunk_vec = np.mean(chunk_mfcc, axis=1)

    corr_value = np.dot(chunk_vec, ref_vec) / (
        np.linalg.norm(chunk_vec) * np.linalg.norm(ref_vec)
    )

    # Cooldown so 1 hit = 1 jump
    if cooldown_counter > 0:
        cooldown_counter -= 1
        return

    if corr_value > threshold:
        jump_count += 1
        cooldown_counter = cooldown_frames
        print(f"Jump Count: {jump_count}")


### START AUDIO STREAM ###

def start_audio_stream():
    if not USE_AUDIO:
        print("⚠️ Audio disabled on Render.")
        return
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
def home():
    return send_from_directory("static", "index.html")
@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory("static", path)

@app.route("/jump_count")
def jump_count_route():
    return jsonify({
        "count": jump_count,
        "counting": counting_enabled   # << add this
    })

@app.route("/timer")
def timer():
    return jsonify({"time": get_elapsed_time()})


@app.route("/laps")
def get_laps():
    return jsonify({"laps": laps})

@app.route("/add_jump", methods=["POST"])
def add_jump():
    global jump_count
    data = request.get_json() or {}
    delta = int(data.get("delta", 1))
    if delta < 0:
        delta = 0
    jump_count += delta
    return jsonify({"count": jump_count})

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
@app.route("/pace")
def pace():
    t = get_elapsed_time()
    if t < 1:
        return jsonify({"pace": 0})
    pace = round(jump_count / (t / 60))  # jumps per minute
    return jsonify({"pace": round(pace, 2)})


### RUN EVERYTHING ###

if __name__ == "__main__":
    if USE_AUDIO:
        audio_thread = threading.Thread(target=start_audio_stream, daemon=True)
        audio_thread.start()
        print("🎧 Local audio capture enabled")
    else:
        print("🌐 Running on Render — audio disabled")

    import logging
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)