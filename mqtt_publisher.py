import time
import random
import datetime
import threading
import paho.mqtt.client as mqtt
import argparse
import sys
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Global variable to share state between Detection thread and MQTT thread
global_person_detected = False

# --- Configuration ---
BROKER = "192.168.68.123"
PORT = 1883
USERNAME = "nicole"
PASSWORD = "Nicole*1223"
TOPIC_BASE = "casa/salon/"

person_detected = False

def get_estacion(month):
    if month in [12, 1, 2]: return "Invierno"
    elif month in [3, 4, 5]: return "Primavera"
    elif month in [6, 7, 8]: return "Verano"
    return "Otoño"

def mqtt_loop():
    client = mqtt.Client()
    client.username_pw_set(USERNAME, PASSWORD)
    
    while True:
        try:
            if not client.is_connected():
                client.connect(BROKER, PORT, 60)
                print("MQTT: Connected")

            temp = round(random.uniform(0, 30), 1)
            hum = round(random.uniform(20, 70), 1)
            now = datetime.datetime.now()
            
            client.publish(TOPIC_BASE + "temperatura", temp)
            client.publish(TOPIC_BASE + "humedad", hum)
            client.publish(TOPIC_BASE + "hora", now.strftime("%H:%M:%S"))
            client.publish(TOPIC_BASE + "fecha", now.strftime("%Y-%m-%d"))
            client.publish(TOPIC_BASE + "estacion", get_estacion(now.month))
            
            # Detection data
            client.publish(TOPIC_BASE + "ocupacion", global_person_detected)
            
            status_msg = "PERSON DETECTED" if global_person_detected else "No one"
            print(f"[{now.strftime('%H:%M:%S')}] MQTT Sent | Sensor Status: {status_msg}")            
        except Exception as e:
            print(f"MQTT Error: {e}")
        
        time.sleep(2)

def detect_person():
    global global_person_detected

# Visualization settings
    row_size = 20  
    left_margin = 24
    text_color = (0, 0, 255)
    font_size = 1
    font_thickness = 1

    # Initialize MediaPipe
    BaseOptions = mp.tasks.BaseOptions
    DetectionResult = mp.tasks.components.containers.Detection
    ObjectDetector = mp.tasks.vision.ObjectDetector
    ObjectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    # Callback Function: This runs every time the AI finishes a frame
    def save_result(result: DetectionResult, output_image: mp.Image, timestamp_ms: int):
        global global_person_detected
        
        is_person = False
        # Loop through detections to see if 'person' is found
        for detection in result.detections:
            category = detection.categories[0]
            if category.category_name == "person" and category.score > 0.5:
                is_person = True
                break
        
        global_person_detected = is_person
        
    options = ObjectDetectorOptions(
        base_options=BaseOptions(model_asset_path='efficientdet_lite0.tflite'),
        running_mode=VisionRunningMode.LIVE_STREAM,
        max_results=5,
        score_threshold=0.5,
        result_callback=save_result
    )
    cap = cv2.VideoCapture(0)
    
    print("Starting Camera...")
    
    # Initialize the holistic model with confidence thresholds
    with ObjectDetector.create_from_options(options) as detector:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                sys.exit(
                    'ERROR: Unable to read from webcam. Please verify your webcam settings.'
                )
            # Convert the frame for MediaPipe
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)

            # Run detection asynchronously (results go to 'save_result' function above)
            detector.detect_async(mp_image, int(time.time() * 1000))

            # Draw "PERSON DETECTED" on screen for debug
            if global_person_detected:
                cv2.putText(frame, "PERSON DETECTED", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "NO DETECTION", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 0, 255), 2, cv2.LINE_AA)
            
            cv2.imshow('Smart Home Sensor', frame)

            if cv2.waitKey(5) & 0xFF == ord('q'):
                break
                    
        detector.close()
        cap.release()
        cv2.destroyAllWindows()


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MQTT Smart Home Sensor')
    parser.add_argument('--detection', action='store_true', help='Enable AI Person Detection')
    args = parser.parse_args()

    # If detection is ON, run MQTT in a background thread and Camera in main thread
    if args.detection:
        print("Starting in AI Mode...")
        mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
        mqtt_thread.start()
        detect_person()
    else:
        print("Starting in Simulation Mode (No Camera)...")
        mqtt_loop()