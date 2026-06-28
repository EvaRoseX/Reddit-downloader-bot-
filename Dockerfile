# Official Python image use karenge
FROM python:3.11-slim

# System level par FFmpeg aur baaki tools automatic install honge
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Work directory set karenge
WORKDIR /app

# Sabse pehle requirements copy karke install karenge
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baaki saara code copy karenge
COPY . .

# Web server port expose karenge
EXPOSE 8080

# Bot start karne ki command
CMD ["python", "main.py"]
