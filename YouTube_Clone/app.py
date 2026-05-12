#!/usr/bin/python3
from flask import Flask, render_template, redirect, url_for, request, session, flash
import pymongo
from datetime import datetime
import os
from random import randint

app = Flask(__name__)
app.secret_key = 'youtube_secret'
app.config['UPLOAD_FOLDER'] = 'static/user-content/'

# Database Connection
client = pymongo.MongoClient('localhost', 27017)
db = client['chat-app']

@app.route('/')
def index():
    videos = list(db.posts.find({'platform': 'youtube'}).sort('date', -1))
    return render_template('index.html', videos=videos)

@app.route('/watch/<int:video_id>')
def watch(video_id):
    video = db.posts.find_one({'id': video_id, 'platform': 'youtube'})
    if not video:
        return "Video not found", 404
    videos = list(db.posts.find({'platform': 'youtube', 'id': {'$ne': video_id}}).limit(10))
    return render_template('watch.html', video=video, videos=videos)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    # YouTube doesn't require login for viewing, but let's assume a default user for uploads
    if request.method == 'POST':
        title = request.form.get('title')
        media = request.files.get('video')
        
        file_path = ""
        if media and media.filename != "":
            filename = media.filename
            user_dir = os.path.join(app.config['UPLOAD_FOLDER'], "yt_user")
            if not os.path.exists(user_dir):
                os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, filename)
            media.save(file_path)

        id = randint(10000, 99999)
        post_doc = {
            'id': id,
            'username': 'yt_user',
            'fullname': 'YouTube Creator',
            'date': datetime.now(),
            'likes': 0,
            'platform': 'youtube',
            'is_blurred': False,
            'content': {
                'posttype': 'video',
                'medialink': file_path.replace("\\", "/"),
                'postcontent': title,
                'postlocation': '',
                'postlink': '',
                'image_prediction': None,
                'text_prediction': None,
                'link_details': {'description': '', 'image': '', 'title': title}
            }
        }
        db.posts.insert_one(post_doc)
        return redirect(url_for('index'))
    return render_template('upload.html')

if __name__ == '__main__':
    if not os.path.exists('static/user-content'):
        os.makedirs('static/user-content', exist_ok=True)
    app.run(host='127.0.0.1', port=3006, debug=True)
