FROM python:3

WORKDIR /usr/src/pycross

COPY preinstall.txt ./
RUN apt-get update
RUN cat preinstall.txt | xargs apt-get install -y

COPY requirements.txt ./
# ENV HTTP_PROXY http://192.168.1.10:3128
# ENV HTTPS_PROXY ${HTTP_PROXY}
RUN pip install -r requirements.txt

COPY . .

WORKDIR pycross
ENTRYPOINT [ "python3", "./cwordg.py" ]

# additional args: CMD ["-c"]
