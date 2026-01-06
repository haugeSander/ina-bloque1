# Smart Home MQTT Sensor

A Python-based IoT sensor that publishes environmental data and real-time person detection to Home Assistant via MQTT.

## Prerequisites
* Python 3.10+
* A webcam (for detection mode)
* MQTT Broker (e.g., Mosquitto in Home Assistant)

## Installation

1.  **Create a virtual environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Download the AI Model (if not present):**
    You must download `efficientdet_lite0.tflite` and place it in this folder.
    [Download Link](https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/float16/1/efficientdet_lite0.tflite)

## Usage

**1. Simulation Mode (No Camera)**
Sends random temperature, humidity, and time data only.
```bash
python3 mqtt_publisher.py
```

**2. AI Detection Mode (Camera On)**
Activates the webcam to detect people while also sending environmental data.
```bash
python3 mqtt_publisher.py --detection
```

## Configuration
Open mqtt_publisher.py to update your MQTT settings:
```python
BROKER = "xxx.xxx.xx.xxx"
USERNAME = "..."
PASSWORD = "..."
```

