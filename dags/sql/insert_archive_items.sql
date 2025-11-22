INSERT INTO "archive_finder_archiveitem" 
(
    "external_id",
    "geometry",
    
    "collection",
    "sensor",
    "thumbnail",
    "start_date",
    "end_date",
    "metadata"
)
VALUES (
    {{ params.external_id }},
    ST_GeomFromText({{ params.geometry }}),
    {{ params.collection }},
    {{ params.sensor }},
    {{ params.thumbnail }},
    {{ params.start_date }},
    {{ params.end_date }},
    {{ params.metadata }}
)
RETURNING "archive_finder_archiveitem"."id"
;