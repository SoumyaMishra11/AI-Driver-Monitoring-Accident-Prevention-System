from __future__ import annotations

from typing import Any, Dict, Tuple

import cv2


def _color_for_status(ok: bool) -> Tuple[int, int, int]:
    return (0, 200, 0) if ok else (0, 0, 255)


def draw_status_panel(frame, metrics: Dict[str, Any], fps: float | None = None) -> None:
    h, w = frame.shape[:2]

    panel_w = min(420, w - 10)
    panel_h = 150
    x0, y0 = 10, 10
    x1, y1 = x0 + panel_w, y0 + panel_h

    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x1, y1), (0, 0, 0), thickness=-1)
    cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)

    lines = []
    face = bool(metrics.get("face_detected", False))
    lines.append(("FACE", "OK" if face else "NO", _color_for_status(face)))

    ear = metrics.get("ear", 0.0)
    lines.append(("EAR", f"{ear:.3f}", (255, 255, 0)))

    pitch = metrics.get("pitch", 0.0)
    yaw = metrics.get("yaw", 0.0)
    lines.append(("POSE", f"pitch {pitch:.1f}  yaw {yaw:.1f}", (255, 255, 0)))

    gaze = metrics.get("gaze", "n/a")
    lines.append(("GAZE", str(gaze), (255, 255, 0)))

    seatbelt = metrics.get("seatbelt", None)
    if seatbelt is True:
        lines.append(("SEATBELT", "ON", (0, 200, 0)))
    elif seatbelt is False:
        lines.append(("SEATBELT", "OFF", (0, 0, 255)))
    else:
        lines.append(("SEATBELT", "N/A", (200, 200, 200)))

    drowsy = bool(metrics.get("drowsy", False))
    distracted = bool(metrics.get("distracted", False))
    lines.append(("DROWSY", "YES" if drowsy else "NO", _color_for_status(not drowsy)))
    lines.append(("DISTRACT", "YES" if distracted else "NO", _color_for_status(not distracted)))

    if fps is not None:
        lines.append(("FPS", f"{fps:.1f}", (200, 200, 200)))

    y = y0 + 28
    for k, v, c in lines[:7]:
        cv2.putText(frame, f"{k}: {v}", (x0 + 12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c, 2)
        y += 20

