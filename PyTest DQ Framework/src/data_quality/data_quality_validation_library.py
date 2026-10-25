import pandas as pd
import datetime
import numbers

_OCCURRENCE = "__occurrence__"

class DataQualityLibrary:
    """
    A library of static methods for performing data quality checks on pandas DataFrames.

    This class is intended to be used in a PyTest-based testing framework to validate
    the quality of data in DataFrames. Each method performs a specific data quality
    check and uses assertions to ensure that the data meets the expected conditions.
    """

    @staticmethod
    def _as_list(column_names):
        if column_names is None:
            return None
        if isinstance(column_names, str):
            return [column_names]
        return list(column_names)

    @staticmethod
    def _require_columns(df, column_names, label="DataFrame"):
        missing = [c for c in column_names if c not in df.columns]
        assert not missing, (
            f"Columns not found in {label}: {missing}. Available columns: {list(df.columns)}"
        )


    @staticmethod
    def _normalise(df, decimals):
        """Make values from Postgres and parquet comparable (numbers -> float, dates -> datetime64[ns])."""
        out = df.copy()
        for col in out.columns:
            s = out[col]
            if pd.api.types.is_bool_dtype(s):
                continue
            if pd.api.types.is_numeric_dtype(s):
                out[col] = s.astype("float64").round(decimals)
            elif pd.api.types.is_datetime64_any_dtype(s):
                if s.dt.tz is None:
                    out[col] = s.astype("datetime64[ns]")
            elif s.dtype == object:
                non_null = s.dropna()
                if non_null.empty:
                    out[col] = s.astype("float64")
                elif all(isinstance(v, numbers.Number) and not isinstance(v, bool) for v in non_null):
                    out[col] = (
                        s.map(lambda v: float("nan") if pd.isna(v) else float(v))
                        .astype("float64")
                        .round(decimals)
                    )
                elif all(isinstance(v, datetime.date) for v in non_null):
                    out[col] = pd.to_datetime(s)
        return out

    @staticmethod
    def _prepare(df, columns, decimals):
        prepared = DataQualityLibrary._normalise(df[columns], decimals).reset_index(drop=True)
        prepared[_OCCURRENCE] = prepared.groupby(columns, dropna=False).cumcount()
        return prepared

    @staticmethod
    def check_duplicates(df, column_names=None):
        subset = DataQualityLibrary._as_list(column_names) or list(df.columns)
        DataQualityLibrary._require_columns(df, subset)
        duplicated = df[df.duplicated(subset=subset, keep=False)]
        assert duplicated.empty, (
            f"Duplicate check failed on columns {subset}: {len(duplicated)} rows belong to "
            f"duplicate groups. Sample:\n{duplicated.head(10).to_string()}"
        )

    @staticmethod
    def check_count(df_expected, df_actual):
        """Fail if the two DataFrames do not have the same number of rows."""
        diff = len(df_expected) - len(df_actual)
        assert diff == 0, (
            f"Count check failed: expected {len(df_expected)} rows, actual {len(df_actual)} rows "
            f"(expected - actual = {diff})."
        )


    @staticmethod
    def check_data_completeness(df_expected, df_actual, column_names=None, decimals=6):
        """
        Fail if the actual data does not contain exactly the expected rows (row order ignored).

        Compared columns: column_names, or all columns of df_expected if omitted.
        Extra columns in df_actual (e.g. hive partition columns) are ignored;
        columns missing from df_actual fail the check.
        """
        columns = DataQualityLibrary._as_list(column_names) or list(df_expected.columns)
        DataQualityLibrary._require_columns(df_expected, columns, "expected data")
        DataQualityLibrary._require_columns(df_actual, columns, "actual data")

        left = DataQualityLibrary._prepare(df_expected, columns, decimals)
        right = DataQualityLibrary._prepare(df_actual, columns, decimals)

        try:
            merged = left.merge(right, on=columns + [_OCCURRENCE], how="outer", indicator=True)
        except ValueError as exc:
            raise AssertionError(
                f"Completeness check could not compare the data sets (incompatible column types): {exc}\n"
                f"Expected dtypes:\n{left[columns].dtypes.to_string()}\n"
                f"Actual dtypes:\n{right[columns].dtypes.to_string()}"
            ) from None

        only_expected = merged.loc[merged["_merge"] == "left_only", columns]
        only_actual = merged.loc[merged["_merge"] == "right_only", columns]
        assert only_expected.empty and only_actual.empty, (
            f"Completeness check failed on columns {columns}: "
            f"{len(only_expected)} expected row(s) missing in actual, "
            f"{len(only_actual)} actual row(s) not present in expected.\n"
            f"Missing in actual (sample):\n{only_expected.head(10).to_string()}\n"
            f"Unexpected in actual (sample):\n{only_actual.head(10).to_string()}"
        )


    @staticmethod
    def check_dataset_is_not_empty(df):
        assert df is not None and len(df) > 0, "Dataset is empty: expected at least one row but got 0."

    @staticmethod
    def check_not_null_values(df, column_names):
        """Fail if any of the named columns contain NULL/NaN values."""
        columns = DataQualityLibrary._as_list(column_names)
        assert columns, "check_not_null_values requires at least one column name."
        DataQualityLibrary._require_columns(df, columns)
        null_counts = df[columns].isnull().sum()
        failing = null_counts[null_counts > 0]
        assert failing.empty, f"Not-null check failed. NULL counts per column: {failing.to_dict()}"
