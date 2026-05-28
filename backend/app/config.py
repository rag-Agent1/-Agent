from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7
    llm_timeout: int = 60

    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    max_image_size: int = 10485760
    allowed_extensions: str = "jpg,jpeg,png,webp"

    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
