#!/usr/bin/env python3
"""
App Store Chart Monitor with Polymarket Integration
Monitors the App Store iPhone charts and sends Telegram notifications when ChatGPT is not #1.
Also tracks Polymarket prices when ChatGPT drops from #1.
Sends heartbeat notifications every 30 minutes to confirm the script is running.
"""

import httpx
from bs4 import BeautifulSoup
import time
from datetime import datetime
import sys

# ========================================
# CONFIGURATION - Update these variables
# ========================================
TELEGRAM_BOT_TOKEN = "8447496257:AAHfIFG2B0eCfQPHiXFDXCCSMIDAqiVMnkY"
TELEGRAM_CHAT_ID = "7652991016"

# URLs and settings
APP_STORE_URL = "https://apps.apple.com/us/iphone/charts"
POLYMARKET_MARKET_SLUG = "will-bitcoin-reach-100k-by-2025"
CHECK_INTERVAL = 1  # Check every 2 seconds (in seconds)
HEARTBEAT_INTERVAL = 1800  # Send heartbeat every 30 minutes (in seconds)
PRICE_CHECK_DELAY = 10  # Wait 10 seconds between price checks

# Global variable for selected token
SELECTED_TOKEN_ID = None
SELECTED_TOKEN_NAME = None

# ========================================
# Functions
# ========================================

