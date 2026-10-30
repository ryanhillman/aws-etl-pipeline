import io
from unittest import mock

import pytest

import lambda_function


class FakeS3:
    """In-memory stand-in for the S3 client, keyed by object key."""

    def __init__(self, objects):
        self.objects = objects
        self.uploads = {}

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, Bucket, Key, Body):
        self.uploads[Key] = Body


def run(s3, encoded_key):
    event = {"Records": [{"s3": {"object": {"key": encoded_key}}}]}
    with mock.patch.object(lambda_function.boto3, "client", return_value=s3):
        return lambda_function.lambda_handler(event, None)


def test_decodes_url_encoded_key():
    s3 = FakeS3({"my data.csv": b"Name,Age\nRyan,29\n"})

    run(s3, "my+data.csv")

    assert "cleaned/my data.csv" in s3.uploads


@pytest.mark.parametrize("key, body", [("empty.csv", b""), ("folder/", b"")])
def test_skips_empty_files_and_folders(key, body):
    s3 = FakeS3({key: body})

    result = run(s3, key)

    assert result["statusCode"] == 200
    assert s3.uploads == {}
