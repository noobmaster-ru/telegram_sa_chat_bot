FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY placa-tables-7b37297f8489.json /app/creds/placa-tables-7b37297f8489.json
CMD ["python", "run.py"]