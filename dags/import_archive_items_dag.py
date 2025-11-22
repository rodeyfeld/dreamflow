
from datetime import timedelta, datetime, timezone
import json
from airflow.decorators import dag, task, task_group
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.providers.mongo.hooks.mongo import MongoHook
from bson.json_util import dumps as bson_dumps

from bson.json_util import loads as bson_loads
from shapely.geometry import shape
from shapely.wkt import dumps
import uuid

@staticmethod
def format_datetime(datetime) -> str:
    return datetime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def build_insert_query(archive_item):
    sql = f"""
    INSERT INTO "augury_archiveitem" 
    (
        "created",
        "modified",
        "external_id",
        "provider",
        "geometry",
        "collection",
        "sensor",
        "thumbnail",
        "start_date",
        "end_date",
        "metadata"
    )
    VALUES (
        CURRENT_TIMESTAMP,
        CURRENT_TIMESTAMP,
        '{archive_item["external_id"]}', 
        '{archive_item["provider"]}',
        ST_GeomFromText('{archive_item["geometry"]}'),
        '{archive_item["collection"]}',  
        '{archive_item["sensor"]}',  
        '{archive_item["thumbnail"]}', 
        '{archive_item["start_date"].isoformat()}', 
        '{archive_item["end_date"].isoformat()}',
        '{archive_item["metadata"]}'
    );
    """
    return sql

def is_valid_geometry_type(geojson):
    if geojson["type"] in ("Polygon"):
        if coords := geojson.get("coordinates"):
            if len(coords) > 0:
                return True
    return False

def geojson_to_wkt(geojson):
    geometry = shape(geojson)
    return dumps(geometry)

def map_sensor_to_technique(sensor: str):
    if sensor in ("EO", "MSI"):
        return "EO"
    elif sensor in ("SAR"):
        return"SAR"
    return "UNKNOWN"

@dag(
    schedule=None,
    catchup=False,
    tags=["archive_finder"],
)
def import_archive_items():
    """
    Process all archive results
    """

    @task_group
    def etl(date_range):
            
        @task(pool="postgres_pool")
        def insert_to_postgres(archive_items):
            # hook = PostgresHook(postgres_conn_id='postgres_default')
            sql_queries = ' '.join([build_insert_query(archive_item) for archive_item in archive_items])
            insert_task = SQLExecuteQueryOperator(
                conn_id="postgres_default",
                task_id=f"insert_archive_item_{uuid.uuid4().hex}",
                sql=sql_queries,
            )
            insert_task.execute(context={})


        @task(pool="default_pool")
        def process_collections(collections):
            archive_items = []
            for collection in collections:
                for feature in bson_loads(collection["features"]):
                    geometry_geojson = feature['geometry']
                    if is_valid_geometry_type(geometry_geojson):
                        geometry = geojson_to_wkt(geometry_geojson)
                        sensor = feature['sensor']
                        technique = map_sensor_to_technique(sensor)
                        archive_item = {
                            "external_id" : feature['id'],
                            "provider": "copernicus",
                            "geometry" : geometry,
                            "collection" : collection["collection_name"],
                            "sensor" : technique,
                            "thumbnail" : feature['assets']['thumbnail']["href"],
                            "start_date" : feature['start_date'].replace(tzinfo=timezone.utc),
                            "end_date" : feature['end_date'].replace(tzinfo=timezone.utc),
                            "metadata" : json.dumps(feature['properties']),
                        }

                        archive_items.append(archive_item)
            return archive_items

        @task(pool="mongo_pool")
        def fetch_from_mongo(date_range):
            hook = MongoHook(mongo_conn_id="mongo_default")
            client = hook.get_conn()
            db = client["Copernicus"]
            collections = [{"collection_name": "SENTINEL-1", "features": []}, 
                                {"collection_name": "SENTINEL-2", "features": []},
                            ]
            
            for collection in collections:
                results = db[collection["collection_name"]].find(
                    {
                        "start_date": {"$gt": date_range["start_date"]},
                        "end_date": {"$lte": date_range["end_date"]},
                    }
                )
                
                collection["features"] = bson_dumps(results)
            return collections

        
        insert_to_postgres(process_collections(fetch_from_mongo(date_range)))

    @task
    def get_date_ranges():
        initial_datetime = datetime(year=2015,
                                    month=1,
                                    day=1,
                                    second=1
                                )
        present_datetime = datetime(year=2025,
                                    month=1,
                                    day=1,
                                    second=1
                                )
        # present_datetime = datetime.now()
        day_difference = (present_datetime - initial_datetime).days

        curr_datetime = datetime(year=initial_datetime.year, month=initial_datetime.month, day=initial_datetime.day)
        date_ranges = []
        stepper = 15
        for day_step in range(1, day_difference // stepper):
            end_date = initial_datetime + timedelta(days=day_step * stepper)
            print(f"Getting results for {curr_datetime} | {end_date}")
            date_ranges.append({
                "start_date": curr_datetime, 
                "end_date": end_date, 
            })
            curr_datetime = end_date
        return date_ranges

    date_ranges = get_date_ranges()
    etl.expand(date_range=date_ranges)

import_archive_items()
