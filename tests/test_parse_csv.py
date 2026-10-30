from lambda_function import parse_csv


def test_reads_every_column_as_text():
    df = parse_csv(b"Name,Age,City\nRyan,29,\n")

    assert df.dtypes.astype(str).tolist() == ["string", "string", "string"]
