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

# Global variables
global_person_detected = False
simulation_mode = False
simulation_time = None

# --- Configuration ---
BROKER = "192.168.1.105"
PORT = 1883
USERNAME = "nicole"
PASSWORD = "Nicole*1223"
TOPIC_BASE = "casa/salon/"

def get_estacion(month):
    if month in [12, 1, 2]: return "Invierno"
    elif month in [3, 4, 5]: return "Primavera"
    elif month in [6, 7, 8]: return "Verano"
    return "Otoño"

def get_current_time():
    """Obtiene el tiempo actual o simulado según el modo"""
    global simulation_mode, simulation_time
    
    if simulation_mode and simulation_time:
        return simulation_time
    else:
        return datetime.datetime.now()

def advance_simulation_time():
    """Avanza el tiempo de simulación en 1 hora"""
    global simulation_time
    
    if simulation_time:
        simulation_time += datetime.timedelta(hours=1)
        
        # Si llegamos al final del año, reiniciamos
        if simulation_time.month == 12 and simulation_time.day == 31 and simulation_time.hour == 23:
            # Reiniciar al 1 de enero del mismo año
            simulation_time = simulation_time.replace(
                month=1, day=1, hour=0, minute=0, second=0
            )
            print(f"\n[Simulación] Reiniciando año {simulation_time.year}\n")
        
        return simulation_time
    return None

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
            now = get_current_time()
            
            client.publish(TOPIC_BASE + "temperatura", temp)
            client.publish(TOPIC_BASE + "humedad", hum)
            client.publish(TOPIC_BASE + "hora", now.strftime("%H:%M:%S"))
            client.publish(TOPIC_BASE + "fecha", now.strftime("%Y-%m-%d"))
            client.publish(TOPIC_BASE + "estacion", get_estacion(now.month))
            
            # Detection data
            client.publish(TOPIC_BASE + "ocupacion", global_person_detected)
            client.publish(TOPIC_BASE + "person", str(global_person_detected))
            
            # Mostrar información del modo de simulación
            mode_indicator = "[SIM]" if simulation_mode else "[REAL]"
            status_msg = "PERSON DETECTED" if global_person_detected else "No one"
            print(f"{mode_indicator}[{now.strftime('%Y-%m-%d %H:%M:%S')}] MQTT Sent | Sensor Status: {status_msg}")
            
            # Si estamos en modo simulación, avanzar el tiempo
            if simulation_mode:
                advance_simulation_time()
                
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

            # Mostrar información del modo en la ventana de video
            mode_text = "MODO SIMULACION" if simulation_mode else "MODO NORMAL"
            cv2.putText(frame, mode_text, (50, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.7, (255, 255, 0), 2, cv2.LINE_AA)
            
            # Draw "PERSON DETECTED" on screen for debug
            if global_person_detected:
                cv2.putText(frame, "PERSON DETECTED", (50, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 255, 0), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, "NO DETECTION", (50, 70), cv2.FONT_HERSHEY_SIMPLEX, 
                            1, (0, 0, 255), 2, cv2.LINE_AA)
            
            # Mostrar fecha y hora actual/simulada
            current_time = get_current_time()
            time_text = current_time.strftime("%Y-%m-%d %H:%M:%S")
            cv2.putText(frame, time_text, (50, 110), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.6, (255, 255, 255), 1, cv2.LINE_AA)
            
            cv2.imshow('Smart Home Sensor', frame)

            key = cv2.waitKey(5) & 0xFF
            if key == ord('q'):
                break
            # Tecla 's' para avanzar manualmente en modo simulación
            elif key == ord('s') and simulation_mode:
                advance_simulation_time()
                print(f"[Simulación] Tiempo avanzado a: {get_current_time().strftime('%Y-%m-%d %H:%M:%S')}")
                    
        detector.close()
        cap.release()
        cv2.destroyAllWindows()


def init_simulation_mode():
    """Inicializa el modo de simulación con la fecha 1/1/año_actual 00:00:00"""
    global simulation_mode, simulation_time
    
    simulation_mode = True
    current_year = datetime.datetime.now().year
    simulation_time = datetime.datetime(current_year, 1, 1, 0, 0, 0)
    
    print("\n" + "="*60)
    print("MODO SIMULACIÓN ACTIVADO")
    print(f"Tiempo inicial: {simulation_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("El tiempo avanzará 1 hora cada 2 segundos")
    print("Presiona 's' en la ventana de video para avanzar manualmente")
    print("="*60 + "\n")

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MQTT Smart Home Sensor')
    parser.add_argument('--detection', action='store_true', help='Enable AI Person Detection')
    parser.add_argument('--simulation', action='store_true', help='Enable Time Simulation Mode')
    args = parser.parse_args()

    # Activar modo simulación si se especifica
    if args.simulation:
        init_simulation_mode()

    # If detection is ON, run MQTT in a background thread and Camera in main thread
    if args.detection:
        print("Starting in AI Mode...")
        mqtt_thread = threading.Thread(target=mqtt_loop, daemon=True)
        mqtt_thread.start()
        detect_person()
    else:
        print("Starting in Simulation Mode (No Camera)...")
        mqtt_loop()