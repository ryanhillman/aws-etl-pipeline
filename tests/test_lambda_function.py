import io
import urllib.parse
from pathlib import Path

import boto3
import pandas as pd
import pytest
from moto import mock_aws

import lambda_function

# Deliberately different from the real bucket names to prove nothing is hardcoded
RAW_BUCKET = "test-raw-bucket"
CLEANED_BUCKET = "test-cleaned-bucket"
SAMPLE_CSV = Path(__file__).parent.parent / "sample_data" / "raw_data.csv"


@pytest.fixture
def s3(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("CLEANED_BUCKET", CLEANED_BUCKET)
    with mock_aws():
        client = boto3.client("s3")
        client.create_bucket(Bucket=RAW_BUCKET)
        client.create_bucket(Bucket=CLEANED_BUCKET)
        yield client


def s3_event(bucket, key):
    """Build an S3 put event the way S3 sends it, with a URL-encoded key."""
    return {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket},
                    "object": {"key": urllib.parse.quote_plus(key)},
                }
            }
        ]
    }


def read_cleaned(s3, key):
    body = s3.get_object(Bucket=CLEANED_BUCKET, Key=f"cleaned/{key}")["Body"].read()
    return pd.read_csv(io.BytesIO(body))


def test_increments_age_in_sample_data(s3):
    s3.put_object(Bucket=RAW_BUCKET, Key="raw_data.csv", Body=SAMPLE_CSV.read_bytes())

    result = lambda_function.lambda_handler(s3_event(RAW_BUCKET, "raw_data.csv"), None)

    assert result["statusCode"] == 200
    cleaned = read_cleaned(s3, "raw_data.csv")
    assert cleaned["Name"].tolist() == ["Ryan", "Palmer"]
    assert cleaned["Age"].tolist() == [30, 9]


def test_handles_url_encoded_keys(s3):
    key = "uploads/my file (1).csv"
    s3.put_object(Bucket=RAW_BUCKET, Key=key, Body=b"Name,Age\nAlex,40\n")

    lambda_function.lambda_handler(s3_event(RAW_BUCKET, key), None)

    assert read_cleaned(s3, key)["Age"].tolist() == [41]


def test_passes_through_data_without_age_column(s3):
    s3.put_object(Bucket=RAW_BUCKET, Key="no_age.csv", Body=b"Name,City\nAlex,Boston\n")

    result = lambda_function.lambda_handler(s3_event(RAW_BUCKET, "no_age.csv"), None)

    assert result["statusCode"] == 200
    cleaned = read_cleaned(s3, "no_age.csv")
    assert cleaned.to_dict("records") == [{"Name": "Alex", "City": "Boston"}]
