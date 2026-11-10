import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY", "procureflow-development-key"
    )

    SQLALCHEMY_DATABASE_URI = (
        "sqlite:///" + os.path.join(BASE_DIR, "procureflow.db")
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    RANDOM_SEED = 20261022

    DATA_SCALE = {
        "requesters": 300,
        "suppliers": 120,
        "requests": 1200,
        "rfqs": 500,
        "quotes": 1500,
        "purchase_orders": 900
    }
