
from datetime import datetime
import json
from airflow.decorators import dag, task, task_group
from airflow.operators.python import get_current_context
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator


def build_execute_query(imagery_finder_pk, dream_pk):
    
    

    sql = f"""

    CREATE TABLE imagery_seeker_{imagery_finder_pk}_{dream_pk} AS
    SELECT 
        archive_items.id as archive_item_id,
        imagery_finders.id as imagery_finder_id
    FROM archive_finder_archiveitem archive_items
    LEFT JOIN archive_finder_imageryfinder imagery_finders
    ON archive_items.start_date >= imagery_finders.start_date
    AND archive_items.end_date <= imagery_finders.end_date
    LEFT JOIN core_location locations
    ON imagery_finders.location_id = locations.id
    WHERE ST_Intersects(
        archive_items.geometry,
        locations.geometry
    )
    AND imagery_finders.id = {imagery_finder_pk}
    ;

    INSERT INTO archive_finder_archivelookupitem (created, modified, imagery_finder_id, archive_item_id, study_id)
    SELECT
        CURRENT_TIMESTAMP as created,
        CURRENT_TIMESTAMP as modified,
        imagery_finder_id,
        archive_item_id,
        (SELECT study_id FROM augury_dream WHERE id = {dream_pk}) as study_id
    FROM imagery_seeker_{imagery_finder_pk}_{dream_pk}
    ;
    """
    return sql


default_params ={"imagery_finder_pk": 2, "dream_pk": 1}

@dag(
    schedule=None,
    catchup=False,
    tags=["imagery_finder"],
    params=default_params
)
def imagery_finder():
    """
    Process all archive results
    """

    @task_group
    def etl():

        def get_conf_value(key):
            context = get_current_context()
            conf = context["dag_run"].conf
            return conf.get(key)

        @task(pool="postgres_pool")
        def create_imagery_finder_items():
            imagery_finder_pk = get_conf_value("imagery_finder_pk")
            dream_pk = get_conf_value("dream_pk")

            execute_query = SQLExecuteQueryOperator(
                conn_id="postgres_default",
                task_id=f"execute_imagery_finder_{imagery_finder_pk}_{dream_pk}",
                sql=build_execute_query(imagery_finder_pk=imagery_finder_pk, dream_pk=dream_pk),
            )
            execute_query.execute(context={})


        @task
        def notify_augur(_):
            dream_pk = get_conf_value("dream_pk")
            
            poll_archive_finder = SimpleHttpOperator(
                http_conn_id="http_augur_connection",
                task_id=f"notify_diviner_{dream_pk}",
                endpoint=f"api/augury/divine",
                data=json.dumps({"dream_id": dream_pk}),
                method="POST",
            )
            poll_archive_finder.execute(context={})
        
        notify_augur(create_imagery_finder_items())
        
    etl()

imagery_finder()
