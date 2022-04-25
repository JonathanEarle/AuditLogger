FROM python:3.10.4

ENV PYTHONUNBUFFERED=1
ENV SRC_DIR $PATH/src
ENV DATABASE_INI=$SRC_DIR/database.ini

COPY src/* ${SRC_DIR}/
WORKDIR ${SRC_DIR}

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["python", "server.py"]