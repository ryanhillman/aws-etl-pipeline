import io
from unittest import mock

import lambda_function


class FakeS3:
    """In-memory stand-in for the S3 client."""

    def __init__(self, objects):
        self.objects = objects  # {(bucket, key): body}

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[(Bucket, Key)])}


def run(objects, *encoded_keys):
    """Invoke the handler with one S3 record per key; return the to_parquet calls."""
    s3 = FakeS3({("test-raw", key): body for key, body in objects.items()})
    event = {
        "Records": [
            {"s3": {"bucket": {"name": "test-raw"}, "object": {"key": key}}}
            for key in encoded_keys
        ]
    }
    with mock.patch.object(lambda_function, "s3_client", s3), \
         mock.patch.object(lambda_function.wr.s3, "to_parquet") as to_parquet:
        lambda_function.lambda_handler(event, None)
    return [call.kwargs for call in to_parquet.call_args_list]


def test_reads_bucket_from_event_and_decodes_key():
    writes = run({"raw/my data.csv": b"Name,Age\nRyan,29\n"}, "raw/my+data.csv")

    assert len(writes) == 1
    write = writes[0]
    assert write["df"].to_dict("records") == [{"Name": "Ryan", "Age": 30}]
    assert (write["path"], write["database"], write["table"]) == (
        "s3://test-cleaned/cleaned/", "test_db", "cleaned"
    )
    assert (write["dataset"], write["mode"]) == (True, "append")


def test_processes_every_record():
    writes = run({"a.csv": b"Age\n1\n", "b.csv": b"Age\n2\n"}, "a.csv", "b.csv")

    assert [w["df"]["Age"].tolist() for w in writes] == [[2], [3]]


def test_skips_files_without_data_rows():
    files = {"empty.csv": b"", "blank.csv": b"\n\n", "header.csv": b"Name,Age\n"}
    writes = run(files, *files)

    assert writes == []
