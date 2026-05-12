#!/usr/bin/python3
from flask import Flask, render_template, url_for, request, session, redirect, jsonify
import json
from bson import ObjectId
from database import Connection
from flask_pymongo import PyMongo   
from flask_cors import CORS
import pymongo
from urllib.parse import urlparse, parse_qs
app = Flask(__name__,) 
app.config["MONGO_URI"] = "mongodb://localhost:27017/reportingapp"
mongo = PyMongo(app)
CORS(app)
db = mongo.db

@app.route('/whatsapp-table',methods=["GET","POST"])
def getWhatsapp():
    wapObj = []
    for i in db.complaints.find({"type":"whatsapp"}):
        wapObj.append({
            "id": i.get("id", "N/A"),
            "timestamp": i["timestamp"],
            "victimName": i["victimName"],
            "harasserName": i['harasserName'],
            "victimDob": i['victimDob'],
            "link": i['link'],
            "type": i['type'],
            "reason": i["reason"],
            "status": i["status"],
            "hscore": i["hscore"]
        })
    #return jsonify(wapObj)
    return render_template("whatsapp-table.html", data = wapObj)
    #return render_template("whatsapp-table.html")


@app.route('/fb-table', methods=["GET", "POST"])
def getFb():
    fbobj = []
    for i in db.complaints.find({"type":"facebook"}):
        fbobj.append({
            "id": i["id"],
            "timestamp": i["timestamp"],
            "victimName": i["victimName"],
            "harasserName": i['harasserName'],
            "victimDob": i['victimDob'],
            "link": i['link'],
            "type": i['type'],
            "reason": i["reason"],
            "status": i["status"],
            "hscore": i["hscore"]
        })
    #return jsonify(fbobj)   
    return render_template("fb-table.html", data = fbobj) 


@app.route('/login', methods=["GET", "POST"])
def login():
    return render_template("login.html")


@app.route('/viralry-table', methods=["GET", "POST"])
def getViraly():
    viralyObj = []
    for i in db.complaints.find({"type":"viraly"}):
        viralyObj.append({
            "id": i["id"],
            "victimName": i["victimName"],
            "harasserName": i['harasserName'],
            "victimDob": i['victimDob'],
            "link": i['link'],
            "type": i['type'],
            "reason": i["reason"],
            "status": i["status"],
            "hscore": i["hscore"]
        })
    #return jsonify(viralyObj)
    return render_template("viralry-table.html",data = viralyObj)


@app.route('/sms-table', methods=["GET", "POST"])
def getSms():
    smsObj = []
    for i in db.complaints.find({"type":"sms"}):
        smsObj.append({
            "id": i["id"],
            "victimName": i["victimName"],
            "harasserName": i['harasserName'],
            "victimDob": i['victimDob'],
            "link": i['link'],
            "type": i['type'],
            "reason": i["reason"],
            "status": i["status"],
            "hscore": i["hscore"]
        })
    return render_template("sms-table.html",data = smsObj)

@app.route('/youtube-table', methods=["GET", "POST"])
def getYoutube():
    ytObj = []
    for i in db.complaints.find({"type":"youtube"}):
        ytObj.append({
            "id": i["id"],
            "timestamp": i["timestamp"],
            "victimName": i["victimName"],
            "harasserName": i['harasserName'],
            "victimDob": i['victimDob'],
            "link": i['link'],
            "type": i['type'],
            "reason": i["reason"],
            "status": i["status"],
            "hscore": i["hscore"]
        })
    return render_template("youtube-table.html", data = ytObj)


@app.route('/twitter-table', methods=["GET", "POST"])
def getTwitter():
    twitterobj = []
    for i in db.complaints.find({"type":"twitter"}):
        twitterobj.append({
            "id": i.get("id", "N/A"),
            "timestamp": i["timestamp"],
            "victimName": i["victimName"],
            "harasserName": i['harasserName'],
            "victimDob": i['victimDob'],
            "link": i['link'],
            "type": i['type'],
            "reason": i["reason"],
            "status": i["status"],
            "hscore": i["hscore"]
        })
    return render_template("twitter-table.html", data = twitterobj)


@app.route('/index', methods=["GET", "POST"])
@app.route('/',methods=["GET","POST"])
def getIndex():
    total_complaints = db.complaints.count_documents({})
    positive_cases = db.complaints.count_documents({"status": "blocked"})
    dismissed_cases = db.complaints.count_documents({"status": "dismissed"})
    
    progress = 0
    if total_complaints > 0:
        progress = int(((positive_cases + dismissed_cases) / total_complaints) * 100)
    
    # Platform counts for chart
    platforms = ["facebook", "whatsapp", "twitter", "youtube", "viraly", "sms"]
    platform_labels = ["Facebook", "WhatsApp", "Twitter", "YouTube", "Viralry", "SMS/MMS"]
    platform_counts = []
    for p in platforms:
        platform_counts.append(db.complaints.count_documents({"type": p}))
    
    recent_complaints = []
    for i in db.complaints.find().sort("timestamp", -1).limit(6):
        text = "No content"
        if "post_content" in i and isinstance(i["post_content"], dict):
            text = i["post_content"].get("post_text", i["reason"])
        
        recent_complaints.append({
            "victimName": i.get("victimName", "Anonymous"),
            "text": text,
            "timestamp": i.get("timestamp", "N/A")
        })

    stats = {
        "total": total_complaints,
        "positive": positive_cases,
        "progress": progress,
        "misclassified": db.complaints.count_documents({"hscore": {"$lt": "0.1"}}), # Example logic
        "platform_counts": platform_counts,
        "recent": recent_complaints
    }

    return render_template("index.html", stats=stats)

