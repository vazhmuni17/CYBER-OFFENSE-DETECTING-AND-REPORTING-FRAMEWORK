#!/usr/bin/python3
import whatsapp, twitter, facebook as fb, viraly, sms
from database import Connection
from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, url_for, request, session, make_response, flash
import hashlib
import json
import tweepy
import re
import csv
import os
import prediction_models
import torch
from BERT import BERT

from datetime import datetime
import text_predict

app = Flask(__name__)
app.secret_key='somerandomvalue'
app.config['UPLOAD_FOLDER'] = 'user-content/'
auth = tweepy.OAuthHandler("YOUR_CONSUMER_KEY","YOUR_CONSUMER_SECRET")
auth.set_access_token("YOUR_ACCESS_TOKEN","YOUR_ACCESS_SECRET")

twapi = tweepy.API(auth,wait_on_rate_limit=True)
db = Connection(app, 'localhost', 27017) 
quick_launch = True

#Importing all models for text and image classification

image_model = None
try:
    import torch
    image_model = torch.load(os.path.join(BASE_DIR, "models", "model_nsfw.pt"), map_location=torch.device('cpu'), weights_only=False)
except Exception as e:
    print(f"Warning: Could not load image model. Reason: {e}")
if quick_launch == False:
    # Importing all models for text and image classification
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')  
    text_model = BERT().to(device)

def load_checkpoint(load_path, model):
    if load_path==None:
        return
    state_dict = torch.load(load_path, map_location=device)
    print(f'Model loaded from <== {load_path}')
    model.load_state_dict(state_dict['model_state_dict'])
    return state_dict['valid_loss']


if quick_launch == False:
    load_checkpoint('models/model_initial_text.pt', text_model)

# Push to Database Functions
def db_push_commons(username, email, full_name, date_of_birth, address, 
                state, city, pincode, crime_type, platform, link ,post_content):
    """ Push Common Data for all platforms database
    """
    from random import randint
    complaint = {
        'id': str(randint(10000, 99999)),
        'timestamp': datetime.now(),
        'victimName':username,
        'harasserName': "kk",
        'victimEmail':email,
        'victimFullName':full_name,
        'victimDob':date_of_birth,
        'victimAddress':address,
        'victimState':state,
        'victimCity':city,
        'victimPincode':pincode,
        'reason':crime_type,
        'type':platform,
        'link': link,
        'status':'pending',
        'hscore':'0.5',
        'post_content':post_content
    }
    print(complaint)
    db.create_complaint(complaint)


# 404: Page not found handler
@app.errorhandler(404)
def not_found(e):
    return render_template("errorpages/404.html")

def get_classification(platform,post_content):
    if(platform=="twitter"):
        # post_content_prediction = text_predict.predict_string(post_content['post_text'])
        post_content_prediction = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        image_prediction = [0,0,0,0,0]
        if(post_content['tweet_type']=="image"):
            image_prediction = prediction_models.predict_image(image_model,post_content['post_media'])
        post_content['text_toxicity'] = post_content_prediction
        post_content['image_prediction'] = image_prediction

    if(platform=="viraly"):
        post_content_prediction = text_predict.predict_string(post_content['post_text'])
        image_prediction = [0,0,0,0,0]
        if(post_content['post_type']=="media"):
            image_prediction = prediction_models.predict_image(image_model,post_content['post_media'])
        post_content['text_toxicity'] = post_content_prediction
        post_content['image_prediction'] = image_prediction

    if(platform=="whatsapp"):
        text_toxicity = prediction_models.predict_chat_toxicity(text_model,post_content['uploaded_chat'],device)
        post_content['text_toxicity'] = text_toxicity

    if(platform=="facebook"):
        post_content_prediction = text_predict.predict_string(post_content['post_text'])
        image_prediction = [0,0,0,0,0]
        if(post_content['post_type']=="image"):
            print('hello')
            image_prediction = prediction_models.predict_image(image_model,post_content['post_media'])
        post_content['text_toxicity'] = post_content_prediction
        post_content['image_prediction'] = image_prediction


    return post_content


