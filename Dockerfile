FROM python:3.9-slim-buster
WORKDIR /app
COPY requirements.txt /app/
RUN apt update && apt install git -y
RUN git config --global --add safe.directory /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
VOLUME [ "/app" ]
CMD ["flask", "run", "--host", "0.0.0.0"]