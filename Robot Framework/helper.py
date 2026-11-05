from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from robot.api import logger
from selenium.webdriver.common.by import By



def path_to_file_url(path):
    return Path(path).expanduser().resolve().as_uri()


def read_html_table(table):
    columns = []
    for col in table.find_elements(By.CSS_SELECTOR, ".y-column"):
        cells = col.find_elements(By.CSS_SELECTOR, ".cell-text")
        if not cells:
            continue
        cells.sort(key=lambda cell: cell.location["y"])
        values = [" ".join((cell.get_attribute("textContent") or "").split())
                  for cell in cells]
        columns.append((col.location["x"], values))

    if not columns:
        raise ValueError("No table columns (.y-column) found in the given element.")

    columns.sort(key=lambda item: item[0])
    headers = [values[0] for _, values in columns]
    if len(set(headers)) != len(headers):
        raise ValueError(f"Duplicate column names in the table: {headers}")

    df = pd.DataFrame({h: values[1:] for h, (_, values) in zip(headers, columns)})
    logger.info(f"Report table loaded: {df.shape[0]} rows x {df.shape[1]} columns")
    logger.info(df.to_string())
    return df


def read_parquet_dataset(folder, filter_date=None, date_column="visit_date",
                         sort_columns=None, drop_columns=None, column_map=None):
    path = Path(folder)
    if not path.exists():
        raise FileNotFoundError(f"Parquet folder not found: {path}")

    df = pd.read_parquet(path)

    for col in df.select_dtypes(include="category").columns:
        df[col] = df[col].astype(object)

    # Keep rows where date_column >= filter_date
    if filter_date and str(filter_date).strip().lower() != "none":
        start = datetime.strptime(str(filter_date).strip(), "%Y-%m-%d")
        if date_column not in df.columns:
            raise ValueError(
                f"Column '{date_column}' not found. Available: {list(df.columns)}"
            )
        df = df[pd.to_datetime(df[date_column]) >= start]
        if df.empty:
            logger.warn(f"No rows found with {date_column} >= {filter_date}.")

    if sort_columns:
        cols = [c.strip() for c in str(sort_columns).split(",") if c.strip()]
        df = df.sort_values(cols, ascending=False)

    if drop_columns:
        to_drop = [c.strip() for c in str(drop_columns).split(",") if c.strip()]
        df = df.drop(columns=to_drop)

    # Rename Parquet columns to the report headers
    if column_map:
        df = df.rename(columns=dict(column_map))

    df = df.reset_index(drop=True)
    logger.info(f"Parquet loaded: {df.shape[0]} rows x {df.shape[1]} columns")
    logger.info(df.to_string())
    return df


def compare_dataframes(html_df, parquet_df, ignore_row_order=False,
                       max_differences=100):
    diffs = []

    html_cols, pq_cols = list(html_df.columns), list(parquet_df.columns)
    for col in html_cols:
        if col not in pq_cols:
            diffs.append(f"Column '{col}' exists only in the HTML table.")
    for col in pq_cols:
        if col not in html_cols:
            diffs.append(f"Column '{col}' exists only in the Parquet data.")

    common = [c for c in html_cols if c in pq_cols]

    if len(html_df) != len(parquet_df):
        diffs.append(
            f"Row count differs: HTML={len(html_df)}, Parquet={len(parquet_df)}"
        )

    left = _normalize(html_df[common])
    right = _normalize(parquet_df[common])

    if ignore_row_order and common:
        left = left.sort_values(common).reset_index(drop=True)
        right = right.sort_values(common).reset_index(drop=True)

    left_rows, right_rows = left.values.tolist(), right.values.tolist()
    shared = min(len(left_rows), len(right_rows))

    for i in range(shared):
        for j, col in enumerate(common):
            if left_rows[i][j] != right_rows[i][j]:
                diffs.append(
                    f"Row {i + 1}, column '{col}': "
                    f"HTML='{left_rows[i][j]}' | Parquet='{right_rows[i][j]}'"
                )

    for i in range(shared, len(left_rows)):
        diffs.append(f"Row {i + 1} exists only in HTML: {left_rows[i]}")
    for i in range(shared, len(right_rows)):
        diffs.append(f"Row {i + 1} exists only in Parquet: {right_rows[i]}")

    total = len(diffs)
    if total > max_differences:
        diffs = diffs[:max_differences]
        diffs.append(f"... and {total - max_differences} more differences")

    return diffs



def _normalize(df):
    return df.apply(lambda column: column.map(_normalize_value))


def _normalize_value(value):
    if value is None:
        return ""
    if pd.api.types.is_scalar(value) and pd.isna(value):
        return ""
    if isinstance(value, datetime):
        if value.time() == time(0):
            return value.date().isoformat()
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    try:
        number = Decimal(text)
        if number.is_finite():
            return format(number.normalize(), "f")
    except InvalidOperation:
        pass
    return text