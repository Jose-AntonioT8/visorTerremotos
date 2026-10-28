FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY productor.py consumidor.py paises.py api.py ./

USER nobody
