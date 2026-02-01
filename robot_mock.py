class RobotMock:
    def __init__(self):
        print("Robot Mock Initialized - Waiting for commands...")

    def action(self, name):
        print(f"[{name.upper()}] - Robot is performing the action.")