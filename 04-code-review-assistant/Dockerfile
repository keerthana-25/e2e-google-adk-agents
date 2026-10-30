FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY code_review_assistant ./code_review_assistant
EXPOSE 8080
# SESSION_DB_URL lets reviews/history survive restarts (e.g. a Cloud SQL Postgres URL).
# Without it ADK keeps sessions in memory.
CMD ["sh", "-c", "adk web --host 0.0.0.0 --port 8080 ${SESSION_DB_URL:+--session_service_uri $SESSION_DB_URL} ."]
