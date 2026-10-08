# A pinned base, one layer per concern, and a non-root user at runtime.
FROM python:3.13-slim

WORKDIR /app
COPY --chown=10001:10001 app.py .

USER 10001
ENTRYPOINT ["python3", "app.py"]
