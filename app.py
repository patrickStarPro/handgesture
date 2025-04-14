import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow info/warning logs

import cv2
import mediapipe as mp
import logging
import base64
import threading
from flask import Flask, render_template, Response, jsonify
from sign_language_translator.translators import RuleBasedTranslator

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Init translator
translator = RuleBasedTranslator()

# Mediapipe setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Store detected signs
detected_signs = []
current_gesture = "None"

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Current gesture lock
gesture_lock = threading.Lock()

# Improved rule-based gesture classifier
def classify_hand_gesture(landmarks):
    """
    Classifies a hand gesture based on the positions of hand landmarks.

    Args:
        landmarks (list): A list of normalized hand landmarks.

    Returns:
        str: The classified gesture ("HELLO", "NO", "YES", "STOP", "THUMBS UP", "PEACE", or "UNKNOWN").
    """
    if not landmarks or len(landmarks) < 21:
        return "UNKNOWN"

    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    middle_tip = landmarks[12]
    ring_tip = landmarks[16]
    pinky_tip = landmarks[20]

    # HELLO: All fingers raised
    if (index_tip.y < landmarks[6].y and
        middle_tip.y < landmarks[10].y and
        ring_tip.y < landmarks[14].y and
        pinky_tip.y < landmarks[18].y):
        return "HELLO"

    # NO: Thumb is to the left of the index finger
    elif thumb_tip.x < index_tip.x:
        return "NO"

    # YES: Index finger raised, others not
    elif (index_tip.y < landmarks[6].y and
          middle_tip.y > landmarks[10].y and
          ring_tip.y > landmarks[14].y and
          pinky_tip.y > landmarks[18].y):
        return "YES"

    # STOP: All fingers extended and palm facing forward
    elif (index_tip.y < landmarks[6].y and
          middle_tip.y < landmarks[10].y and
          ring_tip.y < landmarks[14].y and
          pinky_tip.y < landmarks[18].y and
          thumb_tip.y < landmarks[2].y):
        return "STOP"

    # THUMBS UP: Thumb raised, other fingers folded
    elif (thumb_tip.y < landmarks[3].y and
          index_tip.y > landmarks[6].y and
          middle_tip.y > landmarks[10].y and
          ring_tip.y > landmarks[14].y and
          pinky_tip.y > landmarks[18].y):
        return "THUMBS UP"

    # PEACE: Index and middle fingers raised, others folded
    elif (index_tip.y < landmarks[6].y and
          middle_tip.y < landmarks[10].y and
          ring_tip.y > landmarks[14].y and
          pinky_tip.y > landmarks[18].y):
        return "PEACE"

    return "UNKNOWN"

def process_frame(frame):
    global current_gesture
    
    # Flip and convert to RGB
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    with mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.7) as hands:
        
        # Process hand
        result = hands.process(rgb)
        
        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Get normalized landmark list
                landmarks = hand_landmarks.landmark
                
                # Classify gesture
                label = classify_hand_gesture(landmarks)
                if label != "UNKNOWN":
                    with gesture_lock:
                        current_gesture = label
                
                cv2.putText(frame, f'Gesture: {label}', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    
    return frame

def generate_frames():
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        logging.error("Webcam could not be opened. Please check your camera.")
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            logging.warning("Failed to read frame from webcam. Exiting loop.")
            break
        
        processed_frame = process_frame(frame)
        
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/current_gesture')
def get_current_gesture():
    with gesture_lock:
        return jsonify({"gesture": current_gesture})

@app.route('/add_gesture')
def add_gesture():
    global detected_signs, current_gesture
    with gesture_lock:
        if current_gesture != "None" and current_gesture != "UNKNOWN":
            detected_signs.append(current_gesture)
            return jsonify({"success": True, "detected_signs": detected_signs})
    return jsonify({"success": False})

@app.route('/translate')
def translate():
    global detected_signs
    translation = translator.translate(detected_signs)
    result = {
        "detected_signs": detected_signs.copy(),
        "translation": translation
    }
    detected_signs.clear()
    return jsonify(result)

@app.route('/clear')
def clear():
    global detected_signs
    detected_signs.clear()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True)
