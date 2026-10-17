import pytest
import pandas as pd
from pathlib import Path



# Fixture to read the CSV file
@pytest.fixture(scope="session")
def csv_path():
    return Path(__file__).resolve().parent.parent / "src" / "data" / "data.csv"

@pytest.fixture(scope="session")
def read_csv(csv_path):
    return pd.read_csv(csv_path)

# Fixture to validate the schema of the file
@pytest.fixture(scope="session")
def actual_schema(read_csv):
    return list(read_csv.columns)

@pytest.fixture(scope="session")
def expected_schema():
    return ["id","name","age","email","is_active"]

@pytest.fixture(scope="session")
def validate_schema(actual_schema, expected_schema):
    missing = [col for col in expected_schema if col not in actual_schema]
    unexpected = [col for col in actual_schema if col not in expected_schema]
    return missing, unexpected

# Pytest hook to mark unmarked tests with a custom mark
def pytest_collection_modifyitems(config, items):
    for item in items:
        if not list(item.iter_markers()):
            item.add_marker(pytest.mark.unmarked)