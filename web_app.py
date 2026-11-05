from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, Optional

import cv2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from alert import AlertManager
from app_config import AppConfig
from detector import DriverMonitor
from event_logger import EventLogger
from ui_overlay import draw_status_panel


app = FastAPI(title="Smart Driver Monitoring System")
app.mount("/static", StaticFiles(directory="static"), name="static")


class Runtime:
    def __init__(self) -> None:
        self.cfg = AppConfig()

        self._lock = threading.Lock()
        self._running = False
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._cap: Optional[cv2.VideoCapture] = None
        self._last_jpeg: Optional[bytes] = None
        self._last_metrics: Dict[str, Any] = {}

        self.monitor = DriverMonitor()
        self.alert: Optional[AlertManager] = None
        self.logger: Optional[EventLogger] = None

        # Mutable settings (controlled by UI)
        self.camera_index = int(self.cfg.camera_index)
        self.log_enabled = bool(self.cfg.logging.enabled)
        self.log_path = str(self.cfg.logging.csv_path)
        self.volume = float(self.cfg.alarm.volume)
        self.cooldown = float(self.cfg.alarm.cooldown_s)

    def start(self) -> None:
        with self._lock:
            if self._running:
                return

            self._stop.clear()
            self._cap = cv2.VideoCapture(int(self.camera_index))
            if not self._cap.isOpened():
                self._cap.release()
                self._cap = None
                raise RuntimeError(f"Could not open camera index {self.camera_index}")

            self.alert = AlertManager(
                drowsy_sound_file=self.cfg.alarm.drowsy_sound,
                distracted_sound_file=self.cfg.alarm.distracted_sound,
                volume=float(self.volume),
                cooldown_s=float(self.cooldown),
            )
            self.logger = EventLogger(csv_path=str(self.log_path), enabled=bool(self.log_enabled))

            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            self._running = True

    def stop(self) -> None:
        with self._lock:
            if not self._running:
                return
            self._stop.set()
            self._running = False

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def update_settings(self, settings: Dict[str, Any]) -> None:
        restart_needed = False
        with self._lock:
            if "camera_index" in settings:
                new_cam = int(settings["camera_index"])
                if new_cam != self.camera_index:
                    self.camera_index = new_cam
                    restart_needed = True

            if "log_enabled" in settings:
                self.log_enabled = bool(settings["log_enabled"])
            if "log_path" in settings and settings["log_path"]:
                self.log_path = str(settings["log_path"])
            if "volume" in settings:
                self.volume = float(settings["volume"])
            if "cooldown" in settings:
                self.cooldown = float(settings["cooldown"])

        if restart_needed and self.is_running():
            self._restart()

    def _restart(self) -> None:
        self.stop()
        time.sleep(0.2)
        self.start()

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "settings": {
                    "camera_index": self.camera_index,
                    "log_enabled": self.log_enabled,
                    "log_path": self.log_path,
                    "volume": self.volume,
                    "cooldown": self.cooldown,
                },
                "metrics": self._last_metrics,
            }

    def get_latest_jpeg(self) -> Optional[bytes]:
        with self._lock:
            return self._last_jpeg

    def _loop(self) -> None:
        cap = self._cap
        if cap is None:
            return

        last_t = time.time()
        fps = 0.0
        frame_idx = 0

        while not self._stop.is_set() and cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                continue

            now = time.time()
            dt = max(1e-6, now - last_t)
            last_t = now
            fps = (0.9 * fps) + (0.1 * (1.0 / dt)) if fps > 0 else (1.0 / dt)

            metrics = self.monitor.process_frame(frame)
            draw_status_panel(frame, metrics, fps=fps)

            # Logging (lightweight)
            if self.logger and self.logger.enabled and (frame_idx % self.cfg.logging.metrics_every_n_frames == 0):
                self.logger.log(
                    {
                        "type": "metrics",
                        "ear": float(metrics.get("ear", 0.0)),
                        "pitch": float(metrics.get("pitch", 0.0)),
                        "yaw": float(metrics.get("yaw", 0.0)),
                        "gaze": str(metrics.get("gaze", "n/a")),
                        "seatbelt": metrics.get("seatbelt", None),
                        "drowsy": bool(metrics.get("drowsy", False)),
                        "distracted": bool(metrics.get("distracted", False)),
                        "face_detected": bool(metrics.get("face_detected", False)),
                        "fps": float(fps),
                        "frame": int(frame_idx),
                    }
                )

            if metrics.get("drowsy", False):
                if self.alert:
                    self.alert.play_alert(kind="drowsy")
                if self.logger and self.logger.enabled:
                    self.logger.log({"type": "event", "event": "drowsy", "frame": int(frame_idx)})
            elif metrics.get("distracted", False):
                if self.alert:
                    self.alert.play_alert(kind="distracted")
                if self.logger and self.logger.enabled:
                    self.logger.log({"type": "event", "event": "distracted", "frame": int(frame_idx)})

            ok2, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ok2:
                with self._lock:
                    self._last_jpeg = jpg.tobytes()
                    self._last_metrics = {
                        "ear": float(metrics.get("ear", 0.0)),
                        "pitch": float(metrics.get("pitch", 0.0)),
                        "yaw": float(metrics.get("yaw", 0.0)),
                        "gaze": str(metrics.get("gaze", "n/a")),
                        "seatbelt": metrics.get("seatbelt", None),
                        "drowsy": bool(metrics.get("drowsy", False)),
                        "distracted": bool(metrics.get("distracted", False)),
                        "face_detected": bool(metrics.get("face_detected", False)),
                        "fps": float(fps),
                        "frame": int(frame_idx),
                    }

            frame_idx += 1

        try:
            cap.release()
        except Exception:
            pass

        with self._lock:
            self._cap = None
            self._running = False

        if self.logger:
            self.logger.close()
            self.logger = None


rt = Runtime()
rt.start()


@app.get("/", response_class=HTMLResponse)
def index(_: Request):
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())


@app.get("/api/status")
def api_status():
    return JSONResponse(rt.get_status())


@app.post("/api/start")
def api_start():
    try:
        rt.start()
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


@app.post("/api/stop")
def api_stop():
    rt.stop()
    return JSONResponse({"ok": True})


@app.post("/api/settings")
async def api_settings(request: Request):
    body = await request.body()
    settings = json.loads(body.decode("utf-8") or "{}")
    rt.update_settings(settings)
    return JSONResponse({"ok": True, "status": rt.get_status()})


def _mjpeg_generator():
    boundary = "frame"
    while True:
        jpg = rt.get_latest_jpeg()
        if jpg is None:
            time.sleep(0.05)
            continue
        yield (
            b"--" + boundary.encode() + b"\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: " + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n"
        )
        time.sleep(0.03)


@app.get("/video")
def video():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

