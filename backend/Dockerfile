FROM python:3.12-slim
WORKDIR /app
COPY app.py manage.py notify.py ./
RUN useradd -u 10001 -m receiver && mkdir /data && chown receiver /data
USER receiver
EXPOSE 8080
CMD ["python", "app.py", "--host", "0.0.0.0"]
