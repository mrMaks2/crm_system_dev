FROM python

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

ENV SELENIUM_REMOTE_URL="http://selenium:4444/wd/hub"

COPY . .