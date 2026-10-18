FROM python:3.12-slim
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY app ./app
RUN useradd --create-home civic && mkdir -p /data/uploads && chown -R civic:civic /app /data
USER civic
ENV UPLOAD_DIR=/data/uploads
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
