FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dateparse.py calendar_client.py bot.py ./

# .env と service_account.json は実行時にマウント/コピーする（イメージに焼き込まない）
CMD ["python", "bot.py"]
