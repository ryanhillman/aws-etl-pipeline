import io
import os
import urllib.parse

import boto3
import pandas as pd

# Set by Terraform
CLEANED_BUCKET = os.environ["CLEANED_BUCKET"]

# Created once per container and reused across invocations
s3_client = boto3.client("s3")


def parse_csv(body):
    """Parse CSV bytes with every column as text; transform() types Age."""
    if not body.strip():
        return pd.DataFrame()
    # pandas reads an all-blank column as numbers, which would fix that column's
    # type for the whole table. index_col=False stops it from treating an extra
    # field in the first row as a row index, which shifts every column.
    return pd.read_csv(io.BytesIO(body), dtype="string", index_col=False)


def transform(df):
    """Trim whitespace and increment age by 1, leaving blank or invalid ages blank."""
    # Lowercase headers so "Age", "age" and "AGE" all match; Glue lowercases column
    # names anyway. Whitespace-only cells become blank, like empty ones.
    df = df.rename(columns=lambda c: c.strip().lower()).apply(
        lambda col: col.str.strip().replace("", pd.NA)
    )

    if "age" in df.columns:
        age = pd.to_numeric(df["age"], errors="coerce")
        df["age"] = age.where(age % 1 == 0).astype("Int64") + 1
    else:
        print("⚠️ 'age' column not found in dataset!")
    return df


def process_file(bucket, key):
    # --- Read CSV from the source bucket ---
    df = parse_csv(s3_client.get_object(Bucket=bucket, Key=key)["Body"].read())

    # Blank or header-only file: awswrangler can't infer types from an empty table
    if df.empty:
        print(f"⚠️ Skipping empty file: {key}")
        return

    # Log the shape, not the rows, so file contents don't end up in CloudWatch
    print(f"Read {len(df)} rows with columns {list(df.columns)}")

    # --- Transform: trim whitespace and increment age by 1 ---
    df = transform(df)

    # --- Upload to cleaned S3 bucket ---
    s3_client.put_object(
        Bucket=CLEANED_BUCKET,
        Key=f"cleaned/{key}",
        Body=df.to_csv(index=False),
    )

    print(f"✅ Successfully processed and uploaded: {key}")


def lambda_handler(event, context):
    print("✅ Lambda triggered successfully.")

    for record in event["Records"]:
        # Object keys arrive URL-encoded (e.g. spaces as "+")
        process_file(
            record["s3"]["bucket"]["name"],
            urllib.parse.unquote_plus(record["s3"]["object"]["key"]),
        )
