FROM python:3.9-slim

LABEL "com.gmc.navin3d"="smnavin65@gmail.com"
LABEL version="0.1"

WORKDIR /usr/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 8000

CMD ["python", "-m", "server"]
