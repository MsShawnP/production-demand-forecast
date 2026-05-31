FROM python:3.13-slim

# WeasyPrint system dependencies (pango, cairo, gdk-pixbuf, cffi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user for least-privilege execution
RUN mkdir -p /cache && \
    useradd -r -u 1001 -s /bin/false appuser && \
    chown -R appuser /app /cache

USER appuser

ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "3", "--timeout", "120", "app.run:server"]
