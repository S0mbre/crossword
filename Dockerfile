FROM python:3

WORKDIR /usr/src/pycross

COPY requirements.txt ./
ENV HTTP_PROXY http://192.168.1.10:3128
ENV HTTPS_PROXY ${HTTP_PROXY}
RUN pip install --proxy=http://192.168.1.10:3128 --no-cache-dir -r requirements.txt

COPY . .

WORKDIR pycross
ENTRYPOINT [ "python3", "./cwordg.py" ]

# additional args: CMD ["-c"]