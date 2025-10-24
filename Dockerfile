# Використовуємо більш стабільний образ на базі Debian Bullseye
FROM python:3.11-slim-bullseye

# Встановлюємо wkhtmltopdf та всі необхідні залежності
# Ця команда має успішно спрацювати на Bullseye
RUN apt-get update && apt-get install -y \
    wkhtmltopdf \
    libxrender1 \
    libfontconfig1 \
    libxtst6 \
    && rm -rf /var/lib/apt/lists/*

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо requirements.txt та встановлюємо Python-залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту файлів проєкту в контейнер
COPY . .

# Команда для запуску бота
CMD ["python3", "main.py"]
