FROM python:3.11
WORKDIR /app
COPY services/ml/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY services/ml /app
ENV MODEL_ID=google/medgemma-4b-it
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
