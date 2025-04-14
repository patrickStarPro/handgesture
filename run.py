import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow info/warning logs

import cv2
import mediapipe as mp
import logging
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

# Webcam loop
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    logging.error("Webcam could not be opened. Please check your camera.")
    exit()

with mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7) as hands:

    logging.info("Starting webcam loop. Press 't' to translate or 'ESC' to quit.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            logging.warning("Failed to read frame from webcam. Exiting loop.")
            break

        # Flip and convert to RGB
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process hand
        result = hands.process(rgb)
        label = ""

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Get normalized landmark list
                landmarks = hand_landmarks.landmark

                # Classify gesture
                label = classify_hand_gesture(landmarks)
                if label != "UNKNOWN":
                    detected_signs.append(label)

                cv2.putText(frame, f'Gesture: {label}', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        cv2.imshow("Sign Detector", frame)

        key = cv2.waitKey(10)
        if key == ord('t'):  # Press 't' to translate current sign sequence
            if detected_signs:
                translation = translator.translate(detected_signs)
                logging.info(f"Detected Signs: {detected_signs}")
                logging.info(f"Translation: {translation}")
                detected_signs.clear()
        elif key == 27:  # ESC to quit
            logging.info("Exiting program.")
            break

cap.release()
cv2.destroyAllWindows()
