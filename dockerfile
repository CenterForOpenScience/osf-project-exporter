FROM python:3.12

WORKDIR /code/app

RUN apt-get update \
    && apt-get --assume-yes install libpq-dev gcc python3-dev \
    musl-dev zlib1g-dev libjpeg-dev libldap2-dev libsasl2-dev

COPY . /code/app

RUN pip install -U pip setuptools \
    && pip install --no-cache-dir -r /code/app/requirements.core.txt \
    && pip install -e .

