import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
FIREBASE_SERVER_KEY = os.getenv("FIREBASE_SERVER_KEY")
FCM_URL = "https://fcm.googleapis.com/fcm/send"

def send_otd_notification(title, date, otd_id, topic="otd_updates"):
    """Send a simple On This Day notification to a topic"""
    if not FIREBASE_SERVER_KEY:
        print("Firebase server key not configured")
        return
        
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"key={FIREBASE_SERVER_KEY}"
    }
    
    # Send to topic (all users who subscribed)
    payload = {
        "to": f"/topics/{topic}",
        "notification": {
            "title": "New On This Day Event",
            "body": f"{title} - {date.strftime('%B %d')}",
            "sound": "default"
        },
        "data": {
            "otd_id": str(otd_id),
            "type": "on_this_day"
        }
    }
    
    try:
        response = requests.post(FCM_URL, headers=headers, data=json.dumps(payload))
        return response.json()
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")
        return None 