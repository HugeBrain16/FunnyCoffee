FROM python:3.9.9
WORKDIR /app
COPY . .
RUN python3 -m pip install -r ./requirements.txt
CMD python3 -u -OO ./bot.py
