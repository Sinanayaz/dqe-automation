import os
import pyarrow.dataset as ds
import pandas as pd
import glob
import pyarrow.parquet as pq

CANONICAL_ROOT = "/parquet_data"

class ParquetReader:

    def __init__(self, root: str | None = None):
        self.root = root

    def _resolve(self, path: str) -> str:
        root = (self.root or CANONICAL_ROOT).rstrip("/")
        if root != CANONICAL_ROOT and (path == CANONICAL_ROOT or path.startswith(CANONICAL_ROOT + "/")):
            return os.path.join(root, path[len(CANONICAL_ROOT):].lstrip("/"))
        if not os.path.isabs(path):
            return os.path.join(root, path)
        return path

    def process(self, path: str, include_subfolders: bool = True) -> pd.DataFrame:
 
        full_path = self._resolve(path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Parquet path does not exist: {full_path}")

        if os.path.isfile(full_path):
            return pq.read_table(full_path).to_pandas()

        if include_subfolders:
            dataset = ds.dataset(full_path, format="parquet", partitioning=ds.partitioning(flavor="hive"))
            if not dataset.files:
                raise FileNotFoundError(f"No parquet files found under: {full_path}")
            return dataset.to_table().to_pandas()

        files = sorted(glob.glob(os.path.join(full_path, "*.parquet")))
        if not files:
            raise FileNotFoundError(f"No parquet files directly inside: {full_path}")
        return pd.concat([pq.read_table(f).to_pandas() for f in files], ignore_index=True)