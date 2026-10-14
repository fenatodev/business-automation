# Optional private-only API image. Not started or deployed by this repository.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_NO_CACHE=1
WORKDIR /srv/app
RUN python -m pip install --no-cache-dir uv==0.9.17 \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
RUN uv sync --locked --no-dev --no-editable
COPY app/ ./app/
USER 10001:10001
EXPOSE 8000
CMD [".venv/bin/uvicorn", "app.intake_only:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
