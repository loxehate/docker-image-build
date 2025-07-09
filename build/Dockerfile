FROM python:3.6-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        libffi-dev \
        libxml2-dev \
        libxslt-dev \
        gcc && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/

COPY . .

RUN pip install --no-cache-dir -r ./requirements.txt
	
EXPOSE 5100

CMD gunicorn app:app -c gunicorn.conf.py
