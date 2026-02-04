
"""
Configuration module for Retail Insights Assistant
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    
    # Model Configuration
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
    
    # Data Configuration
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "10000"))
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/vector_db")
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    UPLOAD_DIR = DATA_DIR / "uploads"
    PROCESSED_DIR = DATA_DIR / "processed"
    
    # LangSmith Monitoring
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "retail-insights-assistant")
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.UPLOAD_DIR.mkdir(exist_ok=True)
        cls.PROCESSED_DIR.mkdir(exist_ok=True)
        Path(cls.VECTOR_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.OPENAI_API_KEY and not cls.GEMINI_API_KEY:
            raise ValueError("Either OPENAI_API_KEY or GEMINI_API_KEY must be set")
        
        cls.create_directories()
        return True

# Validate configuration on import
Config.validate()