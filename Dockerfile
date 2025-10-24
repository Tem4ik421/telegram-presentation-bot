# Використовуємо офіційний Python-образ як базу
FROM python:3.11-slim

# Встановлюємо wkhtmltopdf та інші системні залежності
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо requirements.txt та встановлюємо Python-залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо всі файли проєкту в контейнер
COPY . .

# Команда для запуску бота
CMD ["python3", "main.py"]