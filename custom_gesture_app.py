import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow info/warning logs

import cv2
import mediapipe as mp
import numpy as np
import json
import os
from flask import Flask, render_template, Response, jsonify, request
import logging
import threading
import time

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MediaPipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Constants
LANDMARKS_COUNT = 21  # Number of landmarks in a hand
GESTURE_DB_FILE = 'gesture_database.json'
RECORDING_FRAMES = 30  # Number of frames to record for a gesture
SIMILARITY_THRESHOLD = 0.85  # Threshold for similarity matching

# Global variables
current_gesture_name = "None"
is_recording = False
recording_frames = []
gesture_database = {}
recording_text = ""
recording_name = ""
current_frame = None
recording_countdown = 0
gesture_lock = threading.Lock()

# Load existing gesture database if it exists
def load_gesture_database():
    global gesture_database
    if os.path.exists(GESTURE_DB_FILE):
        try:
            with open(GESTURE_DB_FILE, 'r') as f:
                gesture_database = json.load(f)
            logging.info(f"Loaded {len(gesture_database)} gestures from database")
        except Exception as e:
            logging.error(f"Error loading gesture database: {e}")
            gesture_database = {}
    else:
        gesture_database = {}

# Save gesture database
def save_gesture_database():
    try:
        with open(GESTURE_DB_FILE, 'w') as f:
            json.dump(gesture_database, f)
        logging.info(f"Saved {len(gesture_database)} gestures to database")
    except Exception as e:
        logging.error(f"Error saving gesture database: {e}")

# Extract landmarks as a flat list of coordinates
def extract_landmarks(landmarks):
    if not landmarks or len(landmarks) < LANDMARKS_COUNT:
        return None
    
    # Extract x, y coordinates from each landmark and flatten into a 1D array
    coords = []
    for lm in landmarks:
        coords.extend([lm.x, lm.y])
    
    return coords

# Normalize landmarks to be invariant to scale and translation
def normalize_landmarks(landmarks_array):
    if not landmarks_array:
        return None
    
    # Reshape to pairs of [x, y]
    landmarks = np.array(landmarks_array).reshape(-1, 2)
    
    # Calculate center of the hand
    center = np.mean(landmarks, axis=0)
    
    # Center the landmarks around origin
    centered = landmarks - center
    
    # Calculate the maximum distance from the center
    max_distance = np.max(np.linalg.norm(centered, axis=1))
    
    # Scale to ensure invariance to hand size
    if max_distance > 0:
        normalized = centered / max_distance
    else:
        normalized = centered
    
    # Flatten back to 1D array
    return normalized.flatten().tolist()

# Calculate similarity between two gesture landmark sets
def calculate_similarity(landmarks1, landmarks2):
    if not landmarks1 or not landmarks2:
        return 0.0
    
    # Convert to numpy arrays
    array1 = np.array(landmarks1)
    array2 = np.array(landmarks2)
    
    # Calculate cosine similarity
    dot_product = np.dot(array1, array2)
    norm1 = np.linalg.norm(array1)
    norm2 = np.linalg.norm(array2)
    
    if norm1 * norm2 == 0:
        return 0.0
    
    similarity = dot_product / (norm1 * norm2)
    return float(similarity)

# Recognize a gesture from landmarks
def recognize_gesture(landmarks):
    global gesture_database, current_gesture_name
    
    if not landmarks or len(gesture_database) == 0:
        return "No Gestures"
    
    normalized_landmarks = normalize_landmarks(landmarks)
    if not normalized_landmarks:
        return "No Gestures"
    
    best_match = None
    best_similarity = 0
    
    for gesture_name, gesture_data in gesture_database.items():
        for sample in gesture_data["samples"]:
            similarity = calculate_similarity(normalized_landmarks, sample)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = gesture_name
    
    if best_similarity >= SIMILARITY_THRESHOLD and best_match:
        return best_match
    
    return "No Gestures"

