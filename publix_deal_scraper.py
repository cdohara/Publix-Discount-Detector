#!/usr/bin/env python3
"""
Publix Weekly Ad Deal Finder - Interactive Version
Simple scraper with user input - prints results directly to console.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re

def setup_driver(headless=True):
    """Set up Chrome WebDriver."""
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    return webdriver.Chrome(options=options)

def scroll_page(driver):
    """Scroll to load all lazy-loaded content."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    for _ in range(5):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

def detect_bogo(text):
    
    #Detect BOGO deals with multiple patterns.

    text_lower = text.lower()
    
    # Pattern 1: "Buy 1 Get 1" (most common)
    if re.search(r'buy\s*\d+\s*get\s*\d+', text_lower):
        return True
    
    # Pattern 2: Traditional "BOGO"
    if 'bogo' in text_lower:
        return True
    
    # Pattern 3: Spelled out variations
    bogo_phrases = [
        'buy one get one',
        'buy 1 get 1',
        'b1g1',
        'buy one, get one'
    ]
    
    return any(phrase in text_lower for phrase in bogo_phrases)

def categorize_deal(text, prices):
    if detect_bogo(text):
        return "BOGO"
    elif 'save' in text.lower() or re.search(r'save\s*up\s*to', text.lower()):
        return "Discount"
    elif len(prices) > 1:
        return "Price Drop"
    return "Deal"

def extract_deal_info(container):
    try:
        full_text = container.get_text(separator='\n', strip=True)
        
        if not full_text or len(full_text) < 5:
            return None
        
        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
        product_name = lines[0] if lines else 'Unknown Product'
        
        # Extract prices
        prices = re.findall(r'\$\d+\.\d{2}', full_text)
        current_price = prices[0] if prices else None
        
        # Detect BOGO
        is_bogo = detect_bogo(full_text)
        
        # Extract savings amount
        savings = None
        savings_match = re.search(r'save\s*up\s*to\s*\$(\d+\.\d{2})', full_text.lower())
        if savings_match:
            savings = f"${savings_match.group(1)}"
        elif not savings_match:
            savings_match = re.search(r'save\s*\$(\d+\.\d{2})', full_text.lower())
            if savings_match:
                savings = f"${savings_match.group(1)}"
        
        # Get deal description
        deal_description = None
        for line in lines:
            line_lower = line.lower()
            if 'buy' in line_lower and 'get' in line_lower:
                deal_description = line
                break
            elif 'save' in line_lower:
                deal_description = line
                break
        
        # Categorize deal type
        deal_type = categorize_deal(full_text, prices)
        
        
        # Only include if there's actually a deal
        has_deal = is_bogo or savings or deal_description or len(prices) > 1
        
        if not has_deal:
            return None
        
        return {
            'product_name': product_name,
            'current_price': current_price,
            'savings': savings,
            'deal_type': deal_type,
            'deal_description': deal_description,
            'is_bogo': is_bogo,
            'full_text': full_text
        }
        
    except Exception:
        return None

def find_deals(soup):
    """Find all product deals on the page."""
    deals = []
    
    # Strategy: Look for price elements and walk up to find containers
    price_elements = soup.find_all(string=re.compile(r'\$\d+\.\d{2}'))
    
    product_containers = set()
    for price_elem in price_elements:
        parent = price_elem.parent
        for _ in range(10):
            if parent and parent.name == 'div':
                classes = parent.get('class', [])
                class_str = ' '.join(classes).lower()
                
                if any(keyword in class_str for keyword in ['product', 'item', 'card', 'deal', 'tile']):
                    product_containers.add(parent)
                    break
                
                if parent.get('data-testid') or parent.get('data-product-id'):
                    product_containers.add(parent)
                    break
            
            parent = parent.parent if parent else None
    
    # Extract deals from containers
    for container in product_containers:
        deal = extract_deal_info(container)
        if deal:
            deals.append(deal)
    
    return deals

def print_deal(deal, index):
    """Print a single deal in a formatted way."""
    print(f"\n{'='*80}")
    print(f"#{index}. {deal['product_name']}")
    print('-'*80)
    
    # Deal type with emoji
    emoji_map = {'BOGO': '🎁', 'Discount': '💵', 'Price Drop': '📉', 'Deal': '🏷️'}
    emoji = emoji_map.get(deal['deal_type'], '🏷️')
    print(f"{emoji} Deal Type: {deal['deal_type']}")
    
    if deal.get('is_bogo'):
        print(f"🎁 BUY 1 GET 1 FREE!")
    
    if deal.get('current_price'):
        print(f"💰 Price: {deal['current_price']}")
    
    if deal.get('savings'):
        print(f"💵 Savings: {deal['savings']}")
    
    if deal.get('deal_description'):
        print(f"📋 Details: {deal['deal_description']}")

def main():
    """Main function with user input."""
    print("=" * 80)
    print("  PUBLIX WEEKLY AD DEAL FINDER")
    print("=" * 80)
    print()
    
    # Get user input
    search_item = input("🔍 Enter item to search for (e.g., 'frito lay', 'chicken'): ").strip()
    
    store_input = input("📍 Enter store number (e.g., '0865') or press Enter for all stores: ").strip()
    store_number = store_input if store_input else None
    
    if not search_item:
        print("❌ Error: Search item cannot be empty!")
        return
    
    print()
    print(f"🔍 Searching for: '{search_item}'")
    if store_number:
        print(f"📍 Store: #{store_number}")
    else:
        print(f"📍 Store: All stores (generic weekly ad)")
    print()
    
    # Build URL
    if store_number:
        url = f"https://www.publix.com/savings/weekly-ad/view-all?storeNumber={store_number}"
    else:
        url = "https://www.publix.com/savings/weekly-ad/view-all"
    
    # Set up browser
    print("🔧 Setting up browser...")
    driver = setup_driver(headless=True)
    
    try:
        # Load page
        print("🌐 Loading weekly ad page...")
        driver.get(url)
        
        # Wait and scroll
        print("⏳ Waiting for page to load...")
        time.sleep(5)
        
        print("📜 Scrolling to load all products...")
        scroll_page(driver)
        
        # Parse page
        print("🔍 Analyzing page...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Find all deals
        all_deals = find_deals(soup)
        print(f"✅ Found {len(all_deals)} total products")
        
        # Filter by search term
        search_lower = search_item.lower()
        matching_deals = [d for d in all_deals if search_lower in d['product_name'].lower()]
        
        print(f"✅ Found {len(matching_deals)} matching '{search_item}'")
        print()
        
        # Print results
        if not matching_deals:
            print("😞 No deals found for your search")
            print()
            print("💡 Tips:")
            print("   - Try broader search terms (e.g., 'lay' instead of 'frito lay party size')")
            print("   - Check if the item is actually on sale this week")
            print("   - Try a different store number")
        else:
            print(f"🎉 FOUND {len(matching_deals)} DEAL(S):")
            
            for i, deal in enumerate(matching_deals, 1):
                print_deal(deal, i)
            
            print("\n" + "="*80)
            
            # Summary
            bogo_count = sum(1 for d in matching_deals if d['is_bogo'])
            discount_count = sum(1 for d in matching_deals if d['deal_type'] == 'Discount')
            
            print(f"\n📊 Summary: {bogo_count} BOGO deals, {discount_count} Discounts")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        driver.quit()
        print("\n✅ Done!")

if __name__ == "__main__":
    main()


