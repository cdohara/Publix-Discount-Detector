# Publix-Discount-Detector
Quick script that scans the publix weekly ads page to scan for discounts of a user inputted item in a user inputted store. Integrated with Selenium. Dependency management with uv.

# HOW TO RUN

1. Clone the git repository
2. Install uv (if not already)
3. Get dependencies with  `uv sync`
4. Run the scrper via uv with `uv run publix-deal-scraper`

# CONFIGURATION

Modify the provided config.toml. Use your intuition to figure out how to use it. Alternatively, use program args.

# DEPENDENCIES

The script requires the following Python packages:
selenium>=4.0.0
beautifulsoup4>=4.9.0
lxml>=4.6.0
These will be automatically installed when you run: `uv sync`
