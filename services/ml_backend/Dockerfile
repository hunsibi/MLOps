FROM ultralytics/ultralytics:latest-cpu

WORKDIR /app

RUN pip install --no-cache-dir rq redis label-studio-ml gunicorn

COPY model.py .
COPY _wsgi.py .

EXPOSE 9090

CMD ["gunicorn", "-b", "0.0.0.0:9090", "-w", "1", "--timeout", "120", "_wsgi:app"]
