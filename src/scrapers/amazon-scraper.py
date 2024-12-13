import json
import logging
import os
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

MAX_FILE_LENGTH = 255

logging.basicConfig(
    level=logging.INFO,
)

# detect number of workers


def get_num_workers():
    try:
        return os.cpu_count()
    except Exception as e:
        logging.warning(f"Could not detect number of workers: {e}")
        return 1


with open("../headers.json") as header_file:
    config = json.load(header_file)
    headers = config["headers"]

base_url = "https://www.amazon.eg/s?i=electronics&rh={}&fs=true&page={}&language=en&"

# TODO: add more categories
categories = [
    {"n%3A21833212031": "cpu"},
    {"n%3A21833215031": "gpu"},
    {"n%3A21832918031": "data_storage"},
    {"n%3A21832907031": "laptop"},
]

product_list = []


def sanitize_filename(filename):
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    return sanitized[:MAX_FILE_LENGTH]


def insert_products_into_db(product_list, db_path="../db/amazon.db"):
    if not os.path.exists("../db"):
        os.makedirs("../db")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS products (
            title TEXT,
            price TEXT,
            link TEXT,
            category TEXT,
            image TEXT
        )"""
    )

    for product in product_list:
        c.execute(
            "INSERT INTO products (title, price, link, category, image) VALUES (?, ?, ?, ?, ?)",
            (
                product["title"],
                product["price"],
                product["link"],
                product["category"],
                product["image"],
            ),
        )

    conn.commit()
    conn.close()


def download_image(image_url, image_path):
    response = requests.get(image_url, timeout=20)
    with open(image_path, "wb") as file:
        file.write(response.content)


def main():
    with ThreadPoolExecutor(max_workers=get_num_workers()) as executor:
        for category in categories:
            for category_id, category_name in category.items():
                logging.info(
                    f"processing category: {category_name} with id: {category_id}"
                )
                page = 1
                while True:
                    url = base_url.format(category_id, page)
                    logging.info(f"Scraping {url}")
                    logging.info(f"Page: {page}")

                    max_retries = 20
                    for attempt in range(max_retries):
                        try:
                            response = requests.get(url, headers=headers, timeout=20)
                            response.raise_for_status()
                            break
                        except requests.exceptions.RequestException as e:
                            logging.warning(
                                f"Request failed (attempt {attempt + 1}/{max_retries}): {e}"
                            )
                            if attempt < max_retries - 1:
                                time.sleep(0.1)
                            else:
                                return

                    soup = BeautifulSoup(response.content, "html.parser")

                    no_results = soup.find("span", class_="a-size-medium a-color-base")

                    if no_results and "No results for " in no_results.text:
                        logging.info("No more results")
                        break

                    main_div_pattern = re.compile(
                        r"\bpuis-card-container\b.*\bs-card-container\b.*\bs-overflow-hidden\b.*\baok-relative\b.*\bpuis-expand-height\b.*\bpuis-include-content-margin\b.*\bs-latency-cf-section\b.*\bpuis-card-border\b"
                    )

                    main_div = soup.find_all("div", class_=main_div_pattern)

                    for div in main_div:
                        title_element = div.find(
                            "h2",
                            class_="a-size-base-plus a-spacing-none a-color-base a-text-normal",
                        )

                        if title_element:
                            title = title_element.text
                            logging.info(title)
                        else:
                            logging.warning("Title not available")
                            continue

                        # price
                        wholeprice_element = div.find("span", class_="a-price-whole")
                        fraction_element = div.find("span", class_="a-price-fraction")

                        if wholeprice_element and fraction_element:
                            wholeprice = wholeprice_element.text
                            fraction = fraction_element.text
                        else:
                            wholeprice = "N/A"
                            fraction = ""
                            logging.info("Price not available")

                        link_element = div.find(
                            "a",
                            class_="a-link-normal s-line-clamp-4 s-link-style a-text-normal",
                        )
                        if link_element:
                            link = "https://www.amazon.eg" + link_element["href"]
                        else:
                            link = "N/A"
                            logging.warning("Link not available")

                        picture_element = div.find("img", class_="s-image")
                        if picture_element:
                            picture = picture_element["src"]
                        else:
                            picture = ""
                            logging.warning("Picture not available")

                        if not os.path.exists("../images"):
                            os.makedirs("../images")

                        # sanitize title
                        sanitized_title = sanitize_filename(title)

                        image_path = f"../images/{sanitized_title}.jpg"

                        if picture:
                            executor.submit(download_image, picture, image_path)

                        product_list.append(
                            {
                                "title": title,
                                "price": wholeprice + "" + fraction,
                                "link": link,
                                "category": category_name,
                                "image": image_path,
                            }
                        )

                    page += 1

    insert_products_into_db(product_list)


if __name__ == "__main__":
    main()