# Process a video frame
def process_frame(frame):
    global current_gesture_name, is_recording, recording_frames, recording_countdown, current_frame
    
    if frame is None:
        return frame
    
    # Make a copy of the frame for display
    display_frame = frame.copy()
    
    # Flip and convert to RGB for MediaPipe
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Store the current frame for other functions to use
    current_frame = frame
    
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,  # Changed from 1 to 2 to support both hands
        min_detection_confidence=0.7) as hands:
        
        # Process hand
        result = hands.process(rgb)
        
        if result.multi_hand_landmarks:
            # Create a list to combine landmarks from all hands
            all_landmarks = []
            
            for hand_landmarks in result.multi_hand_landmarks:
                # Draw landmarks on display frame
                mp_drawing.draw_landmarks(display_frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Get landmarks
                landmarks = hand_landmarks.landmark
                flat_landmarks = extract_landmarks(landmarks)
                if flat_landmarks:
                    all_landmarks.extend(flat_landmarks)
            
            # If in recording mode, add frame to recording buffer
            if is_recording and all_landmarks:
                recording_frames.append(all_landmarks)
                
                # Display countdown on frame
                remaining = RECORDING_FRAMES - len(recording_frames)
                recording_countdown = remaining
                cv2.putText(display_frame, f'Recording: {remaining}', (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                
                if len(recording_frames) >= RECORDING_FRAMES:
                    # Finished recording
                    finish_recording()
            else:
                # Recognize gesture in normal mode
                gesture = recognize_gesture(all_landmarks)
                with gesture_lock:
                    current_gesture_name = gesture
                
                # Display recognized gesture on frame
                text_to_show = f'Gesture: {gesture}'
                if gesture in gesture_database:
                    text_to_show += f' → {gesture_database[gesture]["text"]}'
                
                cv2.putText(display_frame, text_to_show, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        # If in recording mode but no hand detected, show message
        elif is_recording:
            cv2.putText(display_frame, 'No hand detected!', (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        # Show recording status on frame
        if is_recording:
            cv2.putText(display_frame, f'Recording gesture: {recording_name if recording_name else recording_text}', (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        # Show instruction in normal mode
        if not is_recording:
            cv2.putText(display_frame, 'Press "R" to record new gesture', (10, display_frame.shape[0] - 50),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(display_frame, 'Press "C" to clear all gestures', (10, display_frame.shape[0] - 30),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            cv2.putText(display_frame, 'Press "ESC" to exit', (10, display_frame.shape[0] - 10),
                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
    
    return display_frame

# Finish recording a gesture
def finish_recording():
    global is_recording, recording_frames, gesture_database, recording_text, recording_name
    
    if len(recording_frames) > 0:
        # Calculate average landmarks from all frames
        avg_landmarks = []
        for i in range(0, len(recording_frames[0])):
            avg_value = sum(frame[i] for frame in recording_frames) / len(recording_frames)
            avg_landmarks.append(avg_value)
        
        # Normalize the landmarks
        normalized_landmarks = normalize_landmarks(avg_landmarks)
        
        # Add to database with proper name
        gesture_name = recording_name if recording_name else recording_text
        
        if gesture_name in gesture_database:
            gesture_database[gesture_name]["samples"].append(normalized_landmarks)
        else:
            gesture_database[gesture_name] = {
                "text": recording_text,
                "samples": [normalized_landmarks]
            }
        
        # Save the updated database
        save_gesture_database()
        
        logging.info(f"Recorded new gesture: {gesture_name} -> {recording_text}")
    
    # Reset recording state
    is_recording = False
    recording_frames = []
    recording_text = ""
    recording_name = ""

# Generate video frames for the web
def generate_frames():
    global current_frame
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        logging.error("Webcam could not be opened. Please check your camera.")
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + b'Error: Camera not available' + b'\r\n')
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.warning("Failed to read frame from webcam.")
            break
        
        processed_frame = process_frame(frame)
        
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Flask routes
@app.route('/')
def index():
    return render_template('custom_gesture.html', gestures=gesture_database)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/current_gesture')
def get_current_gesture():
    with gesture_lock:
        gesture = current_gesture_name
        text = ""
        if gesture in gesture_database:
            text = gesture_database[gesture]["text"]
        return jsonify({"gesture": gesture, "text": text})

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global is_recording, recording_frames, recording_text, recording_name
    
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({"success": False, "error": "No text provided"})
    
    recording_text = data['text']
    recording_name = data.get('name', '') or recording_text  # Use name if provided, otherwise use text
    recording_frames = []
    is_recording = True
    
    return jsonify({"success": True})

@app.route('/cancel_recording')
def cancel_recording():
    global is_recording, recording_frames, recording_text, recording_name
    
    is_recording = False
    recording_frames = []
    recording_text = ""
    recording_name = ""
    
    return jsonify({"success": True})

@app.route('/get_gestures')
def get_gestures():
    return jsonify({"gestures": gesture_database})

@app.route('/delete_gesture', methods=['POST'])
def delete_gesture():
    global gesture_database
    
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"success": False, "error": "No gesture name provided"})
    
    gesture_name = data['name']
    if gesture_name in gesture_database:
        del gesture_database[gesture_name]
        save_gesture_database()
        return jsonify({"success": True})
    
    return jsonify({"success": False, "error": "Gesture not found"})

@app.route('/clear_all_gestures')
def clear_all_gestures():
    global gesture_database
    
    gesture_database = {}
    save_gesture_database()
    
    return jsonify({"success": True})

@app.route('/recording_status')
def recording_status():
    return jsonify({
        "is_recording": is_recording,
        "countdown": recording_countdown,
        "text": recording_name if recording_name else recording_text
    })

if __name__ == '__main__':
    # Load existing gesture database
    load_gesture_database()
    app.run(debug=True, threaded=True)
