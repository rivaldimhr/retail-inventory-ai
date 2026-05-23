import json
import os
from src.config.config import config


class MBARepository:
    @staticmethod
    def save(data: dict):
        with open(config.MBA_PATH, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load() -> dict | None:
        if not os.path.exists(config.MBA_PATH):
            return None
        with open(config.MBA_PATH, "r") as f:
            return json.load(f)
