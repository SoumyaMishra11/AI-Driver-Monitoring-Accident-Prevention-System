from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AlarmConfig:
    drowsy_sound: str = "assets/alarm.wav"
    distracted_sound: str = "assets/alarm.wav"
    volume: float = 1.0  # 0.0 - 1.0
    cooldown_s: float = 1.0


@dataclass
class LoggingConfig:
    enabled: bool = True
    csv_path: str = "logs/events.csv"
    metrics_every_n_frames: int = 10


@dataclass
class UiConfig:
    show_fps: bool = True
    show_panel: bool = True


@dataclass
class AppConfig:
    camera_index: int = 0
    alarm: AlarmConfig = field(default_factory=AlarmConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    ui: UiConfig = field(default_factory=UiConfig)
