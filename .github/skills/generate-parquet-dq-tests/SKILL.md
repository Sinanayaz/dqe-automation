---
name: generate-parquet-dq-tests
description: >-
  Creates one PyTest data quality module per Parquet dataset under
  tests/dq checks/parquet_files/, deriving the expected Postgres query only from
  docs/parquet-aggregated-data-mapping.md and always producing the five mandatory
  checks: smoke, completeness, count, uniqueness, not-null. Invoke explicitly by
  name for a named dataset. Refuses to change the framework (library, connectors,
  conftest, pytest.ini, Jenkinsfile), to add extra tests, or to use pipeline code
  as the expected result.
disable-model-invocation: true
---

# Generate Parquet DQ tests

- `PyTest DQ Framework/docs/test-automation-strategy.md` — **§5 Skill contract**, **§6 Test design standard**
- `docs/parquet-aggregated-data-mapping.md` — dataset definitions (expected SQL comes from here)

**Do not** paste expected SQL for the three named datasets into this skill.  
**Do not** instruct the agent to copy SQL from `data_dev/`.


## When this skill applies

Use this skill when the user explicitly names `generate-parquet-dq-tests` and asks for tests for one
Parquet dataset.

Before generating, check that the framework already exists. If something is missing, stop and tell the
user what is missing. Do not create it.

- `src/connectors/postgres/postgres_connector.py` provides `get_data_sql`.
- `src/connectors/file_system/parquet_reader.py` provides `process(path, include_subfolders=True)`.
- `src/data_quality/data_quality_validation_library.py` provides `check_dataset_is_not_empty`,
  `check_data_completeness`, `check_count`, `check_duplicates` and `check_not_null_values`.
- `tests/conftest.py` provides the session fixtures `db_connection`, `parquet_reader` and
  `data_quality_library`.
- `tests/pytest.ini` registers the markers `parquet_data` and `smoke`, plus a marker named exactly like
  the dataset.

Allowed output path: `PyTest DQ Framework/tests/dq checks/parquet_files/test_<dataset_name>.py`, one
dataset per file. Writing anywhere else is not allowed.

Refuse, and explain why, if the user asks you to:

- edit the library, connectors, `conftest.py`, `pytest.ini`, `requirements.txt` or the Jenkinsfile;
- add tests beyond the five mandatory ones;
- take expected SQL from anywhere other than the mapping;
- change expected SQL so that a failing run turns green;
- put several datasets into one module.

## Inputs you must have

Required inputs and where mapping lives (docs/parquet-aggregated-data-mapping.md).

1. **Dataset name.** It must be a snake_case heading in the mapping file and the same name as the
   folder under `/parquet_data/`.
2. **Mapping.** Read the section for that dataset in `docs/parquet-aggregated-data-mapping.md`: target
   columns, transformations, source tables and columns, comments (grouping, not null, rounding, format),
   filters and partitioning.
3. **Header values.** Use the author and requirement id the user gives. If none are given, keep the
   template placeholders `TICKET-1234` and `Name Surname` and do not invent values.

If the mapping file or the dataset section is missing, stop and ask the user. Never reconstruct a mapping
from memory, from parquet previews or from the code that produced the data.

Forbidden sources for the expected result:

- anything under `data_dev/`, including its query files and the parquet loader SQL;
- previews or samples of the parquet files;
- the `src_generated_*` staging tables in Postgres;
- the dataset summary table in the TAS, where it disagrees with the mapping. The mapping wins.

The only allowed source tables are the 3NF tables `facilities`, `patients` and `visits`.

## Hard rules

1. Dataset-agnostic. No hardcoded SQL for the three known datasets inside SKILL.md. The skill explains how to derive SQL from a mapping.
2. Source = Postgres, target = Parquet. Do not swap fixtures (the sample test_examples.py has placeholders and mixed direction — follow the TAS (sections 5.4 and 6.2), not the placeholder names).
3. Do not read data_dev/ (especially queries.py and parquet-loader SQL) to build expected queries.
4. Do not add UNION / extra WHERE / CASE / sign flips unless they are in the mapping.
5. Aliases and grain of source_data must match the Parquet schema / mapping names.
6. target_path is /parquet_data/<dataset_name> with include_subfolders=True.
7. Markers: parquet_data, dataset-specific mark, smoke only on the not-empty test.
8. Not-null column list = mapped output columns for that dataset.



## Workflow

1. Confirm the framework prerequisites listed above exist.
2. Read the dataset section of the mapping and write down: the output columns (in mapping order), the
   grouping columns, the measures and their transformations, the source tables and columns, any
   filters, and any comments such as rounding and format.
3. Derive the expected query using "SQL derivation". Stop there. Do not run it against the pipeline
   output and do not adjust it afterwards.
4. Copy the template into `test_<dataset_name>.py`. Replace every placeholder: the dataset name in the
   docstring, the path and the markers, the expected query, and the not-null column list.
