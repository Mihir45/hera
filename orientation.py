class Orientation:
    pitch: float
    roll: float
    yaw: float

    def dict(self) -> dict:
        return {"pitch": self.pitch, "roll": self.roll, "yaw": self.yaw}
