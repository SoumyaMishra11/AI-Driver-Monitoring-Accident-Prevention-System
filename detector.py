import cv2
import mediapipe as mp
import numpy as np

class DriverMonitor:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        
        self.LEFT_EYE = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE = [33, 160, 158, 133, 153, 144]

        
        self.LEFT_IRIS = [474, 475, 476, 477]
        self.RIGHT_IRIS = [469, 470, 471, 472]
        
        self.EAR_THRESH = 0.22  
        self.EAR_CONSEC_FRAMES = 15 
        
        self.counter = 0
        self.drowsy = False
        
        self.distracted = False
       
        self.PITCH_THRESH = 15 
        self.YAW_THRESH = 20  

        
        self.GAZE_AWAY_CONSEC_FRAMES = 12
        self._gaze_counter = 0
        self._gaze_away = False

       
        self.model_3d_points = np.array([
            (0.0, 0.0, 0.0),             
            (0.0, 330.0, -65.0),         
            (-225.0, -170.0, -135.0),    
            (225.0, -170.0, -135.0),     
            (-150.0, 150.0, -125.0),    
            (150.0, 150.0, -125.0)       
        ], dtype=np.float64)

    def calculate_ear(self, landmarks, eye_indices):
        
        p = [np.array([landmarks[idx].x, landmarks[idx].y]) for idx in eye_indices]

        # vertical distances
        dist_2_6 = np.linalg.norm(p[1] - p[5])
        dist_3_5 = np.linalg.norm(p[2] - p[4])
        # horizontal distance
        dist_1_4 = np.linalg.norm(p[0] - p[3])

        if dist_1_4 == 0:
            return 0.0

        ear = (dist_2_6 + dist_3_5) / (2.0 * dist_1_4)
        return ear

    def head_pose_estimation(self, results, frame_shape):
        """Uses solvePnP to estimate head Pitch, Yaw, and Roll."""
        image_h, image_w, _ = frame_shape
        face_2d = []
        
        # Landmark indices mapping to the 3D model
        pose_indices = [1, 152, 33, 263, 61, 291]
        
        if not results.multi_face_landmarks:
            return None

        # Process first detected face
        face_landmarks = results.multi_face_landmarks[0]
        
        for idx in pose_indices:
            lm = face_landmarks.landmark[idx]
            x, y = int(lm.x * image_w), int(lm.y * image_h)
            face_2d.append([x, y])
            
        face_2d = np.array(face_2d, dtype=np.float64)

        # Camera matrix estimation
        focal_length = 1 * image_w
        cam_matrix = np.array([[focal_length, 0, image_w / 2],
                                [0, focal_length, image_h / 2],
                                [0, 0, 1]], dtype=np.float64)

        dist_matrix = np.zeros((4, 1), dtype=np.float64)

        # Solve PnP
        success, rot_vec, trans_vec = cv2.solvePnP(self.model_3d_points, face_2d, cam_matrix, dist_matrix)
        
        if not success:
            return None
            
        # Get rotational matrix
        rmat, _ = cv2.Rodrigues(rot_vec)

        # Decompose into angles
        angles, _, _, _, _, _ = cv2.RQDecomp3x3(rmat)
        
        #changed by Ne
        pitch = angles[0]
        yaw = angles[1]
        roll = angles[2]
        pitch = max(min(pitch, 50), -50)
        yaw = max(min(yaw, 50), -50)
        #till here

      
        return (pitch, yaw, roll)

    def _gaze_direction(self, landmarks) -> str:
       
        def center(ids):
            pts = np.array([[landmarks[i].x, landmarks[i].y] for i in ids], dtype=np.float32)
            return pts.mean(axis=0)

        def eye_bounds(ids):
            pts = np.array([[landmarks[i].x, landmarks[i].y] for i in ids], dtype=np.float32)
            mn = pts.min(axis=0)
            mx = pts.max(axis=0)
            return mn, mx

        li = center(self.LEFT_IRIS)
        ri = center(self.RIGHT_IRIS)
        l_mn, l_mx = eye_bounds(self.LEFT_EYE)
        r_mn, r_mx = eye_bounds(self.RIGHT_EYE)

      
        def norm_x(iris, mn, mx):
            w = max(1e-6, float(mx[0] - mn[0]))
            return float((iris[0] - mn[0]) / w)

        lx = norm_x(li, l_mn, l_mx)
        rx = norm_x(ri, r_mn, r_mx)
        x = (lx + rx) / 2.0

        if x < 0.40:
            return "left"
        if x > 0.60:
            return "right"
        return "center"

    def _seatbelt_present(self, frame_bgr: np.ndarray, landmarks) -> bool | None:
        
        h, w = frame_bgr.shape[:2]
        pts = np.array([[lm.x * w, lm.y * h] for lm in landmarks], dtype=np.float32)
        mn = pts.min(axis=0)
        mx = pts.max(axis=0)

        face_w = mx[0] - mn[0]
        face_h = mx[1] - mn[1]
        if face_w <= 1 or face_h <= 1:
            return None

        
        x0 = int(max(0, mn[0] - 0.25 * face_w))
        x1 = int(min(w, mx[0] + 0.25 * face_w))
        y0 = int(min(h - 1, mx[1] + 0.10 * face_h))
        y1 = int(min(h, y0 + 1.0 * face_h))
        if y1 <= y0 + 10:
            return None

        roi = frame_bgr[y0:y1, x0:x1]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(gray, 60, 180)

        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=60, minLineLength=40, maxLineGap=10)
        if lines is None:
            return False

    
        diag_count = 0
        for x1l, y1l, x2l, y2l in lines[:, 0]:
            dx = float(x2l - x1l)
            dy = float(y2l - y1l)
            if abs(dx) < 1e-3:
                continue
            angle = abs(np.degrees(np.arctan2(dy, dx)))
            if 20 < angle < 70:
                length = (dx * dx + dy * dy) ** 0.5
                if length > 60:
                    diag_count += 1

        return diag_count >= 1

    def process_frame(self, frame):
        """Analyze a single video frame and return drowsiness/distraction metrics."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_rgb.flags.writeable = False # Performance mapping
        results = self.face_mesh.process(frame_rgb)
        frame_rgb.flags.writeable = True
        
        metrics = {
            "ear": 0.0,
            "pitch": 0.0,
            "yaw": 0.0,
            "drowsy": False,
            "distracted": False,
            "face_detected": False,
            "gaze": "n/a",
            "seatbelt": None
        }

        if results.multi_face_landmarks:
            metrics["face_detected"] = True
            landmarks = results.multi_face_landmarks[0].landmark
            
            # 1. EAR Calculation
            left_ear = self.calculate_ear(landmarks, self.LEFT_EYE)
            right_ear = self.calculate_ear(landmarks, self.RIGHT_EYE)
            ear = (left_ear + right_ear) / 2.0
            metrics["ear"] = ear
            
            if ear < self.EAR_THRESH:
                self.counter += 1
                if self.counter >= self.EAR_CONSEC_FRAMES:
                    self.drowsy = True
                    metrics["drowsy"] = True
            else:
                # If eyes are slightly open, reset the counter
                self.counter = max(0, self.counter - 1)
                if self.counter == 0:
                    self.drowsy = False
                
            # 2. Head Pose Calculation
            pose = self.head_pose_estimation(results, frame.shape)
            if pose:
                pitch, yaw, roll = pose
                metrics["pitch"] = pitch
                metrics["yaw"] = yaw
                
                # Check thresholds
                if abs(yaw) > self.YAW_THRESH or abs(pitch) > self.PITCH_THRESH:
                    if not hasattr(self, "distracted_counter"):
                        self.distracted_counter = 0
                    self.distracted_counter += 1
                else:
                    self.distracted_counter = 0

                if self.distracted_counter > 15:
                    self.distracted = True
                    metrics["distracted"] = True
                else:
                    self.distracted = False

            # 3. Gaze direction (iris-based)
            try:
                gaze = self._gaze_direction(landmarks)
                metrics["gaze"] = gaze

                if gaze in ("left", "right"):
                    self._gaze_counter += 1
                else:
                    self._gaze_counter = max(0, self._gaze_counter - 1)

                if self._gaze_counter >= self.GAZE_AWAY_CONSEC_FRAMES:
                    self._gaze_away = True
                if self._gaze_counter == 0:
                    self._gaze_away = False

                if self._gaze_away:
                    metrics["distracted"] = True
                    self.distracted = True
            except Exception:
                pass

            # 4. Seatbelt detection (experimental)
            try:
                metrics["seatbelt"] = self._seatbelt_present(frame, landmarks)
            except Exception:
                metrics["seatbelt"] = None
                    
        return metrics
