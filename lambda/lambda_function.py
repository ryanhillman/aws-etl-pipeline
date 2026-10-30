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

def transform(df):
    """Trim whitespace and increment Age by 1, leaving blank or invalid ages blank."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    if "Age" in df.columns:
        age = pd.to_numeric(df["Age"], errors="coerce")
        df["Age"] = age.where(age % 1 == 0).astype("Int64") + 1
    else:
        print("⚠️ 'Age' column not found in dataset!")
    return df

def process_file(bucket, key):
    # --- Read CSV from the source bucket ---
    body = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()

    if not body.strip():
        print(f"⚠️ Skipping empty file: {key}")
        return

    df = pd.read_csv(io.BytesIO(body))

    print("Original data:")
    print(df)

    # --- Simple transformation: increment age by 1 ---
    df = transform(df)

    # --- Write the file's rows as its own partition of the "cleaned" Glue table ---
    # Overwriting the partition means reprocessing a file (re-upload, duplicate
    # event, retry) replaces its rows instead of duplicating them. "/" would break
    # the partition path, so raw/a/b.csv becomes a__b.csv.
    df["source_file"] = key.removeprefix("raw/").replace("/", "__")
    wr.s3.to_parquet(
        df=df,
        path=CLEANED_PATH,
        dataset=True,
        mode="overwrite_partitions",
        partition_cols=["source_file"],
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
