import io

import pandas as pd

from lambda_function import transform


def read(csv):
    return pd.read_csv(io.StringIO(csv))


def test_increments_age():
    result = transform(read("Name,Age,City\nRyan,29,Charlotte\nPalmer,8,Davidson\n"))

    assert result["Age"].tolist() == [30, 9]
    assert result["Name"].tolist() == ["Ryan", "Palmer"]


def test_blank_age_stays_blank():
    result = transform(read("Name,Age,City\nRyan,29,Charlotte\nPalmer,,Davidson\n"))

    assert result["Age"].iloc[0] == 30
    assert pd.isna(result["Age"].iloc[1])


def test_trims_whitespace_in_headers_and_values():
    result = transform(read("Name,Age,City \nRyan,29,Charlotte \n"))

    assert list(result.columns) == ["Name", "Age", "City"]
    assert result["City"].tolist() == ["Charlotte"]
