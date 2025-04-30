import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    model_config = {
        "env_file": ".env",          
        "env_file_encoding": "utf-8",
        "extra": "ignore",          
    }
    # Application Settings
    APP_NAME: str = "Microsoft Hackathon AI Agent"
    # LangChain Settings
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN")
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY")

    #API Settings
    BASE_WB_URL: str = os.getenv("BASE_WB_URL")

# Instantiate settings
settings = Settings()