@app.route('/push', methods=['POST']) 
def form_entry():
    if request.method == 'POST':
        platform = request.form['platform']

        # Form data retrieval from POST
        username        = request.form['username']
        email           = request.form['email']
        full_name       = request.form['full_name']
        date_of_birth   = request.form['dob']
        address         = request.form['address']
        state           = request.form['state']
        city            = request.form['city']
        pincode         = request.form['pincode']
        crime_type      = request.form['crime_type']    # Common in specific cards

        if(platform=="twitter"):    
            link = request.form['tweet_link']
            post_content = twitter.get_data_twitter(request.form['tweet_link'], twapi)
            post_content = get_classification(platform,post_content)
        elif(platform=="facebook"): 
            link = request.form['fb_link']
            encoded_link =  request.form['post_encoded_url']
            post_content = fb.get_data_facebook(encoded_link,link)
            post_content = get_classification(platform,post_content)
            
            # Real-time Blurring for FB Clone
            if "localhost:3005" in link or "127.0.0.1:3005" in link:
                import pymongo
                from urllib.parse import urlparse, parse_qs
                post_id = parse_qs(urlparse(link).query).get('id')
                if post_id:
                    client = pymongo.MongoClient('localhost', 27017)
                    if post_content.get('image_prediction', [0])[3] > 1 or post_content.get('text_toxicity', [0])[0] > 0.5: # Example threshold
                        client['chat-app'].posts.update_one({'id': int(post_id[0])}, {'$set': {'is_blurred': True}})
        elif(platform=="viraly"):   
            link = request.form['viraly_post_id']
            post_content = viraly.get_data_viraly(db,request.form['viraly_content-type'],request.form['viraly_post_id'])
            post_content = get_classification(platform,post_content)
        elif(platform=="whatsapp"): 
            link = "http://localhost:3003/static/user-content/"+username+"/"+request.files['whatsapp_backup'].filename
            post_content = whatsapp.get_data_whatsapp(username,request.files['whatsapp_backup'],app.config['UPLOAD_FOLDER'])
            post_content = get_classification(platform,post_content)
        elif(platform == "youtube"):    
            yt_link = request.form['youtube_link']
            from youtube import Youtube
            yt = Youtube()
            temp = yt.auto_yt(yt_link, image_model, pretty=True)
            
            # Real-time Blurring for YT Clone
            if "localhost:3006" in yt_link or "127.0.0.1:3006" in yt_link:
                import pymongo
                from urllib.parse import urlparse
                post_id = urlparse(yt_link).path.split("/")[-1]
                if post_id.isdigit():
                    client = pymongo.MongoClient('localhost', 27017)
                    # For youtube, auto_yt returns temp list like [['Pornography', 10, '100%']]
                    is_offensive = any(cls[0] in ['Pornography', 'Hentai', 'Sexually Provocative'] for cls in temp)
                    if is_offensive:
                        client['chat-app'].posts.update_one({'id': int(post_id)}, {'$set': {'is_blurred': True}})
            
            # Push YouTube report to DB
            db_push_commons(username, email, full_name, date_of_birth,
                address, state, city, pincode, crime_type, platform, yt_link, {"classification": temp})
            return render_template("video-result.html", temp=temp, yt_link=yt_link)

        elif(platform == "sms"):    
            post_content = sms.get_data_sms(request.form['sender_number'])
        else:                       
            return redirect(url_for('index_main'))
        db_push_commons(username, email, full_name, date_of_birth,
            address, state, city, pincode, crime_type,platform,link,post_content)
        return redirect(url_for('index_main'))
    else:
        return redirect(url_for('index_main'))


@app.route('/', methods=['GET'])
def index_main():
    if request.method == 'GET': 
        platform = request.args.get('platform')
        print(platform)
        # Render the right template
        if platform==None or platform=="twitter":   return render_template("twitter.html", platform="twitter")
        elif platform=="sms":                       return render_template("phone-message.html", platform=platform)
        elif platform=="viraly":                    return render_template("viraly.html", platform=platform)
        elif platform=="facebook":                  return render_template("facebook.html", platform=platform)
        elif platform=="whatsapp":                  return render_template("whatsapp.html", platform=platform)
        elif platform=="youtube":                   return render_template("youtube.html", platform=platform)
        else:                                       return render_template("under-construction.html", platform=platform)
    else:
        return render_template("twitter.html", platform="twitter")

@app.route('/dashboard')
def dashboard():
    all_complaints = list(db.complaints.find().sort('timestamp', -1))
    stats = {
        'total': db.complaints.count_documents({}),
        'facebook': db.complaints.count_documents({'type': 'facebook'}),
        'youtube': db.complaints.count_documents({'type': 'youtube'}),
        'viraly': db.complaints.count_documents({'type': 'viraly'}),
        'blurred': db.posts.count_documents({'is_blurred': True})
    }
    return render_template("dashboard.html", complaints=all_complaints, stats=stats)

@app.route('/api/stats')
def api_stats():
    stats = {
        'total': db.complaints.count_documents({}),
        'facebook': db.complaints.count_documents({'type': 'facebook'}),
        'youtube': db.complaints.count_documents({'type': 'youtube'}),
        'viraly': db.complaints.count_documents({'type': 'viraly'}),
        'blurred': db.posts.count_documents({'is_blurred': True})
    }
    return json.dumps(stats)

if __name__ == '__main__':
     app.run(host='0.0.0.0', port=3003, use_reloader=True, debug=True)
