# PyTest Introduction

Run these 3 commands from PyTest Introduction directory:

- All tests: 
pytest -c tests/pytest.ini --html=reports/all_tests/report.html

- Unmarked tests: 
pytest -c tests/pytest.ini -m unmarked --html=reports/unmarked/report.html

- CSV validation tests, excluding expected failures: 
pytest -c tests/pytest.ini -m "validate_csv and not xfail" --html=reports/validate_csv/report.html
