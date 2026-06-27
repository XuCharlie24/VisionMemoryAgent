from dataclasses import dataclass, field


@dataclass
class Settings:
    camera_device: str = "/dev/video8"
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 25
    cors_origins: list[str] = field(default_factory=lambda: ["*"])


settings = Settings()
