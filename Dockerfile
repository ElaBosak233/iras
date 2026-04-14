FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY app/ ./app/
COPY main.py .

EXPOSE 8000

CMD ["python", "main.py"]
