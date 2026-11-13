from src.config.config import config
from src.repositories.data_repository import _read_json, _write_json


class MBARepository:
    @staticmethod
    def save(data: dict):
        _write_json(config.MBA_PATH, data)

    @staticmethod
    def load():
        return _read_json(config.MBA_PATH)
