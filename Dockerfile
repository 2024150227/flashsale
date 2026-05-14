FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static
COPY scripts ./scripts

ENV DATABASE_URL=mysql+mysqlconnector://root:mysql123456@mysql-master:3306/flashsale
ENV REDIS_URL=redis://redis:6379/0
ENV KAFKA_BOOTSTRAP_SERVERS=kafka:9092

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]