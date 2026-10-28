import time
import pandas as pd
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains


BASE_DIR = Path(__file__).resolve().parent
SCREENSHOT_DIR = BASE_DIR / "screenshots"
OUTPUT_DIR = BASE_DIR / "output"
REPORT_DIR = BASE_DIR / "generated_report"

TABLE_HEADERS = ["Facility Type", "Visit Date", "Average Time Spent"]
DOUGHNUT_HEADERS = ["Facility Type", "Min Average Time Spent"]

WAIT_SECONDS = 10


class SeleniumWebDriverContextManager:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver: WebDriver | None = None

    def __enter__(self) -> WebDriver:
        options = Options()
        options.add_argument("--window-size=1920,1200")
        if self.headless:
            options.add_argument("--headless=new")
        self.driver = webdriver.Chrome(options=options)
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver:
            self.driver.quit()
        return False

    @staticmethod
    def find_report_file() -> Path:
        index = REPORT_DIR / "index.html"
        if index.exists():
            return index
        html_files = list(REPORT_DIR.glob("*.html"))
        if not html_files:
            raise FileNotFoundError(f"No HTML report file found in the generated_report directory: {REPORT_DIR}")
        return html_files[0]

    @staticmethod
    def text_of(element) -> str:
        return (element.get_attribute("textContent") or "").strip()

    @staticmethod
    def extract_table_data(driver: WebDriver) -> pd.DataFrame:
        wait = WebDriverWait(driver, WAIT_SECONDS)

        # By.CLASS_NAME
        table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table")))

        # By.CSS_SELECTOR
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".y-column text.cell-text")))

        # By.XPATH 
        columns = table.find_elements(
            By.XPATH, ".//*[contains(concat(' ', normalize-space(@class), ' '), ' y-column ')]"
        )
        if not columns:
            raise NoSuchElementException("No columns found in the table.")

        column_values = []
        for column in columns:
            cells = column.find_elements(By.CSS_SELECTOR, "text.cell-text")
            column_values.append([DriverContext.text_of(cell) for cell in cells])

        lengths = {len(values) for values in column_values}
        if len(lengths) != 1:
            raise ValueError(f"Columns have different lengths: {[len(v) for v in column_values]}")

        # In the DOM the header cell comes LAST: AFTER ALL DATA ROWS
        header = [values[-1] for values in column_values]
        if header != TABLE_HEADERS:
            raise ValueError(f"Unexpected header {header}, expected {TABLE_HEADERS}")

        body = [values[:-1] for values in column_values]
        return pd.DataFrame(list(zip(*body)), columns=header)

    @staticmethod
    def get_pie(driver: WebDriver):
        return WebDriverWait(driver, WAIT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "pielayer"))
        )

    @staticmethod
    def get_slice_texts(driver: WebDriver):
        pie = DriverContext.get_pie(driver)
        return pie.find_elements(By.CSS_SELECTOR, "text.slicetext, g.slicetext > text")

    @staticmethod
    def count_slices(driver: WebDriver) -> int:
        return len(DriverContext.get_slice_texts(driver))

    @staticmethod
    def extract_doughnut(driver: WebDriver) -> pd.DataFrame:
        rows = []
        for slice_text in DriverContext.get_slice_texts(driver):
            parts = [DriverContext.text_of(t) for t in slice_text.find_elements(By.TAG_NAME, "tspan")]
            parts = [p for p in parts if p]
            if len(parts) < 2:  # fallback if there are no tspans
                parts = DriverContext.text_of(slice_text).rsplit(" ", 1)
            if len(parts) >= 2:
                rows.append((" ".join(parts[:-1]), parts[-1]))
        return pd.DataFrame(rows, columns=DOUGHNUT_HEADERS)

    @staticmethod
    def get_legend_toggles(driver: WebDriver):
        legend = WebDriverWait(driver, WAIT_SECONDS).until(
            EC.presence_of_element_located((By.CLASS_NAME, "scrollbox"))
        )
        return legend.find_elements(By.CLASS_NAME, "legendtoggle")

    @staticmethod
    def click_element(driver: WebDriver, element) -> None:
        try:
            element.click()
        except (ElementClickInterceptedException, ElementNotInteractableException):
            ActionChains(driver).move_to_element(element).click().perform()

    @staticmethod
    def save_step(driver: WebDriver, step: int) -> None:
        time.sleep(0.7)  # let Plotly finish its transition animation
        driver.save_screenshot(str(SCREENSHOT_DIR / f"screenshot{step}.png"))
        DriverContext.extract_doughnut(driver).to_csv(OUTPUT_DIR / f"doughnut{step}.csv", index=False)
        print(f"step {step}: saved screenshot{step}.png and doughnut{step}.csv")

    @staticmethod
    def run_doughnut_filters(driver: WebDriver) -> None:
        total = len(DriverContext.get_legend_toggles(driver))
        if total == 0:
            raise NoSuchElementException("No legend items found")
        try:
            WebDriverWait(driver, WAIT_SECONDS).until(lambda d: DriverContext.count_slices(d) == total)
        except TimeoutException:
            raise TimeoutException(
                f"Expected {total} slices, found {DriverContext.count_slices(driver)}"
            )

        DriverContext.save_step(driver, 0)  # initial, unfiltered state

        for i in range(total):
            toggles = DriverContext.get_legend_toggles(driver)
            DriverContext.click_element(driver, toggles[i])
            expected_slices = total - (i + 1)
            try:
                WebDriverWait(driver, WAIT_SECONDS).until(lambda d: DriverContext.count_slices(d) == expected_slices)
            except TimeoutException:
                raise TimeoutException(f"Filter {i + 1} did not apply: expected {expected_slices} slices")
            DriverContext.save_step(driver, i + 1)  # the last one is the "all filters unselected" case


DriverContext = SeleniumWebDriverContextManager


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(exist_ok=True)
    SCREENSHOT_DIR.mkdir(exist_ok=True)

    with DriverContext() as driver:
        try:
            driver.get(DriverContext.find_report_file().as_uri())
            table_df = DriverContext.extract_table_data(driver)
            table_df.to_csv(OUTPUT_DIR / "table.csv", index=False)
            print(f"Table data extracted with {len(table_df)} rows, and saved as table.csv")
            DriverContext.run_doughnut_filters(driver)

        except (TimeoutException, NoSuchElementException, FileNotFoundError, ElementNotInteractableException, ValueError, ElementClickInterceptedException) as e:
            driver.save_screenshot(str(SCREENSHOT_DIR / "error_screenshot.png"))
            print(f"An error occurred: {type(e).__name__}. Screenshot saved as error_screenshot.png")
            raise e

