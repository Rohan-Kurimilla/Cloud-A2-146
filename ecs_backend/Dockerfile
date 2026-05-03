FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["python", "-c", "from app import app; app.run(host='0.0.0.0', port=80, debug=False, use_reloader=False)"]