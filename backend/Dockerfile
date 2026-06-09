FROM python:3.11-slim

WORKDIR /app

# torch CPU wheel keeps the image lean. Override with --build-arg TORCH_INDEX=...
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --extra-index-url ${TORCH_INDEX} -r requirements.txt

COPY server/ ./server/

EXPOSE 8000
ENV FL_ADMIN_USER=admin \
    FL_ADMIN_PASS=admin

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
