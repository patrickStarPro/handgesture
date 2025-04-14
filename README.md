# Hand Gesture Recognition Web Application

This project provides a web-based frontend for the Hand Gesture Recognition system, allowing users to detect and translate hand gestures through a user-friendly interface.

## Features

- Real-time hand gesture detection through webcam
- Visual display of detected gestures
- Easy-to-use interface for adding gestures to a sequence
- Translation of gesture sequences into text
- Responsive design that works on various devices

## Supported Gestures

The application can recognize the following hand gestures:
- HELLO: All fingers raised
- YES: Index finger raised, others folded
- NO: Thumb to the left of index finger
- STOP: All fingers extended with palm facing forward
- THUMBS UP: Thumb raised, other fingers folded
- PEACE: Index and middle fingers raised, others folded

## Installation

1. Ensure you have Python 3.7+ installed
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the Flask application:
   ```
   python app.py
   ```
2. Open your web browser and navigate to: http://127.0.0.1:5000
3. Grant permission to use your webcam if prompted
4. Use the interface to:
   - View the current detected gesture
   - Add gestures to the sequence with the "Add Gesture" button
   - Translate the sequence with the "Translate" button
   - Clear the sequence with the "Clear" button

## Technical Details

The application uses:
- Flask for the web server
- OpenCV for webcam access and image processing
- MediaPipe for hand landmark detection
- JavaScript for the frontend interactivity
- Bootstrap 5 for responsive design
