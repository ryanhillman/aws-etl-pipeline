import json
import boto3
import pandas as pd
import io

def lambda_handler(event, context):
    print("✅ Lambda triggered successfully.")

    # Initialize S3 client
    s3_client = boto3.client("s3")

    # Buckets
    source_bucket = "raw-data-ryan"
    cleaned_bucket = "cleaned-data-ryan"

    # Extract uploaded file name from the S3 event
    key = event["Records"][0]["s3"]["object"]["key"]

    # --- Read CSV from the source bucket ---
    response = s3_client.get_object(Bucket=source_bucket, Key=key)
    df = pd.read_csv(io.BytesIO(response["Body"].read()))

    print("Original data:")
    print(df)

    # --- Simple transformation: increment age by 1 ---
    if "Age" in df.columns:
        df["Age"] = df["Age"].astype(int) + 1
    else:
        print("⚠️ 'Age' column not found in dataset!")

    # --- Write entire DataFrame to memory as CSV ---
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)

    # --- Upload to cleaned S3 bucket ---
    s3_client.put_object(
        Bucket=cleaned_bucket,
        Key=f"cleaned/{key}",
        Body=csv_buffer.getvalue()
    )

    print(f"✅ Successfully processed and uploaded: {key}")
    return {"statusCode": 200, "body": json.dumps("Processing complete.")}
