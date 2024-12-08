#pip install selenium webdriver-manager pandas


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd

# Set up the Chrome WebDriver
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Set an implicit wait
driver.implicitly_wait(10)

# Navigate to the specified URL
driver.get("https://mcscertified.com/product-directory/")

# Set an explicit wait
wait = WebDriverWait(driver, 15)

# Loop through all pages
while True:
    # List of selectors to click on
    selectors = [
        f"#ProductResultsTableAllBody > tr:nth-child({i}) > td > div > div.row > div > span"
        for i in range(1, 11)
    ]

    # Iterate over each selector and click on the element
    for selector in selectors:
        success = False
        for attempt in range(2):  # Attempt up to 2 times
            try:
                target_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))
                driver.execute_script("arguments[0].click();", target_element)  # JavaScript click to ensure interaction
                print(f"Clicked on the target element for selector: {selector} successfully.")
                success = True
                break
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for selector {selector}: {e}")
                time.sleep(5)  # Wait a bit before retrying

        if not success:
            print(f"Failed to click on the target element for selector: {selector} after 2 attempts.")

    # Wait for all elements with class "msw-list-view-item" to be present and save them to a DataFrame
    try:
        items = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "msw-list-view-item")))
        print(f"Found {len(items)} items with class 'msw-list-view-item'.")
        data = []
        for item in items:
            text = item.text.split('\n')
            # Extract basic product information
            item_data = {
                "Product Name": text[0] if len(text) > 0 else "Not Available",
                "Certification Number": text[1].replace("Certification Number: ", "") if len(text) > 1 else "Not Available",
                "Model Number": text[2].replace("Model Number: ", "") if len(text) > 2 else "Not Available",
                "Certification Period": text[3].replace("Certification Period: ", "") if len(text) > 3 else "Not Available",
                "Manufacturer": text[6] if len(text) > 6 else "Not Available",
                "Technology": text[10] if len(text) > 10 else "Not Available",
                "Certification Body": text[12] if len(text) > 12 else "Not Available",
                "Current Certification Status": text[14] if len(text) > 14 else "Not Available"
            }

            # Extract SCOP values from the table
            try:
                scop_table = item.find_element(By.ID, "msw-product-scop-container")
                scop_rows = scop_table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip the header row
                for row in scop_rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) == 2:
                        flow_temp = cells[0].text.strip()
                        scop_value = cells[1].text.strip()
                        item_data[flow_temp] = float(scop_value) if scop_value else 0.0
            except Exception as e:
                print(f"No SCOP table found or error while extracting SCOP values for product '{item_data['Product Name']}': {e}")

            data.append(item_data)
            print(f"Extracted data for item: {item_data}")

        # Create a DataFrame and append it to the CSV file
        df = pd.DataFrame(data)
        # Ensure that all SCOP columns (from 35°C to 65°C) are present and filled appropriately
        all_flow_temps = [f"{i}°C" for i in range(35, 66)]
        for col in all_flow_temps:
            if col not in df.columns:
                df[col] = 0.0
        df = df.reindex(columns=list(df.columns)).fillna(0.0)  # Fill any remaining empty cells with 0.0
        with open('MCS_Product_Data_Base_June_24.csv', 'a', newline='', encoding='utf-8') as f:
            df.to_csv(f, index=False, header=f.tell() == 0)  # Write header only if file is empty

        # Clear the list of WebElement references to free memory
        items.clear()
        del items
        del data
    except Exception as e:
        print(f"An error occurred: {e}")

    # Try to click on the next page button by navigating through pagination buttons
    try:
        pagination_container = driver.find_element(By.ID, "ProductResultsTableAll_paginate")
        page_buttons = pagination_container.find_elements(By.CSS_SELECTOR, "a.paginate_button")

        # Iterate through page buttons (excluding "previous" and "next")
        current_page = pagination_container.find_element(By.CSS_SELECTOR, "a.paginate_button.current")
        current_page_idx = int(current_page.get_attribute("data-dt-idx"))

        next_page_button = None
        for page_button in page_buttons:
            if "previous" in page_button.get_attribute("id") or "next" in page_button.get_attribute("id"):
                continue
            page_idx = int(page_button.get_attribute("data-dt-idx"))
            if page_idx == current_page_idx + 1:
                next_page_button = page_button
                break

        if next_page_button:
            driver.execute_script("arguments[0].click();", next_page_button)
            print(f"Clicked on page {next_page_button.text} button successfully.")
            time.sleep(3)  # Wait for the page to load
        else:
            print("No more pages left to navigate.")
            break
    except Exception as e:
        print("No more pages left or error while navigating pages: ", e)
        break

# Close the browser
driver.quit()
