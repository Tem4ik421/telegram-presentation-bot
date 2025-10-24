# Використовуємо Alpine Linux (менший та швидший)
FROM python:3.11-alpine

# Встановлюємо wkhtmltopdf та всі необхідні залежності через apk
# Alpine використовує інший пакетний менеджер (apk)
RUN apk update && \
    apk add --no-cache wkhtmltopdf \
    && rm -rf /var/cache/apk/*

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо requirements.txt та встановлюємо Python-залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо решту файлів проєкту в контейнер
COPY . .

# Команда для запуску бота
CMD ["python3", "main.py"]
