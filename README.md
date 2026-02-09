# Publix-Discount-Detector
Quick script that scans the publix weekly ads page to scan for discounts of a user inputted item in a user inputted store. Integrated with Selenium.


# HOW TO RUN

Download the script:

Download publix_deal_scraper.py

Download requirements.txt


Create a virtual environment:

python3 -m venv venv

source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

# DEPENDENCIES

The script requires the following Python packages:
selenium>=4.0.0
beautifulsoup4>=4.9.0
lxml>=4.6.0
These will be automatically installed when you run:

pip install -r requirements.txt

# USAGE

Basic Usage

Activate your virtual environment (if not already activated):

source venv/bin/activate  # On Windows: venv\Scripts\activate

Run the scraper:

python publix_deal_scraper.py
