import pandas as pd
import pytest

from lambda_function import parse_csv, transform


def read(csv):
    return parse_csv(csv.encode())


def test_reads_every_column_as_text():
    df = read("Name,Age,City\nRyan,29,\n")

    assert df.dtypes.astype(str).tolist() == ["string", "string", "string"]


def test_extra_field_in_first_row_keeps_columns_aligned():
    with pytest.warns(pd.errors.ParserWarning):  # pandas notes the dropped field
        df = read("Name,Age,City\nRyan,29,Charlotte,oops\nPalmer,8,Davidson\n")

    assert df["Name"].tolist() == ["Ryan", "Palmer"]
    assert df["City"].tolist() == ["Charlotte", "Davidson"]


def test_increments_age():
    result = transform(read("Name,Age,City\nRyan,29,Charlotte\nPalmer,8,Davidson\n"))

    assert result["Age"].tolist() == [30, 9]
    assert result["Name"].tolist() == ["Ryan", "Palmer"]


@pytest.mark.parametrize("bad_age", ["", "abc", "29.5"])
def test_blank_or_invalid_age_becomes_blank(bad_age):
    result = transform(read(f"Name,Age,City\nRyan,29,Charlotte\nPalmer,{bad_age},Davidson\n"))

    assert result["Age"].iloc[0] == 30
    assert pd.isna(result["Age"].iloc[1])


def test_trims_whitespace_in_headers_and_values():
    result = transform(read("Name,Age,City \nRyan,29,Charlotte \n"))

    assert list(result.columns) == ["Name", "Age", "City"]
    assert result["City"].tolist() == ["Charlotte"]


def test_whitespace_only_cell_becomes_blank():
    result = transform(read("Name,Age,City\nRyan,29,   \n"))

    assert pd.isna(result["City"].iloc[0])
