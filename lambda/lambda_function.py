import json
import boto3
import pandas as pd
import io

def lambda_handler(event, context):
    print("✅ Lambda triggered successfully.")

    s3 = boto3.client("s3")

    source_bucket = "raw-data-ryan"
    destination_bucket = "cleaned-data-ryan"
    key = event["Records"][0]["s3"]["object"]["key"]

    # Read CSV from source bucket
    response = s3.get_object(Bucket=source_bucket, Key=key)
    df = pd.read_csv(io.BytesIO(response["Body"].read()))

    print("Original data:")
    print(df)

    # Simple transform
    df["Age"] = df["Age"].astype(int) + 1

    # Save transformed CSV to destination bucket
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    s3.put_object(Bucket=destination_bucket, Key=f"cleaned/{key}", Body=csv_buffer.getvalue())

    print("✅ Successfully processed and uploaded:", key)
    return {"statusCode": 200, "body": json.dumps("Processing complete.")}

