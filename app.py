from flask import Flask, render_template, Response, jsonify, url_for
from tensorflow.keras.models import load_model # type: ignore
import cv2
import numpy as np
import time
import threading
import os

app = Flask(__name__)

# Load the model
MODEL_PATH = "latest_full_model.h5"
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
model = load_model(MODEL_PATH)

# Global variables for pothole counting
start_time = time.time()
pothole_count = 0
is_detecting = False
lock = threading.Lock()

# Pothole tracking
tracked_potholes = []
TRACKING_THRESHOLD = 50  # pixels

def detect_pothole(frame):
    global pothole_count, tracked_potholes
    
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, (300, 300))
    img = img.reshape(1, 300, 300, 1).astype('float32') / 255.0
    
    prediction = model.predict(img)
    is_pothole = np.argmax(prediction[0]) == 1
    confidence = float(np.max(prediction[0]))

    if is_pothole:
        # Find contours to get pothole location
        _, binary = cv2.threshold(img[0, :, :, 0], 0.5, 1, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours((binary * 255).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Get the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Scale coordinates back to original frame size
            scale_factor = frame.shape[1] / 300
            x, y, w, h = int(x * scale_factor), int(y * scale_factor), int(w * scale_factor), int(h * scale_factor)
            
            # Check if this pothole is already tracked
            new_pothole = True
            for tracked in tracked_potholes:
                if abs(tracked['x'] - x) < TRACKING_THRESHOLD and abs(tracked['y'] - y) < TRACKING_THRESHOLD:
                    new_pothole = False
                    break
            
            if new_pothole:
                tracked_potholes.append({'x': x, 'y': y, 'w': w, 'h': h, 'last_seen': time.time()})
                with lock:
                    pothole_count += 1
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    # Remove old tracked potholes
    current_time = time.time()
    tracked_potholes = [p for p in tracked_potholes if current_time - p['last_seen'] < 5]  # Remove after 5 seconds
    
    return is_pothole, confidence, frame

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    def gen_frames():
        try:
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                raise Exception("Could not open camera")
            
            while True:
                success, frame = camera.read()
                if not success:
                    break
                else:
                    if is_detecting:
                        try:
                            is_pothole, confidence, processed_frame = detect_pothole(frame)
                            if is_pothole:
                                cv2.putText(processed_frame, f"Pothole: {confidence:.2f}", (10, 30),
                                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                            frame = processed_frame
                        except Exception as e:
                            print(f"Error in detection: {str(e)}")
                    
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        except Exception as e:
            print(f"Error in gen_frames: {str(e)}")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + b'Error: Could not access camera' + b'\r\n')
        finally:
            if 'camera' in locals():
                camera.release()

    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_detection')
def start_detection():
    global is_detecting, start_time, pothole_count, tracked_potholes
    is_detecting = True
    start_time = time.time()
    pothole_count = 0
    tracked_potholes = []
    return jsonify({"status": "Detection started"})

@app.route('/stop_detection')
def stop_detection():
    global is_detecting
    is_detecting = False
    return jsonify({"status": "Detection stopped"})

@app.route('/get_count')
def get_count():
    global start_time, pothole_count
    current_time = time.time()
    elapsed_time = current_time - start_time
    
    if elapsed_time >= 60:
        with lock:
            count = pothole_count
            pothole_count = 0
        start_time = current_time
        return jsonify({"count": count, "time_up": True})
    else:
        with lock:
            count = pothole_count
        return jsonify({"count": count, "time_up": False, "time_left": int(60 - elapsed_time)})

if __name__ == '__main__':
    app.run(debug=True)
