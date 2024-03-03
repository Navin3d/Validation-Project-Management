FROM python:3

LABEL "com.gmc.navin3d"="smnavin65@gmail.com"

LABEL version="0.1"

WORKDIR /usr/app

COPY ./requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt

COPY ./ ./

EXPOSE 8000

CMD ["python3", "server.py"]
