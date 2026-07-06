from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import string

print("Starting automation test for steganography project...")

options = webdriver.ChromeOptions()
options.add_experimental_option("excludeSwitches", ["enable-logging"])
driver = webdriver.Chrome(options=options)


def generate_random_user():
    rnd = "".join(random.choices(string.ascii_lowercase + string.digits, k=5))
    return f"tester_{rnd}", f"test_{rnd}@example.com", "Test@1234"


try:
    username, email, password = generate_random_user()

    print("Opening Homepage...")
    driver.get("http://127.0.0.1:5000")
    driver.maximize_window()
    time.sleep(3)

    print("Navigating to Sign Up Page...")
    driver.get("http://127.0.0.1:5000/auth/signup")

    print(f"Registering new user: {username}")

    username_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "username"))
    )

    username_field.send_keys(username)
    time.sleep(0.5)
    driver.find_element(By.NAME, "email_or_mobile").send_keys(email)
    time.sleep(0.5)
    driver.find_element(By.NAME, "password").send_keys(password)
    time.sleep(0.5)
    confirm_field = driver.find_element(By.NAME, "confirm_password")
    confirm_field.send_keys(password)
    time.sleep(1)

    confirm_field.send_keys(Keys.RETURN)
    time.sleep(3)

    print("Logging in...")
    driver.find_element(By.NAME, "identifier").send_keys(username)
    time.sleep(1)
    driver.find_element(By.NAME, "password").send_keys(password)
    time.sleep(1)
    driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
    time.sleep(4)

    current_url = driver.current_url
    if "dashboard" in current_url:
        print("Successfully reached Dashboard")

        driver.get("http://127.0.0.1:5000/hide")
        time.sleep(3)

        driver.get("http://127.0.0.1:5000/extract")
        time.sleep(3)

        print("Test passed successfully.")
    else:
        print("Failed to reach Dashboard.")

except Exception as e:
    print(f"Error: {e}")

finally:
    print("Closing browser in 5 seconds...")
    time.sleep(5)
    driver.quit()
