FROM ultralytics/ultralytics:latest-cpu

WORKDIR /app

RUN pip install --no-cache-dir rq redis label-studio-ml gunicorn "mlflow==2.15.0" pyyaml

COPY ml_backend/model.py .
COPY ml_backend/_wsgi.py .

COPY trainer/train.py /trainer/train.py
COPY trainer/dataset_builder.py /trainer/dataset_builder.py

EXPOSE 9090

CMD ["gunicorn", "-b", "0.0.0.0:9090", "-w", "1", "--timeout", "7200", "_wsgi:app"]
