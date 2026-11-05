# Smart Driver Monitoring System



A real-time computer vision system that monitors driver behavior using a webcam to detect drowsiness and distraction.



The system analyzes facial landmarks, eye movement, and head pose to identify unsafe conditions and trigger alerts.



---



## Overview


This project simulates an intelligent driver safety system that continuously observes the driver and evaluates attentiveness.

It combines facial analysis with temporal stability logic to reduce false alarms and provide reliable detection.


---


## Key Features


- Real-time face tracking using MediaPipe

- Drowsiness detection using Eye Aspect Ratio (EAR)

- Distraction detection using head pose (pitch and yaw)

- Gaze tracking for attention monitoring

- Experimental seatbelt detection (heuristic-based)

- Live web dashboard for visualization

- Audio alerts for unsafe behavior

- CSV logging for events and metrics



---



## System Workflow



1. Capture video frames using a webcam.

2. Detect facial landmarks using MediaPipe.

3. Compute EAR for eye closure detection.

4. Estimate head pose for distraction detection.

5. Track gaze direction for attention analysis.

6. Apply temporal smoothing to avoid false triggers.

7. Trigger alerts and log events.


---



## Tech Stack



- Python

- OpenCV

- MediaPipe

- FastAPI

- NumPy



---



## Installation



Clone the repository and install dependencies:



```bash

git clone https://github.com/SoumyaMishra11/AI-Driver-Monitoring-Accident-Prevention-System.git

cd AI-Driver-Monitoring-Accident-Prevention-System

pip install -r requirements.txt

```

