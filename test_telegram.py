#!/usr/bin/env python3
"""Test Telegram integration endpoints."""

import requests
import sys

BASE_URL = "http://localhost:3101"

# Test credentials - you'll need to replace these
TEST_USER = {
    "username": "testuser",
    "password": "testpass123"
}

# Telegram bot credentials - replace with your actual bot token and chat ID
TELEGRAM_CONFIG = {
    "bot_token": "YOUR_BOT_TOKEN",  # Get from @BotFather
    "chat_id": "YOUR_CHAT_ID"  # Your chat/channel ID
}

def main():
    session = requests.Session()

    # 1. Register/login user
    print("1. Creating test user...")
    response = session.post(f"{BASE_URL}/auth/register", json=TEST_USER)
    if response.status_code == 201:
        print("   ✓ User created")
    elif response.status_code == 400:
        # User exists, login instead
        print("   User exists, logging in...")
        response = session.post(f"{BASE_URL}/auth/login", json=TEST_USER)
        if response.status_code == 200:
            print("   ✓ Logged in")
        else:
            print(f"   ✗ Login failed: {response.json()}")
            return 1
    else:
        print(f"   ✗ Failed: {response.json()}")
        return 1

    # 2. Create a test space
    print("\n2. Creating test space...")
    space_data = {
        "title": "Telegram Test Space",
        "slug": "telegram-test"
    }
    response = session.post(f"{BASE_URL}/spaces", json=space_data)
    if response.status_code == 201:
        print("   ✓ Space created")
    elif response.status_code == 400 and "already exists" in response.json().get("detail", ""):
        print("   Space already exists, continuing...")
    else:
        print(f"   ✗ Failed: {response.json()}")
        return 1

    # 3. Create Telegram integration
    print("\n3. Creating Telegram integration...")
    response = session.post(
        f"{BASE_URL}/spaces/telegram-test/telegram",
        json=TELEGRAM_CONFIG
    )
    if response.status_code == 201:
        print("   ✓ Integration created")
        print(f"   Bot token: {response.json()['bot_token'][:20]}...")
        print(f"   Chat ID: {response.json()['chat_id']}")
    elif response.status_code == 400 and "already exists" in response.json().get("detail", ""):
        print("   Integration already exists, continuing...")
    else:
        print(f"   ✗ Failed: {response.json()}")
        return 1

    # 4. Test sending message
    print("\n4. Testing Telegram message send...")
    response = session.post(f"{BASE_URL}/spaces/telegram-test/telegram/test")
    if response.status_code == 200:
        result = response.json()
        if result["success"]:
            print("   ✓ Test message sent successfully!")
            print(f"   Message: {result['message']}")
        else:
            print(f"   ✗ Failed to send: {result['message']}")
    else:
        print(f"   ✗ Request failed: {response.json()}")
        return 1

    # 5. Check integration status
    print("\n5. Checking integration status...")
    response = session.get(f"{BASE_URL}/spaces/telegram-test/telegram")
    if response.status_code == 200:
        integration = response.json()
        if integration:
            print(f"   ✓ Integration active")
            print(f"   Enabled: {integration['is_enabled']}")
            print(f"   Events configured: {len(integration.get('notifications', {}))}")
        else:
            print("   No integration found")
    else:
        print(f"   ✗ Failed: {response.json()}")

    print("\n✅ All tests completed!")
    return 0

if __name__ == "__main__":
    if TELEGRAM_CONFIG["bot_token"] == "YOUR_BOT_TOKEN":
        print("⚠️  Please edit this file and set your actual Telegram bot token and chat ID")
        print("   Get bot token from @BotFather on Telegram")
        print("   Get chat ID by sending a message to your bot and checking:")
        print("   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates")
        sys.exit(1)

    sys.exit(main())