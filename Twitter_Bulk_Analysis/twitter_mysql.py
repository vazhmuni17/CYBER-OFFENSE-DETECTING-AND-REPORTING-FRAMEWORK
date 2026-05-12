#!/usr/bin/python3
import tweepy
import json
import pymysql.cursors
import geocoder
import prediction_models
import torch
from BERT import BERT
import text_predict
from datetime import datetime, timezone
import time
import random

# ==========================================
# SET TO True to use dummy data instead of Twitter API
USE_DUMMY_DATA = True 
# ==========================================

# Credentials
# For API v2, Bearer Token is required
bearer_token = "AAAAAAAAAAAAAAAAAAAAAKz98AEAAAAAaOhGFBpse56oF4%2FlDgibrnlx4Cc%3DqbpW7PXHqIyOabD6I4nsIbcZAF5HoL0mlvNfZRiJhyexb5Gub0"
# API v1.1 credentials (kept for potential other uses, though not for v2 streaming)
ckey="abc123XYZrandomkey"
csecret="secretkeygoeshere123"
atoken="1234567890-accesstokenhere"
asecret="accesstokensecrethere"

connection = pymysql.connect(host='localhost',
                             port=3306,
                             user='root',
                             password='root',
                             db='tweet_monitoring',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

image_model = torch.load("models/model_nsfw.pt", map_location=torch.device('cpu'), weights_only=False)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')  
# text_model = BERT().to(device)  # Redundant: handled by text_predict.py

def load_checkpoint(load_path, model):
    if load_path==None:
        return
    state_dict = torch.load(load_path, map_location=device, weights_only=False)
    print(f'Model loaded from <== {load_path}')
    model.load_state_dict(state_dict['model_state_dict'])
    return state_dict['valid_loss']

# load_checkpoint('models/model_initial_text.pt', text_model) # Redundant: handled by text_predict.py

class listener(tweepy.StreamingClient):
    def on_data(self, raw_data):
        try:
            full_data = json.loads(raw_data)
            if 'data' not in full_data:
                return True
                
            tweet_data = full_data['data']
            includes = full_data.get('includes', {})
            users = includes.get('users', [])
            media = includes.get('media', [])
            
            # Simple check for retweets (v2 approach: 'referenced_tweets' contains 'retweeted')
            if any(ref.get('type') == 'retweeted' for ref in tweet_data.get('referenced_tweets', [])):
                return True

            tweet_type = "text"
            tweet_id = tweet_data.get('id')
            tweet_text = tweet_data.get('text')
            tweet_created = tweet_data.get('created_at')
            
            # Convert ISO 8601 to dt_object
            dt_object = datetime.fromisoformat(tweet_created.replace('Z', '+00:00'))
            
            # Get User Info
            user_data = users[0] if users else {}
            username = user_data.get('name', 'Unknown')
            profile_picture = user_data.get('profile_image_url', '')
            location = user_data.get('location', '')
            
            media_url = ''
            if media:
                tweet_type = "image"
                best_media = media[0]
                media_url = best_media.get('url') or best_media.get('preview_image_url') or ''
                if best_media.get('type') == 'video':
                    tweet_type = "video"

            hashtags = []
            if 'entities' in tweet_data and 'hashtags' in tweet_data['entities']:
                hashtags = [h['tag'] for h in tweet_data['entities']['hashtags']]

            latitude = ""
            longitude = ""
            if location and hasattr(geocoder, 'arcgis'):
                try:
                    result = geocoder.arcgis(location)
                    if result and result.x != None and result.y != None:
                        latitude = str(result.y)
                        longitude = str(result.x)
                except Exception as geo_e:
                    print(f"Geocoding Error: {geo_e}")
            else:
                location = ''

            # Toxicity Prediction
            post_content_prediction = text_predict.predict_string(tweet_text)
            text_toxicity = max(post_content_prediction)
            
            image_class = ''
            if tweet_type == "image" and media_url:
                image_class = prediction_models.predict_image(image_model, media_url)

            try:
                with connection.cursor() as cursor:
                    sql = "INSERT INTO `tweets` VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    cursor.execute(sql, (tweet_id, dt_object, tweet_created, username, profile_picture, tweet_type, tweet_text, media_url, location, latitude, longitude, text_toxicity, image_class))
                    for h_text in hashtags:
                        cursor.execute("INSERT INTO `hashtags` VALUES (%s)", (h_text,))
                    connection.commit()
            except Exception as e:
                print(f"Database Error: {e}")
                
            print(f"Post ID: {tweet_id} inserted!")
            
        except Exception as e:
            print(f"Error on_data: {e}")
        return True

    def on_error(self, status):
        print(f"Error status: {status}")

def simulate_tweets():
    print("DUMMY MODE ENABLED: Generating simulated tweets...")
    sc = listener(bearer_token)
    
    sample_texts = [
        "This is a wonderful day! I love coding. #coding #happy",
        "I hate this traffic so much, it's so annoying and stupid. #angry #traffic",
        "Just saw a beautiful sunset at the beach. #nature #beach",
        "The new update is terrible, the developers are idiots. #badupdate",
        "Incredible performance by the team today! #sports #win",
        "I'm going to hurt someone if they don't stop talking. #threat #annoyed",
        "You are absolutely disgusting and worthless. #hate #insult"
    ]
    
    cities = ["New York, USA", "London, UK", "Tokyo, Japan", "Mumbai, India", "Berlin, Germany"]
    
    while True:
        try:
            fake_id = str(random.randint(1000000000000000000, 9999999999999999999))
            fake_text = random.choice(sample_texts)
            fake_user = f"User_{random.randint(100, 999)}"
            fake_loc = random.choice(cities)
            fake_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # Extract hashtags
            fake_hashtags = [{"tag": part.strip("#")} for part in fake_text.split() if part.startswith("#")]
            
            dummy_json = {
                "data": {
                    "id": fake_id,
                    "text": fake_text,
                    "created_at": fake_time,
                    "entities": {"hashtags": fake_hashtags}
                },
                "includes": {
                    "users": [{
                        "name": fake_user,
                        "profile_image_url": "https://abs.twimg.com/sticky/default_profile_images/default_profile_normal.png",
                        "location": fake_loc
                    }]
                }
            }
            
            sc.on_data(json.dumps(dummy_json))
            time.sleep(random.randint(3, 8)) # Wait 3-8 seconds between tweets
            
        except KeyboardInterrupt:
            print("\nStopping simulation...")
            break
        except Exception as e:
            print(f"Simulation Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    if USE_DUMMY_DATA:
        simulate_tweets()
    else:
        # Initialize and run
        sc = listener(bearer_token)

        # Clear existing rules and add new one
        rules = sc.get_rules()
        if rules.data:
            sc.delete_rules([r.id for r in rules.data])
        sc.add_rules(tweepy.StreamRule("PrakashTestCODAR123"))

        print("Starting stream...")
        sc.filter(
            expansions=['author_id', 'attachments.media_keys', 'geo.place_id'],
            tweet_fields=['created_at', 'entities', 'referenced_tweets'],
            user_fields=['profile_image_url', 'location'],
            media_fields=['url', 'preview_image_url', 'type']
        )
