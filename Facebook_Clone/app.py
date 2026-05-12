#!/usr/bin/python3
from flask import Flask, render_template, redirect, url_for, request, session, flash
import pymongo
from datetime import datetime
import os
import bcrypt
from random import randint

app = Flask(__name__)
app.secret_key = 'facebook_secret'
app.config['UPLOAD_FOLDER'] = 'static/user-content/'

# Database Connection
client = pymongo.MongoClient('localhost', 27017)
db = client['chat-app'] # Reusing same DB

@app.route('/')
def index():
    if session.get('username'):
        return redirect(url_for('feed'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username').lower()
    password = request.form.get('password')
    
    # Specific credentials requested by user
    if username == "facebook" and password == "facebook123":
        # Ensure 'facebook' user exists in DB for proper feed attribution
        user = db.users.find_one({'username': 'facebook'})
        if not user:
            hashed = bcrypt.hashpw("facebook123".encode('utf-8'), bcrypt.gensalt())
            db.users.insert_one({
                'username': 'facebook',
                'password': hashed,
                'fullname': 'Facebook Admin'
            })
            user = db.users.find_one({'username': 'facebook'})
            
        session['username'] = 'facebook'
        session['fullname'] = user['fullname']
        return redirect(url_for('feed'))
    
    user = db.users.find_one({'username': username})
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        session['username'] = username
        session['fullname'] = user['fullname']
        return redirect(url_for('feed'))
    
    flash("Invalid credentials")
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/feed')
def feed():
    if not session.get('username'):
        return redirect(url_for('index'))
    
    post_id = request.args.get('id')
    if post_id:
        try:
            posts = list(db.posts.find({'platform': 'facebook', 'id': int(post_id)}))
        except:
            posts = list(db.posts.find({'platform': 'facebook', 'id': post_id}))
    else:
        posts = list(db.posts.find({'platform': 'facebook'}).sort('date', -1))
        
    return render_template('feed.html', posts=posts, user=session.get('username'), fullname=session.get('fullname'))

@app.route('/post', methods=['POST'])
def post():
    if not session.get('username'):
        return redirect(url_for('index'))
    
    content_text = request.form.get('content')
    media = request.files.get('media')
    
    file_path = ""
    post_type = "text"
    
    if media and media.filename != "":
        post_type = "media"
        filename = media.filename
        user_dir = os.path.join(app.config['UPLOAD_FOLDER'], session.get('username'))
        if not os.path.exists(user_dir):
            os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, filename)
        media.save(file_path)

    id = randint(10000, 99999)
    post_doc = {
        'id': id,
        'username': session.get('username'),
        'fullname': session.get('fullname'),
        'date': datetime.now(),
        'likes': 0,
        'platform': 'facebook',
        'is_blurred': False,
        'content': {
            'posttype': post_type,
            'medialink': file_path.replace("\\", "/"),
            'postcontent': content_text,
            'postlocation': '',
            'postlink': '',
            'image_prediction': None,
            'text_prediction': None,
            'link_details': {'description': '', 'image': '', 'title': ''}
        }
    }
    db.posts.insert_one(post_doc)
    return redirect(url_for('feed'))

if __name__ == '__main__':
    if not os.path.exists('static/user-content'):
        os.makedirs('static/user-content', exist_ok=True)
    app.run(host='127.0.0.1', port=3005, debug=True)
