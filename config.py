import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/tervtest")
    
    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "terv-test-super-secret-key-2024")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    
    # Code Execution
    CODE_EXEC_TIMEOUT = 5       # seconds
    CODE_EXEC_MEM_MB = 128      # MB (soft limit via ulimit on Linux)
    
    # HuggingFace API
    HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")
    
    # App
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "flask-secret-key-terv-test")
