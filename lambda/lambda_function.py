import io
import os
import urllib.parse

import awswrangler as wr
import boto3
import pandas as pd

# Set by Terraform
CLEANED_PATH = os.environ["CLEANED_PATH"]
GLUE_DATABASE = os.environ["GLUE_DATABASE"]

# Created once per container and reused across invocations
s3_client = boto3.client("s3")

def parse_csv(body):
    """Parse CSV bytes with every column as text; transform() types Age."""
    if not body.strip():
        return pd.DataFrame()
    # pandas reads an all-blank column as numbers, which would fix that column's
    # type for the whole table
    return pd.read_csv(io.BytesIO(body), dtype="string")

def transform(df):
    """Trim whitespace and increment Age by 1, leaving blank or invalid ages blank."""
    df = df.rename(columns=str.strip).apply(lambda col: col.str.strip())

    if "Age" in df.columns:
        age = pd.to_numeric(df["Age"], errors="coerce")
        df["Age"] = age.where(age % 1 == 0).astype("Int64") + 1
    else:
        print("⚠️ 'Age' column not found in dataset!")
    return df

def process_file(bucket, key):
    # --- Read CSV from the source bucket ---
    df = parse_csv(s3_client.get_object(Bucket=bucket, Key=key)["Body"].read())

    # Blank or header-only file: awswrangler can't infer types from an empty table
    if df.empty:
        print(f"⚠️ Skipping empty file: {key}")
        return

    print("Original data:")
    print(df)

    # --- Simple transformation: increment age by 1 ---
    df = transform(df)

    # --- Append to the Parquet dataset and register it as the "cleaned" Glue table ---
    wr.s3.to_parquet(
        df=df,
        path=CLEANED_PATH,
        dataset=True,
        mode="append",
        database=GLUE_DATABASE,
        table="cleaned"
    )

    print(f"✅ Successfully processed and uploaded: {key}")

def lambda_handler(event, context):
    print("✅ Lambda triggered successfully.")

    for record in event["Records"]:
        # Object keys arrive URL-encoded (e.g. spaces as "+")
        process_file(
            record["s3"]["bucket"]["name"],
            urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        )
