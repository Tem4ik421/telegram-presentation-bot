"""
Бот для создания AI-презентаций в PDF.
Версия 36.0 - Aesthetic Upgrade. Улучшенный поиск фото, выравнивание, больше текста.
"""

import os
import re
import logging
import sqlite3
from dotenv import load_dotenv
import requests
import html
import base64
import time
import json
from datetime import datetime

import telebot
from telebot import types
import pdfkit
import google.generativeai as genai
from PIL import Image

# --- 1. ЗАГРУЗКА НАСТРОЕК ---
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PIXABAY_API_KEY = os.getenv('PIXABAY_API_KEY')
WKHTMLTOPDF_PATH = os.getenv('WKHTMLTOPDF_PATH', r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
user_sessions = {}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-pro-latest')
else:
    gemini_model = None

# --- 2. БАЗА ДАННЫХ ---
DB_NAME = 'bot_stats.db'
def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS user_stats (user_id INTEGER PRIMARY KEY, presentations_count INTEGER DEFAULT 0, questions_count INTEGER DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS presentations (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, topic TEXT, created_at TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, question_text TEXT, created_at TEXT)')
    conn.commit(); conn.close(); logging.info(f"База данных инициализирована ({DB_NAME}).")

def save_presentation_topic(user_id, topic):
    conn = sqlite3.connect(DB_NAME, check_same_thread=False); c = conn.cursor()
    c.execute("INSERT INTO presentations (user_id, topic, created_at) VALUES (?, ?, ?)", (user_id, topic, datetime.now().isoformat()))
    c.execute("INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)", (user_id,)); c.execute("UPDATE user_stats SET presentations_count = presentations_count + 1 WHERE user_id = ?", (user_id,)); conn.commit(); conn.close()

def save_question_history(user_id, question):
    conn = sqlite3.connect(DB_NAME, check_same_thread=False); c = conn.cursor()
    c.execute("INSERT INTO questions (user_id, question_text, created_at) VALUES (?, ?, ?)", (user_id, question, datetime.now().isoformat()))
    c.execute("INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)", (user_id,)); c.execute("UPDATE user_stats SET questions_count = questions_count + 1 WHERE user_id = ?", (user_id,)); conn.commit(); conn.close()

def get_user_profile_data(user_id):
    conn = sqlite3.connect(DB_NAME, check_same_thread=False); c = conn.cursor()
    c.execute("SELECT presentations_count, questions_count FROM user_stats WHERE user_id = ?", (user_id,))
    stats = c.fetchone(); p_count, q_count = (stats[0], stats[1]) if stats else (0, 0)
    c.execute("SELECT topic FROM presentations WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
    topics = [row[0] for row in c.fetchall()]
    c.execute("SELECT question_text FROM questions WHERE user_id = ? ORDER BY created_at DESC LIMIT 5", (user_id,))
    questions = [row[0] for row in c.fetchall()]
    conn.close(); return p_count, q_count, topics, questions

init_db()

# --- 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def call_gemini(prompt, is_json=False):
    if not gemini_model: raise ConnectionError("Модель Gemini не инициализирована.")
    mime_type = "application/json" if is_json else "text/plain"
    config_gemini = genai.types.GenerationConfig(response_mime_type=mime_type)
    response = gemini_model.generate_content(prompt, generation_config=config_gemini)
    text = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(text) if is_json else text

def image_to_base64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode('utf-8')
    except: return ""

def find_image_pixabay(query, user_id, fallback_query=None):
    base_queries = [q for q in [query, fallback_query] if q and q.strip()]
    if not base_queries: base_queries.append("minimalist abstract")
    
    # --- УЛУЧШЕННЫЕ ЗАПРОСЫ ДЛЯ КРАСИВЫХ ФОТО ---
    artistic_keywords = ["photorealistic", "cinematic lighting", "dramatic", "masterpiece", "professional photography"]
    queries_to_try = [f"{base_queries[0]} {keyword}" for keyword in artistic_keywords]
    queries_to_try.extend(base_queries) # Добавляем оригинальные запросы в конец

    for q in queries_to_try:
        try:
            params = {'key': PIXABAY_API_KEY, 'q': q, 'image_type': 'photo', 'safesearch': 'true', 'per_page': 5, 'orientation': 'horizontal'}
            res = requests.get("https://pixabay.com/api/", params=params, timeout=15); res.raise_for_status()
            data = res.json().get('hits', [])
            if data:
                img_url = data[0]['largeImageURL']
                img_resp = requests.get(img_url, timeout=15); img_resp.raise_for_status()
                img_path = os.path.abspath(f"temp_img_{user_id}_{int(time.time())}.jpg")
                with open(img_path, 'wb') as f: f.write(img_resp.content)
                return img_path
        except Exception as e: logging.warning(f"Ошибка Pixabay для '{q}': {e}")
    return None

# --- 4. ГЕНЕРАТОР PDF (ФИНАЛЬНАЯ ВЕРСТКА НА ТАБЛИЦАХ) ---
def create_presentation_pdf(user_id, slides_data):
    filename = f'presentation_{user_id}.pdf'
    
    html_head = f"""
    <html><head><meta charset="UTF-8"><title>Презентация</title>
    <style>
        body {{ margin: 0; padding: 0; background-color: #fff; font-family: 'Times New Roman', Times, serif; color: #333; }}
        .page {{ 
            width: 210mm; height: 297mm; page-break-after: always; 
            padding: 22mm; box-sizing: border-box; 
        }}
        
        /* --- Элементы типографики --- */
        h1.main-title {{ font-size: 40pt; font-weight: bold; margin: 25mm 0; line-height: 1.2; text-align: center; color: #111; }}
        h2.section-title {{ font-size: 28px; font-weight: bold; margin-top: 0; margin-bottom: 10px; }}
        p.main-text {{ font-size: 14px; line-height: 1.6; text-align: justify; margin: 0; }}
        
        .image-portrait {{ width: 150px; height: 190px; object-fit: cover; border-radius: 4px; }}
        
        hr.separator {{ border: none; border-top: 1px solid #eee; margin: 25mm 0; }}

        /* --- Секция с колонками --- */
        h2.columns-title {{ font-size: 24px; font-weight: bold; margin-top: 0; margin-bottom: 20px; }}
        
        .info-blocks-table {{ width: 100%; border-collapse: separate; border-spacing: 20px 0; }}
        .info-blocks-table td {{ 
            background-color: #f8f5f0; padding: 20px; border-radius: 4px; 
            width: 50%; vertical-align: top;
        }}
        .info-blocks-table h3 {{ font-size: 16px; font-weight: bold; margin-top: 0; margin-bottom: 8px; }}
        .info-blocks-table p {{ font-size: 13px; line-height: 1.5; margin: 0; text-align: left; }}
    </style></head><body>
    """
    
    slides_html = ""
    for slide in slides_data:
        img_b64 = image_to_base64(slide.get('image_path'))
        
        slide_html = '<div class="page">'
        # --- НАЧАЛО СТРУКТУРЫ СЛАЙДА НА ТАБЛИЦАХ ---
        
        # Основная таблица-макет
        slide_html += '<table style="width: 100%; border-collapse: collapse;">'
        
        # Секция 1: Картинка слева, текст справа
        slide_html += '<tr>'
        # --- ИЗМЕНЕНИЕ: ИДЕАЛЬНОЕ ВЫРАВНИВАНИЕ ПО ВЕРХУ ---
        slide_html += f'<td style="width: 170px; padding-right: 30px; vertical-align: top;">'
        if img_b64:
            slide_html += f'<img src="data:image/jpeg;base64,{img_b64}" class="image-portrait">'
        slide_html += '</td>'
        slide_html += '<td style="vertical-align: top;">'
        slide_html += f'<h2 class="section-title">{html.escape(slide["title"])}</h2>'
        slide_html += f'<p class="main-text">{html.escape(slide["intro"])}</p>'
        slide_html += '</td>'
        slide_html += '</tr>'
        
        # Разделитель, если есть инфоблоки
        if slide.get("info_blocks"):
            slide_html += '<tr><td colspan="2"><hr class="separator"></td></tr>'
        
            # Секция 2: Информационные блоки в две колонки
            columns_title = slide["info_blocks"][0].get("section_title", "Основные моменты")
            slide_html += f'<tr><td colspan="2"><h2 class="columns-title">{html.escape(columns_title)}</h2></td></tr>'
            
            slide_html += '<tr><td colspan="2">'
            slide_html += '<table class="info-blocks-table">'
            for j in range(0, len(slide["info_blocks"]), 2):
                slide_html += '<tr>'
                block1 = slide["info_blocks"][j]
                slide_html += f'<td><h3>{html.escape(block1["title"])}</h3><p>{html.escape(block1["text"])}</p></td>'
                if j + 1 < len(slide["info_blocks"]):
                    block2 = slide["info_blocks"][j + 1]
                    slide_html += f'<td><h3>{html.escape(block2["title"])}</h3><p>{html.escape(block2["text"])}</p></td>'
                else:
                    slide_html += '<td></td>'
                slide_html += '</tr>'
            slide_html += '</table>'
            slide_html += '</td></tr>'

        slide_html += '</table>'
        # --- КОНЕЦ СТРУКТУРЫ СЛАЙДА ---
        slide_html += '</div>'
        slides_html += slide_html

    final_html = html_head + slides_html + "</body></html>"
    options = {'page-size':'A4', 'margin-top':'0', 'margin-right':'0', 'margin-bottom':'0', 'margin-left':'0', 'encoding':"UTF-8", '--enable-local-file-access': None}
    pdfkit.from_string(final_html, filename, options=options, configuration=config)
    return filename

# --- 5. ОБРАБОТЧИКИ TELEGRAM ---
def get_main_menu_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.add(types.KeyboardButton("Создать презентацию 🎨"), types.KeyboardButton("Ответы на вопросы ❓"), types.KeyboardButton("Профиль 👤"))
    return keyboard

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_sessions.pop(message.from_user.id, None)
    bot.send_message(message.chat.id, "👋 **Привет!**\n\nЯ AI-ассистент для создания стильных PDF-презентаций.", reply_markup=get_main_menu_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "Профиль 👤")
def handle_profile(message):
    # ... (код без изменений)
    pass

@bot.message_handler(func=lambda msg: msg.text == "Ответы на вопросы ❓")
def handle_qna_start(message):
    # ... (код без изменений)
    pass

@bot.message_handler(func=lambda msg: msg.text == "Создать презентацию 🎨")
def handle_presentation_start(message):
    # ... (код без изменений)
    pass

@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    # ... (код без изменений)
    pass

def is_math_query(text: str):
    # ... (код без изменений)
    pass

def handle_qna_question(message):
    # ... (код без изменений)
    pass

def start_generation_process(user_id, chat_id, slide_count):
    session = user_sessions.get(user_id)
    if not session: return
    session['state'] = 'generating'
    last_msg_id = session.get('last_msg_id')
    
    temp_files = []
    pdf_file = None
    try:
        bot.edit_message_text("⏳ Генерирую контент (1/3)...", chat_id, last_msg_id)
        
        # --- ИЗМЕНЕНИЕ: ПРОСИМ AI ДАТЬ БОЛЬШЕ ТЕКСТА ---
        prompt = (
            f"Создай контент для презентации в журнальном стиле из {slide_count} слайдов на тему '{session['topic']}'. "
            f"Для КАЖДОГО из {slide_count} слайдов верни JSON-объект с ключами: "
            f"'title' (основной заголовок слайда), "
            f"'intro' (вступительный текст на 2-3 развернутых абзаца), "
            f"'image_query' (запрос для красивого портретного или пейзажного изображения), "
            f"'info_blocks' (массив из 2 или 4 объектов. У первого объекта должен быть ключ 'section_title', например, 'Ключевые аспекты'. "
            f"У всех объектов должны быть ключи 'title' и 'text' (текст должен быть подробным, на 3-5 предложений)). "
            f"В итоге верни ОДИН БОЛЬШОЙ JSON-массив, содержащий все {slide_count} объектов."
        )
        
        slides_structure = call_gemini(prompt, is_json=True)
        if not isinstance(slides_structure, list) or not slides_structure:
            raise ValueError("AI вернул некорректную структуру данных.")
        
        save_presentation_topic(user_id, session['topic'])
        slides_data = []
        
        bot.edit_message_text("✅ Контент готов. Ищу красивые фото (2/3)...", chat_id, last_msg_id)
        
        for i, slide_struct in enumerate(slides_structure):
            image_query = slide_struct.get('image_query')
            image_path = find_image_pixabay(image_query, user_id, fallback_query=session['topic'])
            
            slide_struct['image_path'] = image_path
            slides_data.append(slide_struct)

        bot.edit_message_text("✅ Фото найдены. Собираю PDF (3/3)...", chat_id, last_msg_id)
        pdf_file = create_presentation_pdf(user_id, slides_data)
        
        with open(pdf_file, 'rb') as doc:
            bot.send_document(chat_id, doc, caption="Ваша презентация готова!")

    except Exception as e:
        bot.send_message(chat_id, f"🚫 Произошла критическая ошибка: {e}")
    finally:
        if pdf_file and os.path.exists(pdf_file): os.remove(pdf_file)
        for f in temp_files:
            if f and os.path.exists(f): os.remove(f)
        user_sessions.pop(user_id, None)
        bot.send_message(chat_id, "Готов к новым задачам!", reply_markup=get_main_menu_keyboard())


@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    # ... (код без изменений)
    pass

# --- ЗАПУСК БОТА ---
if __name__ == '__main__':
    print("Бот запущен (v36.0 - Aesthetic Upgrade)...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Критическая ошибка! Перезапуск через 15 секунд. Ошибка: {e}")
            time.sleep(15)