5. Fill the header. Use the user's values if given, otherwise keep the template placeholders.
6. Run the self-check:
   - Five tests, in order, with the exact names.
   - Markers are correct, and `smoke` appears on the not-empty test only.
   - Fixture directions are correct (Postgres is the source, Parquet is the target).
   - The not-null list equals the mapped columns.
   - The query contains nothing the mapping does not state.
7. Report to the user: the file path, the mapping decisions that required interpretation, and any
   ambiguity you could not resolve from the mapping. Ask about ambiguities. Do not guess silently.


## Template

```python
"""
"""
Description: Data Quality checks for <dataset_name> dataset.
Requirement(s): TICKET-1234
Author(s): <name>
"""

import pytest


@pytest.fixture(scope='module')
def source_data(db_connection):
    source_query = """
    -- expected query derived from mapping (grain + measures + joins)
    """
    return db_connection.get_data_sql(source_query)


@pytest.fixture(scope='module')
def target_data(parquet_reader):
    target_path = '/parquet_data/<dataset_name>'
    return parquet_reader.process(target_path, include_subfolders=True)


@pytest.mark.parquet_data
@pytest.mark.smoke
@pytest.mark.<dataset_name>
def test_check_dataset_is_not_empty(target_data, data_quality_library):
    data_quality_library.check_dataset_is_not_empty(target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_data_completeness(source_data, target_data, data_quality_library):
    data_quality_library.check_data_completeness(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_count(source_data, target_data, data_quality_library):
    data_quality_library.check_count(source_data, target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_uniqueness(target_data, data_quality_library):
    data_quality_library.check_duplicates(target_data)


@pytest.mark.parquet_data
@pytest.mark.<dataset_name>
def test_check_not_null_values(target_data, data_quality_library):
    data_quality_library.check_not_null_values(target_data, ['<col_1>', '<col_2>', '<col_3>'])

```

## SQL derivation (generic)


Follow the order of TAS 6.3. All names below are placeholders. Take the real names only from the mapping.

1. **Tables and joins.** Identify the 3NF source tables named in the mapping. The `visits` table is
   joined to each dimension table (`facilities`, `patients`) through its foreign key
   (`visits.<dimension>_id = <dimension>.id`). Use inner joins unless the mapping says otherwise. Join
   only the tables that supply mapped columns.
2. **Dimensions (grain).** Every mapped column commented as "grouping" becomes a select expression and
   appears in `GROUP BY`. The mapped columns together are the grain. Do not group by anything that is
   not a mapped output column.
3. **Date columns.** If the mapped source column is a timestamp and the mapped target column is a date
   (the mapping name and sample show a date, not a time), reduce the timestamp to its calendar date.
   Use the same expression in `SELECT` and `GROUP BY`.
4. **Name columns.** If the mapping gives a format for a combined text column, build it exactly as
   described. For example, with a "separated by space" format, join the parts in the stated order with
   exactly one space. Do not add trimming, casing or other cleaning that the mapping does not state.
5. **Measures.** Implement the mapped transformation exactly: the stated aggregate function over the
   stated source column. Apply stated rounding with the stated number of decimal places, and apply none
   if none is stated. Do not change the sign, scale or type of a measure.
6. **Aliases.** Alias every output expression to its mapping target column name, in mapping order.
7. **Filters.** Add a `WHERE` condition only if the mapping's "Filters" line states one. A dash means no
   filter.
8. **Stop.** Do not compare the query with parquet output and do not "fix" it to match. A mismatch
   between this query and the Parquet data is the finding the test exists to detect.

Generic shape. This is a structure only, not a query for any dataset:

```sql
SELECT
    <grouping_expression> AS <target_column>,
    <aggregate_function>(<source_column>) AS <target_measure>
FROM <fact_table> f
JOIN <dimension_table> d ON f.<foreign_key> = d.id
GROUP BY <grouping_expression>
```

## After generation

- Do not run pytest unless the user asks. If asked, run only the new module with its dataset marker and
  report the outcome as it is.
- If checks fail, do not edit the expected query, loosen the library or remove checks to get a green
  run. A failure means the Parquet data disagrees with the mapping. Describe it as a transformation or
  mapping defect: dataset, test name, what the mapping expects, what the Parquet data contains
  (from the assertion message), and the likely cause in the transformation.
- If the failure looks like a wrong query on your side, re-read the mapping and correct the query only
  where it deviates from the mapping, then tell the user exactly what you changed and why.
- Never claim that the data is correct because the run is green without saying that the expected query
  came from the mapping.

---

## Skill review (self-check before Step 3)

Reject your own skill if any of these are true:

- [ ] Contains concrete expected SQL for `facility_name_min_time_spent_per_visit_date`, `facility_type_avg_time_spent_per_visit_date`, or `patient_sum_treatment_cost_per_facility_type`
- [ ] Tells the agent to use `data_dev/` or parquet loader SQL
- [ ] Omits completeness, count, uniqueness, or not-null
- [ ] Swaps Postgres vs Parquet fixtures or generates trivial always-pass checks
- [ ] Any section still says `TODO`
