# filename: Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY backend .

RUN pip install poetry==1.8.3
RUN poetry config virtualenvs.create false && poetry install --no-dev

CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]