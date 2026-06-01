import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bilearn.db")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or "sk-4471d01619fa44f2a6c40b9d1b88a862"
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
