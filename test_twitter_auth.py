"""
Twitter API Authentication Diagnostic Script.
Tests each component of the OAuth 1.0a flow.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("TWITTER API DIAGNOSTIC")
print("=" * 60)

# 1. Check credentials are loaded
print("\n[1] CHECKING CREDENTIALS")
consumer_key = os.environ.get("TWITTER_API_KEY", "")
consumer_secret = os.environ.get("TWITTER_API_SECRET", "")
access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
access_secret = os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", "")

print(f"  Consumer Key: {consumer_key[:8]}...{consumer_key[-4:]} ({len(consumer_key)} chars)")
print(f"  Consumer Secret: {consumer_secret[:8]}...{consumer_secret[-4:]} ({len(consumer_secret)} chars)")
print(f"  Access Token: {access_token[:8]}...{access_token[-4:]} ({len(access_token)} chars)")
print(f"  Access Secret: {access_secret[:8]}...{access_secret[-4:]} ({len(access_secret)} chars)")

if not all([consumer_key, consumer_secret, access_token, access_secret]):
    print("\n  ERROR: Missing credentials!")
    sys.exit(1)

# 2. Check system time (OAuth is timestamp-sensitive)
print("\n[2] CHECKING SYSTEM TIME")
local_time = datetime.now()
print(f"  Local time: {local_time.isoformat()}")
try:
    import ntplib
    client = ntplib.NTPClient()
    response = client.request('pool.ntp.org', version=3)
    ntp_time = datetime.fromtimestamp(response.tx_time)
    drift = abs((local_time - ntp_time).total_seconds())
    print(f"  NTP time:   {ntp_time.isoformat()}")
    print(f"  Drift:      {drift:.1f} seconds")
    if drift > 60:
        print("  WARNING: System clock drift > 60s may cause OAuth failures!")
except Exception as e:
    print(f"  Could not check NTP time: {e}")
    print("  (Install ntplib with: pip install ntplib)")

# 3. Test authentication with tweepy
print("\n[3] TESTING TWEEPY CLIENT")
try:
    import tweepy
    print(f"  Tweepy version: {tweepy.__version__}")

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )
    print("  Client created successfully")
except Exception as e:
    print(f"  ERROR creating client: {e}")
    sys.exit(1)

# 4. Test read-only endpoint first (get_me)
print("\n[4] TESTING READ-ONLY ENDPOINT (get_me)")
try:
    me = client.get_me(user_fields=["id", "username", "name"])
    if me.data:
        print(f"  SUCCESS! Authenticated as:")
        print(f"    ID:       {me.data.id}")
        print(f"    Username: @{me.data.username}")
        print(f"    Name:     {me.data.name}")
    else:
        print("  WARNING: get_me returned no data")
except tweepy.Unauthorized as e:
    print(f"  401 UNAUTHORIZED on get_me!")
    print(f"  This means credentials are INVALID.")
    print(f"  Full error: {e}")
    print("\n  DIAGNOSIS: Consumer Key or Access Token are wrong/expired.")
    print("  ACTION: Regenerate ALL credentials in Developer Portal.")
    sys.exit(1)
except tweepy.Forbidden as e:
    print(f"  403 FORBIDDEN: {e}")
    print("  Your access level may not include this endpoint.")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")

# 5. Test write endpoint (create_tweet)
print("\n[5] TESTING WRITE ENDPOINT (create_tweet)")
print("  Attempting to post a test tweet...")
try:
    # Use unique timestamp to avoid duplicate tweet detection
    test_text = f"API test {datetime.now().strftime('%Y%m%d_%H%M%S')} - please delete"
    response = client.create_tweet(text=test_text)

    if response.data:
        tweet_id = response.data["id"]
        print(f"  SUCCESS! Tweet posted!")
        print(f"    Tweet ID: {tweet_id}")
        print(f"    URL: https://x.com/i/status/{tweet_id}")
        print("\n  Deleting test tweet...")
        try:
            client.delete_tweet(tweet_id)
            print("  Test tweet deleted.")
        except Exception as de:
            print(f"  Could not delete: {de}")
            print(f"  Please delete manually: https://x.com/i/status/{tweet_id}")
    else:
        print("  WARNING: create_tweet returned no data")

except tweepy.Unauthorized as e:
    print(f"  401 UNAUTHORIZED on create_tweet!")
    print(f"  Full error: {e}")
    print(f"  Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
    print("\n  DIAGNOSIS OPTIONS:")
    print("    1. App permissions are Read-Only (need Read+Write)")
    print("    2. Access Token was generated BEFORE permissions were changed")
    print("    3. App is not linked to a Project in Developer Portal")
    print("\n  ACTION:")
    print("    1. Go to Developer Portal > Your App > Settings")
    print("    2. Check User Authentication Settings > App Permissions")
    print("    3. Ensure it says 'Read and Write'")
    print("    4. Go to Keys and Tokens tab")
    print("    5. Regenerate Access Token AND Secret")
    print("    6. Update .env with new values")

except tweepy.Forbidden as e:
    print(f"  403 FORBIDDEN: {e}")
    print(f"  Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
    print("\n  DIAGNOSIS: Access level doesn't support posting.")
    print("  Free tier SHOULD support posting - check your app setup.")

except tweepy.TooManyRequests as e:
    print(f"  429 RATE LIMITED: {e}")

except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    if hasattr(e, 'response'):
        print(f"  Response: {e.response.text}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
