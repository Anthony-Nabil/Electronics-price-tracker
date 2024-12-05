import requests
from bs4 import BeautifulSoup
import time
# from fuzzywuzzy import fuzz
# from fuzzywuzzy import process
import sqlite3
import os
import re
import json


MAX_FILE_LENGTH = 255

with open("headers.json", "r") as header_file:
    config = json.load(header_file)
    headers = config["headers"]

# TODO: add more categories
categories = [
    {"n%3A21833212031": "cpu"},
    {"n%3A21833215031": "gpu"},
    {"n%3A21832918031": "data_storage"},
    {"n%3A21832907031": "laptop"}
]

base_url = "https://www.amazon.eg/s?i=electronics&rh={}&fs=true&page={}&language=en&"

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


def main():
    for category in categories:
        for category_id, category_name in category.items():
            print(f"processing category: {category_name} with id: {category_id}")
            page = 1
            while True:
                url = base_url.format(category_id, page)
                print(url)
                print(f"Page: {page}")

                max_retries = 6
                for attempt in range(max_retries):
                    try:
                        response = requests.get(url, headers=headers)
                        # print(response.text)
                        response.raise_for_status()
                        break
                    except requests.exceptions.RequestException as e:
                        print(
                            f"Request failed (attempt {attempt + 1}/{max_retries}): {e}"
                        )
                        if attempt < max_retries - 1:
                            time.sleep(0.1)
                        else:
                            return

                soup = BeautifulSoup(response.content, "html.parser")

                no_results = soup.find("span", class_="a-size-medium a-color-base")

                if no_results and "No results for " in no_results.text:
                    print("No more results")
                    break

                main_div_pattern = re.compile(r'\bpuis-card-container\b.*\bs-card-container\b.*\bs-overflow-hidden\b.*\baok-relative\b.*\bpuis-expand-height\b.*\bpuis-include-content-margin\b.*\bs-latency-cf-section\b.*\bpuis-card-border\b')

                main_div = soup.find_all(
                    "div",
                    class_=main_div_pattern
                )

                # print(main_div)

                for div in main_div:
                    title = div.find(
                        "span", class_="a-size-base-plus a-color-base a-text-normal"
                    ).text
                    print(title)

                    # price
                    wholeprice_element = div.find("span", class_="a-price-whole")
                    fraction_element = div.find("span", class_="a-price-fraction")

                    if wholeprice_element and fraction_element:
                        wholeprice = wholeprice_element.text
                        fraction = fraction_element.text
                        # print(wholeprice + "" + fraction)
                    else:
                        print("Price not available")

                    link = div.find(
                        "a",
                        class_="a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal",
                    )["href"]
                    link = "https://www.amazon.eg" + link
                    # print(link)

                    picture = div.find("img", class_="s-image")["src"]

                    if not os.path.exists("../images"):
                        os.makedirs("../images")

                    # sanitize title
                    sanitized_title = sanitize_filename(title)

                    image_path = f"../images/{sanitized_title}.jpg"

                    if not os.path.exists(image_path):
                        with open(f"../images/{sanitized_title}.jpg", "wb") as file:
                            response = requests.get(picture)
                            file.write(response.content)

                    product_list.append(
                        {
                            "title": title,
                            "price": wholeprice + "" + fraction,
                            "link": link,
                            "category": category_name,
                            "image": "../images/" + sanitized_title + ".jpg",
                        }
                    )

                page += 1

    # print(product_list)

    insert_products_into_db(product_list)

if __name__ == "__main__":
    main()