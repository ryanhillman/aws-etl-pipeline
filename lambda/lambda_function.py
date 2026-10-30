import json
import urllib.parse
import boto3
import pandas as pd
import io

CLEANED_BUCKET = "cleaned-data-ryan"

# Created once per container and reused across invocations
s3_client = boto3.client("s3")

def transform(df):
    """Trim whitespace and increment Age by 1, leaving blank ages blank."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()

    if "Age" in df.columns:
        df["Age"] = df["Age"].astype("Int64") + 1
    else:
        print("⚠️ 'Age' column not found in dataset!")
    return df

def process_file(bucket, key):
    # --- Read CSV from the source bucket ---
    body = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()

    # Skip folders created in the console and empty files
    if key.endswith("/") or not body.strip():
        print(f"⚠️ Skipping empty file or folder: {key}")
        return

    df = pd.read_csv(io.BytesIO(body))

    print("Original data:")
    print(df)

    # --- Simple transformation: increment age by 1 ---
    df = transform(df)

    # --- Write entire DataFrame to memory as CSV ---
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    # --- Upload to cleaned S3 bucket ---
    s3_client.put_object(
        Bucket=CLEANED_BUCKET,
        Key=f"cleaned/{key}",
        Body=csv_buffer.getvalue()
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

    return {"statusCode": 200, "body": json.dumps("Processing complete.")}
