from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    label_studio_host: str = "http://localhost:8080"
    label_studio_api_key: str = ""
    mlflow_tracking_uri: str = "http://localhost:5000"
    ml_backend_url: str = "http://localhost:9090"
    data_root: str = "/data"
    models_root: str = "/models"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
