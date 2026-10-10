FROM python:3.12-slim

ARG BUILD_NUMBER=0
ARG APP_VERSION=0.1.0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BUILD_NUMBER=${BUILD_NUMBER} APP_VERSION=${APP_VERSION}
WORKDIR /srv

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir .

RUN useradd --system --uid 1001 priveo
USER priveo

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
