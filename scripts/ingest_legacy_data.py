import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent

load_dotenv(project_root / ".env")

data_path = project_root / "data" / "raw" / "dynamic_supply_chain_logistics_dataset.csv"
database_url = os.environ["DATABASE_URL"]

print(f"Loading CSV from {data_path}...")

df = pd.read_csv(data_path)

legacy_mapping = {
    "timestamp": "TS_UTC",
    "vehicle_gps_latitude": "V_LAT",
    "vehicle_gps_longitude": "V_LON",
    "iot_temperature": "IOT_TEMP_VAL_C",
    "cargo_condition_status": "CGO_COND_CD",
    "risk_classification": "RISK_CLS_TXT",
    "delay_probability": "DELAY_PROB_DEC",
    "port_congestion_level": "PRT_CNG_LVL",
    "route_risk_level": "RT_RSK_IDX",
}

df_legacy = df[list(legacy_mapping)].rename(columns=legacy_mapping)
df_legacy["SYS_INGEST_FLAG"] = "Y"

print("Connecting to PostgreSQL...")

engine = create_engine(database_url)
table_name = "shipment_telemetry_raw"

print(f"Ingesting into {table_name}...")

df_legacy.to_sql(table_name, engine, if_exists="replace", index=False)

print(f"Legacy ingestion complete: {len(df_legacy)} rows loaded.")