def send_telegram_message(message):
    """Send a message via Telegram bot"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload)
            if response.status_code == 200:
                print(f"✓ Telegram message sent: {message[:50]}...")
                return True
            else:
                print(f"✗ Failed to send Telegram message: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
    except Exception as e:
        print(f"✗ Error sending Telegram message: {e}")
        return False


def get_polymarket_tokens():
    """Fetch Polymarket market data and return token IDs"""
    try:
        print(f"\nFetching Polymarket market: {POLYMARKET_MARKET_SLUG}")
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                f"https://gamma-api.polymarket.com/markets?slug={POLYMARKET_MARKET_SLUG}"
            )
            response.raise_for_status()
            market_data = response.json()
            
            if not market_data or len(market_data) == 0:
                print("✗ No market data found")
                return None
            
            # Get the first market
            market = market_data[0]
            token_ids = market.get('clobTokenIds', [])
            outcomes = market.get('outcomes', [])
            
            if len(token_ids) != 2:
                print(f"✗ Expected 2 tokens, found {len(token_ids)}")
                return None
            
            print(f"✓ Found market: {market.get('question', 'Unknown')}")
            return {
                'token_ids': token_ids,
                'outcomes': outcomes,
                'question': market.get('question', 'Unknown')
            }
            
    except Exception as e:
        print(f"✗ Error fetching Polymarket data: {e}")
        return None


def get_token_price(token_id):
    """Get the current price for a specific token"""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://clob.polymarket.com/price",
                params={
                    "token_id": token_id,
                    "side": "BUY"
                }
            )
            response.raise_for_status()
            price_data = response.json()
            price = float(price_data.get("price", 0))
            return price
    except Exception as e:
        print(f"✗ Error fetching price for token {token_id}: {e}")
        return None


def setup_polymarket_tracking():
    """Let user choose which token to track"""
    global SELECTED_TOKEN_ID, SELECTED_TOKEN_NAME
    
    print("\n" + "=" * 60)
    print("POLYMARKET SETUP")
    print("=" * 60)
    
    tokens_data = get_polymarket_tokens()
    if not tokens_data:
        print("⚠️ Could not fetch Polymarket data. Continuing without price tracking.")
        return False
    
    print(f"\nMarket Question: {tokens_data['question']}")
    print("\nAvailable outcomes:")
    
    for i, (token_id, outcome) in enumerate(zip(tokens_data['token_ids'], tokens_data['outcomes'])):
        price = get_token_price(token_id)
        price_display = f"${price:.4f}" if price else "N/A"
        print(f"  {i+1}. {outcome} - Current Price: {price_display}")
        print(f"     Token ID: {token_id}")
    
    while True:
        try:
            choice = input("\nWhich outcome do you want to track? (1 or 2): ").strip()
            choice_idx = int(choice) - 1
            
            if choice_idx in [0, 1]:
                SELECTED_TOKEN_ID = tokens_data['token_ids'][choice_idx]
                SELECTED_TOKEN_NAME = tokens_data['outcomes'][choice_idx]
                print(f"\n✓ Tracking: {SELECTED_TOKEN_NAME}")
                print(f"  Token ID: {SELECTED_TOKEN_ID}")
                return True
            else:
                print("Invalid choice. Please enter 1 or 2.")
        except (ValueError, KeyboardInterrupt):
            print("\nInvalid input. Please enter 1 or 2.")


def track_price_change():
    """Track price change when ChatGPT is not #1"""
    if not SELECTED_TOKEN_ID:
        return
    
    try:
        # Get initial price
        print(f"\n📊 Getting initial price for {SELECTED_TOKEN_NAME}...")
        price1 = get_token_price(SELECTED_TOKEN_ID)
        
        if price1 is None:
            print("✗ Could not fetch initial price")
            return
        
        print(f"   Initial price: ${price1:.4f}")
        
        # Wait 10 seconds
        print(f"   Waiting {PRICE_CHECK_DELAY} seconds...")
        time.sleep(PRICE_CHECK_DELAY)
        
        # Get second price
        print(f"📊 Getting second price for {SELECTED_TOKEN_NAME}...")
        price2 = get_token_price(SELECTED_TOKEN_ID)
        
        if price2 is None:
            print("✗ Could not fetch second price")
            return
        
        print(f"   Second price: ${price2:.4f}")
        
        # Calculate change
        price_diff = price2 - price1
        price_diff_percent = (price_diff / price1 * 100) if price1 != 0 else 0
        
        # Determine direction emoji
        if price_diff > 0:
            direction = "📈"
        elif price_diff < 0:
            direction = "📉"
        else:
            direction = "➡️"
        
        # Send message
        message = (
            f"{direction} <b>Polymarket Price Update</b>\n\n"
            f"Market: {SELECTED_TOKEN_NAME}\n"
            f"Price 1: ${price1:.4f}\n"
            f"Price 2: ${price2:.4f}\n"
            f"Change: ${price_diff:+.4f} ({price_diff_percent:+.2f}%)\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        send_telegram_message(message)
        print(f"✓ Price changed by ${price_diff:+.4f} ({price_diff_percent:+.2f}%)")
        
    except Exception as e:
        print(f"✗ Error tracking price change: {e}")


def fetch_top_app():
    """Fetch the #1 app from the App Store charts"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"Fetching App Store charts from: {APP_STORE_URL}")
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(APP_STORE_URL, headers=headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find the #1 app (this may need adjustment based on Apple's HTML structure)
            # Looking for common patterns in App Store pages
            
            # Method 1: Look for the first app link
            app_links = soup.find_all('a', href=True)
            for link in app_links:
                href = link.get('href', '')
                if '/app/' in href and 'id' in href:
                    app_name = link.get_text(strip=True)
                    if app_name and len(app_name) > 0:
                        print(f"Found #1 app: {app_name}")
                        return app_name
            
            # Method 2: Try to find by common class patterns
            # Note: Apple's structure changes frequently, so this might need updates
            print("Could not determine #1 app from page structure")
            return None
        
    except httpx.HTTPError as e:
        print(f"✗ Error fetching App Store page: {e}")
        return None
    except Exception as e:
        print(f"✗ Unexpected error parsing page: {e}")
        return None


def check_chatgpt_ranking():
    """Check if ChatGPT is #1 and send notification if not"""
    top_app = fetch_top_app()
    
    if top_app is None:
        message = f"⚠️ <b>Monitor Warning</b>\n\nCould not fetch App Store charts.\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(message)
        return False
    
    # Check if ChatGPT is #1 (case-insensitive check)
    is_chatgpt_number_one = "chatgpt" in top_app.lower()
    
    if not is_chatgpt_number_one:
        message = f"🚨 <b>Alert: ChatGPT is NOT #1!</b>\n\n#1 App: {top_app}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(message)
        print(f"⚠️ ChatGPT is not #1. Current #1: {top_app}")
        
        # Track price change
        if SELECTED_TOKEN_ID:
            print("\n💰 Tracking Polymarket price change...")
            track_price_change()
        
        return False
    else:
        print(f"✓ ChatGPT is #1")
        return True


def send_heartbeat():
    """Send a heartbeat notification to confirm the script is running"""
    uptime_hours = (time.time() - start_time) / 3600
    message = f"💚 <b>Monitor Heartbeat</b>\n\nScript is running normally.\nUptime: {uptime_hours:.1f} hours\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(message)


def main():
    """Main monitoring loop"""
    global start_time
    start_time = time.time()
    
    print("=" * 60)
    print("App Store Chart Monitor with Polymarket Integration")
    print("=" * 60)
    print(f"Monitoring URL: {APP_STORE_URL}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print(f"Heartbeat interval: {HEARTBEAT_INTERVAL} seconds")
    print("=" * 60)
    
    # Validate configuration
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or TELEGRAM_CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("\n⚠️ ERROR: Please configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        print("Edit the script and update these variables at the top.\n")
        sys.exit(1)
    
    # Setup Polymarket tracking
    setup_polymarket_tracking()
    
    # Send startup notification
    startup_msg = f"🚀 <b>Monitor Started</b>\n\nApp Store chart monitoring is now active."
    if SELECTED_TOKEN_ID:
        startup_msg += f"\n\nPolymarket Tracking: {SELECTED_TOKEN_NAME}"
    startup_msg += f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    send_telegram_message(startup_msg)
    
    last_heartbeat = time.time()
    
    try:
        while True:
            # Check ChatGPT ranking
            check_chatgpt_ranking()
            
            # Send heartbeat if interval has passed
            if time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
                send_heartbeat()
                last_heartbeat = time.time()
            
            # Wait before next check
            print(f"\nWaiting {CHECK_INTERVAL} seconds until next check...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Monitor stopped by user")
        print("=" * 60)
        uptime_hours = (time.time() - start_time) / 3600
        shutdown_message = f"🛑 <b>Monitor Stopped</b>\n\nScript was manually stopped.\nTotal uptime: {uptime_hours:.1f} hours"
        send_telegram_message(shutdown_message)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        error_message = f"💥 <b>Monitor Crashed</b>\n\nError: {str(e)}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(error_message)
        raise


if __name__ == "__main__":
    main()