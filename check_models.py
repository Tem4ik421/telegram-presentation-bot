import google.generativeai as genai
import os
from dotenv import load_dotenv

# Загружаем ключ из .env файла
load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("Ошибка: Не могу найти GEMINI_API_KEY в вашем .env файле.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("--- Список доступных моделей для вашего ключа ---")
        for m in genai.list_models():
            # Проверяем, поддерживает ли модель генерацию контента
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
        print("-------------------------------------------------")
    except Exception as e:
        print(f"Произошла ошибка при подключении к Google API: {e}")