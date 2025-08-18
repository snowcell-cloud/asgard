FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml .
COPY app/ ./app/

RUN pip install --upgrade pip && pip install .

EXPOSE 8000

CMD ["python", "app/main.py"]
