from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium import webdriver
import time
class SiteScraper:
    def __init__(self, chrome_driver_path: str ):
        try:
            self.service = Service()
            self.chrome_options = ChromeOptions()
            self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        except FileNotFoundError:
            print("The ChromeDriver executable was not found. Is it installed and accessible in PATH?")
            quit()
        except Exception as e:
            print(f"An unknown error occurred: {e}")
            quit()

    
    def get_page_source(self, url, wait_time=5) -> str:
        """
        Get the page source of the given URL
        :param url: The URL of the page to scrape
        :param wait_time: The time to wait for the page to load (for JavaScript)
        """
        try:
            self.driver.get(url)
        except Exception as e:
            print(f"An error occurred while trying to get the page source: {e}")
            return ""
        if wait_time > 0:
            time.sleep(5)
        return self.driver.page_source

    def close(self):
        """
        Close the WebDriver
        """
        self.driver.quit()
        self.service.stop()
        print("WebDriver closed successfully")