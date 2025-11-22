# Dreamflow

Airflow for running satellite imagery analysis jobs.

## Setup

Make a `.env` file:
```bash
export AIRFLOW_UID=1000
export AIRFLOW_PROJ_DIR=$HOME/universe/dreamflow
export AIRFLOW_HOME=$HOME/universe/dreamflow
export AIRFLOW_CONN_MONGO_DEFAULT=mongodb://root:example@localhost:27017/
export AIRFLOW_CONN_POSTGRES_DEFAULT=postgresql://airflow:airflow@localhost:5432/lore
```

You'll need graphviz:
```bash
sudo apt-get install graphviz
```

Then run it:
```bash
source .env
airflow standalone
```

Go to http://localhost:8080 and use the password from the logs.

## Updating dependencies

```bash
pip-compile --output-file=requirements.txt pyproject.toml --constraint constraints.txt
```

## What's here

Two main DAGs:
- `imagery_finder_dag.py` - runs the actual satellite imagery searches and analysis
- `import_archive_items_dag.py` - imports archive metadata

Built on Airflow 2.10.4, Python 3.11, uses Postgres (via Atlas) and Celery + Redis for task queueing.
