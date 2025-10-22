# type Vec3D = tuple[float, float, float]


class Frame:
    temperature: float
    humidity: float
    lux: int
    infrared: int
    visible: int
    acceleration: tuple[float, float, float]
    gyro: tuple[float, float, float]
    magnetic: tuple[float, float, float]

    def dict(self) -> dict:
        return {
            "temperature": self.temperature,
            "relative_humidity": self.humidity,
            "lux": self.lux,
            "infrared": self.infrared,
            "visible": self.visible,
            "acceleration": self.acceleration,
            "gyro": self.gyro,
            "magnetic": self.magnetic,
        }
