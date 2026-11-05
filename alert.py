import pygame
import threading
import time

class AlertManager:
    def __init__(
        self,
        drowsy_sound_file="assets/alarm.wav",
        distracted_sound_file="assets/alarm.wav",
        volume=1.0,
        cooldown_s=1.0,
    ):
        
        pygame.mixer.init()

        self.cooldown_s = float(cooldown_s)
        self.volume = float(max(0.0, min(1.0, volume)))
        self._last_play_ts = 0.0

        try:
            self.drowsy_sound = pygame.mixer.Sound(drowsy_sound_file)
            self.drowsy_sound.set_volume(self.volume)
            self.sound_loaded = True
        except FileNotFoundError:
            print(
                f"Warning: Sound file {drowsy_sound_file} not found. Audio alerts will be disabled."
            )
            self.sound_loaded = False

        try:
            self.distracted_sound = pygame.mixer.Sound(distracted_sound_file)
            self.distracted_sound.set_volume(self.volume)
        except FileNotFoundError:
            self.distracted_sound = None
            
        self.is_playing = False

    def play_alert(self, kind="drowsy"):
        
        now = time.time()
        if (now - self._last_play_ts) < self.cooldown_s:
            return

        if self.sound_loaded and not self.is_playing:
            self.is_playing = True
            self._last_play_ts = now
            threading.Thread(target=self._play, args=(kind,), daemon=True).start()

    def _play(self, kind):
 
        sound = self.drowsy_sound
        if kind == "distracted" and self.distracted_sound is not None:
            sound = self.distracted_sound

        try:
            sound.set_volume(self.volume)
            sound.play()
        except Exception:
            pass

    
        time.sleep(max(0.2, self.cooldown_s))
        self.is_playing = False