@app.route('/block-complaint/<id>')
def block_complaint(id):
    # Update complaint status
    db.complaints.update_one({"id": id}, {"$set": {"status": "blocked"}})
    
    # Also find the complaint to get the post link and blur it in the social media DB
    complaint = db.complaints.find_one({"id": id})
    if complaint and 'link' in complaint:
        link = complaint['link']
        
        # Connect to social media DB
        client = pymongo.MongoClient('localhost', 27017)
        post_db = client['chat-app']
        
        # Try to extract ID from link (Facebook, YouTube, Viraly)
        if "id=" in link: # Facebook or generic
            post_id_list = parse_qs(urlparse(link).query).get('id')
            if post_id_list:
                try:
                    p_id = int(post_id_list[0])
                    post_db.posts.update_one({'id': p_id}, {'$set': {'is_blurred': True}})
                except:
                    post_db.posts.update_one({'id': post_id_list[0]}, {'$set': {'is_blurred': True}})
        elif "/watch/" in link: # YouTube
            video_id = link.split("/watch/")[-1].split("?")[0]
            try:
                post_db.posts.update_one({'id': int(video_id)}, {'$set': {'is_blurred': True}})
            except:
                 post_db.posts.update_one({'id': video_id}, {'$set': {'is_blurred': True}})
        else:
            # Try Viraly style or direct ID match
            try:
                post_db.posts.update_one({'id': int(link)}, {'$set': {'is_blurred': True}})
            except:
                post_db.posts.update_one({'id': link}, {'$set': {'is_blurred': True}})
                
    return redirect(request.referrer or url_for('getIndex'))

@app.route('/dismiss-complaint/<id>')
def dismiss_complaint(id):
    # Update complaint status
    db.complaints.update_one({"id": id}, {"$set": {"status": "dismissed"}})
    
    # Also find the complaint and un-blur the post in social media DB
    complaint = db.complaints.find_one({"id": id})
    if complaint and 'link' in complaint:
        link = complaint['link']
        client = pymongo.MongoClient('localhost', 27017)
        post_db = client['chat-app']
        
        if "id=" in link:
            post_id_list = parse_qs(urlparse(link).query).get('id')
            if post_id_list:
                try:
                    p_id = int(post_id_list[0])
                    post_db.posts.update_one({'id': p_id}, {'$set': {'is_blurred': False}})
                except:
                    post_db.posts.update_one({'id': post_id_list[0]}, {'$set': {'is_blurred': False}})
        elif "/watch/" in link:
            video_id = link.split("/watch/")[-1].split("?")[0]
            try:
                post_db.posts.update_one({'id': int(video_id)}, {'$set': {'is_blurred': False}})
            except:
                 post_db.posts.update_one({'id': video_id}, {'$set': {'is_blurred': False}})
        else:
            try:
                post_db.posts.update_one({'id': int(link)}, {'$set': {'is_blurred': False}})
            except:
                post_db.posts.update_one({'id': link}, {'$set': {'is_blurred': False}})

    return redirect(request.referrer or url_for('getIndex'))

@app.route('/facebookReport', methods=["GET","POST"])
def preview():
    fbReport = []
    for i in db.complaints.find({"id": str(request.args.get('id'))}):
        fbReport.append({
            "victimFullName": i["victimFullName"],
            "victimName" : i["victimName"],
            "link" : i["link"],
            "harasserName" : i["harasserName"],
            "type": i["type"],
            "victimDob": i["victimDob"],
            "text": i["post_content"]["post_text"],
            "timestamp": i["timestamp"],
            "victimAddress": i["victimAddress"],
            "victimState": i["victimState"],
            "victimCity": i["victimCity"],
            "victimPincode": i["victimPincode"],
            "reason": i["reason"],
            "status": i["status"],
            "hscore":i["hscore"],
            "post_type": i["post_content"]["post_type"], 
            "text_toxicity": i["post_content"]["text_toxicity"],
            "image_prediction": i["post_content"]["image_prediction"],
            "image_link": i["post_content"]["link"],
            "victimEmail": i["victimEmail"]
            
        })
    #return jsonify(fbReport)
    return render_template("facebookReport.html", data = fbReport)



if __name__ == '__main__':
    app.secret_key = 'mysecret'
    app.run(host='0.0.0.0',debug=True,port=3007)
