*** Settings ***
Documentation     Validates that the table in report.html matches the Parquet dataset.
Library           SeleniumLibrary
Library           helper.py
Test Teardown     Close All Browsers

*** Variables ***
${REPORT_FILE}         ${CURDIR}${/}generated_report${/}report.html
${PARQUET_FOLDER}      ${CURDIR}${/}parquet_data${/}facility_type_avg_time_spent_per_visit_date
${FILTER_DATE}         2026-09-25
${DATE_COLUMN}         visit_date
${SORT_COLUMNS}        visit_date,facility_type
${DROP_COLUMNS}        partition_date
${IGNORE_ROW_ORDER}    ${FALSE}
${TABLE_LOCATOR}       xpath://div[contains(@class,'js-plotly-plot')][.//*[contains(@class,'y-column')]]
&{COLUMN_MAP}          facility_type=Facility Type    visit_date=Visit Date    avg_time_spent=Average Time Spent

*** Test Cases ***
HTML Report Table Should Match Parquet Dataset
    [Documentation]    Reads the report table and the Parquet data, then compares them.
    [Tags]    data-quality    report

    ${report_url}=    Path To File Url    ${REPORT_FILE}
    Open Browser    ${report_url}    chrome
    Wait Until Element Is Visible    ${TABLE_LOCATOR}    timeout=15s
    ${table}=    Get WebElement    ${TABLE_LOCATOR}

    ${html_df}=       Read Html Table    ${table}
    ${parquet_df}=    Read Parquet Dataset    ${PARQUET_FOLDER}
    ...    filter_date=${FILTER_DATE}
    ...    date_column=${DATE_COLUMN}
    ...    sort_columns=${SORT_COLUMNS}
    ...    drop_columns=${DROP_COLUMNS}
    ...    column_map=${COLUMN_MAP}

    ${differences}=    Compare Dataframes    ${html_df}    ${parquet_df}
    ...    ignore_row_order=${IGNORE_ROW_ORDER}
    ${count}=    Get Length    ${differences}

    IF    ${count} > 0
        ${details}=    Catenate    SEPARATOR=\n    @{differences}
        Fail    Data mismatch found:\n${details}
    END
    Log    HTML table and Parquet data match exactly.