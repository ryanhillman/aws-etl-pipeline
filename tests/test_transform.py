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

    assert result["age"].tolist() == [30, 9]
    assert result["name"].tolist() == ["Ryan", "Palmer"]


@pytest.mark.parametrize("bad_age", ["", "abc", "29.5"])
def test_blank_or_invalid_age_becomes_blank(bad_age):
    result = transform(
        read(f"Name,Age,City\nRyan,29,Charlotte\nPalmer,{bad_age},Davidson\n")
    )

    assert result["age"].iloc[0] == 30
    assert pd.isna(result["age"].iloc[1])


def test_normalizes_headers_and_trims_values():
    result = transform(read("Name,Age,City \nRyan,29,Charlotte \n"))

    assert list(result.columns) == ["name", "age", "city"]
    assert result["city"].tolist() == ["Charlotte"]


def test_whitespace_only_cell_becomes_blank():
    result = transform(read("Name,Age,City\nRyan,29,   \n"))

    assert pd.isna(result["city"].iloc[0])


@pytest.mark.parametrize("header", ["Age", "age", "AGE", " Age "])
def test_matches_age_header_in_any_case(header):
    result = transform(read(f"Name,{header},City\nRyan,29,Charlotte\n"))

    assert result["age"].tolist() == [30]


def test_missing_required_column_raises():
    with pytest.raises(ValueError, match="city"):
        transform(read("Name,Age\nRyan,29\n"))


def test_drops_columns_outside_the_schema():
    # The trailing comma would otherwise add an "unnamed_3" column to the table
    result = transform(read("Email,Name,Age,City,\na@b.c,Ryan,29,Charlotte,\n"))

    assert list(result.columns) == ["name", "age", "city"]


def test_drops_all_blank_rows():
    result = transform(read("Name,Age,City\nRyan,29,Charlotte\n,,\n"))

    assert result["name"].tolist() == ["Ryan"]
