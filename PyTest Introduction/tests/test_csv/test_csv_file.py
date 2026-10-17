import pytest

def test_file_not_empty(csv_path):
    assert csv_path.exists(), f"File not found in {csv_path}"
    assert csv_path.stat().st_size > 0, f"File at:{csv_path} is empty"

@pytest.mark.validate_csv
@pytest.mark.xfail(reason="Expected to contain duplicates.")
def test_duplicates(read_csv):
    duplicates = read_csv[read_csv.duplicated(keep=False)]
    assert duplicates.empty, f"{len(duplicates)} found in the CSV file.\nDuplicates: {duplicates}"  

@pytest.mark.validate_csv
def test_validate_schema(validate_schema, actual_schema, expected_schema):
    missing, unexpected = validate_schema
    assert not missing and not unexpected, f"Missing columns: {missing}, Unexpected columns: {unexpected}"

@pytest.mark.validate_csv
@pytest.mark.skip(reason="Temporarily disabled")
def test_age_column_valid(read_csv):
    ages = read_csv["age"]
    invalid_ages = [age for age in ages if not 0 <= age <= 100]
    assert len(invalid_ages) == 0, f"Invalid ages found: {invalid_ages}"

@pytest.mark.validate_csv
def test_email_column_valid(read_csv):
    emails = read_csv["email"]
    is_valid = emails.str.contains("@") & emails.str.endswith(".com")
    invalid_rows = read_csv[~is_valid]

    assert invalid_rows.empty, f"Found {len(invalid_rows)} invalid rows. Invalid emails: {invalid_rows['email'].tolist()}"

@pytest.mark.parametrize("id, is_active", [(1, False), (2, True)])
def test_active_players(read_csv, id, is_active):
    row = read_csv[read_csv["id"] == id]
    assert not row.empty, f"Row is empty: {row}"

    assert bool(row["is_active"].iloc[0]) == is_active, f"Expected is_active = {is_active} but found {not is_active}"

def test_active_player(read_csv):
    row = read_csv[read_csv["id"] == 2]
    assert not row.empty, f"Row is empty: {row}"

    assert bool(row["is_active"].iloc[0]) == True, f"Expected is_active = True but found False"
