import io
from unittest import mock

import lambda_function


class FakeS3:
    """In-memory stand-in for the S3 client."""

    def __init__(self, objects):
        self.objects = objects  # {(bucket, key): body}
        self.uploads = {}  # {key: body}

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}

    def put_object(self, Bucket, Key, Body):
        self.uploads[Key] = Body


def run(objects, *encoded_keys):
    """Invoke the handler with one S3 record per key, as S3 would send it."""
    s3 = FakeS3({("test-raw", key): body for key, body in objects.items()})
    event = {
        "Records": [
            {"s3": {"bucket": {"name": "test-raw"}, "object": {"key": key}}}
            for key in encoded_keys
        ]
    }
    with mock.patch.object(lambda_function, "s3_client", s3):
        lambda_function.lambda_handler(event, None)
    return s3.uploads


def test_reads_bucket_from_event_and_decodes_key():
    uploads = run({"my data.csv": b"Name,Age\nRyan,29\n"}, "my+data.csv")

    assert uploads["cleaned/my data.csv"].splitlines() == ["Name,Age", "Ryan,30"]


def test_processes_every_record():
    uploads = run({"a.csv": b"Age\n1\n", "b.csv": b"Age\n2\n"}, "a.csv", "b.csv")

    assert set(uploads) == {"cleaned/a.csv", "cleaned/b.csv"}


def test_skips_empty_files():
    uploads = run({"empty.csv": b"", "blank.csv": b"\n\n"}, "empty.csv", "blank.csv")

    assert uploads == {}
