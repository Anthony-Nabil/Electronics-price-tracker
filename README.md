## Setup

1. Clone the repository:
    ```sh
    git clone https://github.com/Anthony-Nabil/Electronics-price-tracker
    cd Electronics-price-tracker
    ```

2. Install the requirements:
    ```sh
    pip install -r requirements.txt
    ```

3. Create a `headers.json` file in the root directory 

## Usage

1. To run the scrapers independently:
    ```sh
    python src/scrapers/<scraper_name>.py
    ```

    For example:
    ```sh
    python src/scrapers/amazon-scraper.py
   ```

2. The scraped data will be stored in a SQLite database located at `../db/` directory.

## Project Structure

- `src/scrapers/*`: Contains the scraper scripts.
- `headers.json`: Configuration file for request headers.
- `../db/`: Directory where the SQLite database will be stored.
- `../images/`: Directory where product images will be saved.