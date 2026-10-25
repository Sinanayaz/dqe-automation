import pytest
from src.connectors.postgres.postgres_connector import PostgresConnectorContextManager
from src.data_quality.data_quality_validation_library import DataQualityLibrary
from src.connectors.file_system.parquet_reader import ParquetReader

def pytest_addoption(parser):
    parser.addoption("--db_host", action="store", default="localhost", help="Database host")
    parser.addoption("--db_port", action="store", type=int, default=5434, help="Database port")
    parser.addoption("--db_name", action="store", default="mydatabase", help="Database name")
    parser.addoption("--db_user", action="store", default=None, help="Database user (required)")
    parser.addoption("--db_password", action="store", default=None, help="Database password (required)")
    parser.addoption("--parquet_root", action="store", default="/parquet_data",
                     help="Root folder of the parquet datasets (remaps /parquet_data/... paths)")



def pytest_configure(config):
    """
    Validates that all required command-line options are provided.
    Skipped for --collect-only and --help so the suite can still be inspected without credentials.
    """
    if config.option.collectonly or config.option.help:
        return
    required_options = ["--db_user", "--db_password"]
    missing = [opt for opt in required_options if not config.getoption(opt)]
    if missing:
        raise pytest.UsageError(f"Missing required option(s): {', '.join(missing)}")


@pytest.fixture(scope='session')
def db_connection(request):
    get = request.config.getoption
    try:
        with PostgresConnectorContextManager(
            db_host=get("--db_host"),
            db_port=get("--db_port"),
            db_name=get("--db_name"),
            db_user=get("--db_user"),
            db_password=get("--db_password"),
        ) as db_connector:
            yield db_connector
    except Exception as e:
        pytest.fail(f"Failed to initialize PostgresConnectorContextManager: {e}")


@pytest.fixture(scope='session')
def parquet_reader(request):
    return ParquetReader(root=request.config.getoption("--parquet_root"))


@pytest.fixture(scope='session')
def data_quality_library():
    return DataQualityLibrary()