FROM python:3.12-slim
WORKDIR /opt/zongyuan
COPY . .
RUN pip install --no-cache-dir fastapi uvicorn chromadb requests pyyaml
EXPOSE 8000 8001 8005 8009
CMD ["python3", "mmbase_server.py"]
