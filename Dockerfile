FROM apache/airflow:slim-2.10.4-python3.11

ENV PYTHONUNBUFFERED=1
WORKDIR /dreamflow
USER root
RUN apt-get update \
  && apt-get install -y \
         vim \
         libpq-dev \
  && apt-get clean 
COPY . /dreamflow
RUN chown -R airflow /dreamflow
USER airflow
RUN pip install --upgrade pip pip-tools
RUN pip-compile --output-file=requirements.txt pyproject.toml --constraint constraints.txt
RUN pip-sync
