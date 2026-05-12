#!/usr/bin/python3
"""
All functions related to facebook go here
"""
#!/usr/bin/python3
from bs4 import BeautifulSoup
import time
import urllib.request
import requests
import urllib.parse
import imageio


def get_local_fb_data(url):
    """ Fetch data from local FB clone database """
    import pymongo
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(url)
    post_id = parse_qs(parsed.query).get('id')
    if post_id:
        client = pymongo.MongoClient('localhost', 27017)
        db = client['chat-app']
        post = db.posts.find_one({'id': int(post_id[0]), 'platform': 'facebook'})
        if post:
            return [post['content']['medialink']], [post['content']['postcontent']]
    return [], []

def parse_urls(urlencode):
    if "localhost:3005" in urlencode or "127.0.0.1:3005" in urlencode:
        return get_local_fb_data(urlencode)
        
    url_prefix = 'https://www.facebook.com/plugins/post.php?href='
    url_suffix = '&show_text=1'
    full_url = url_prefix + urlencode + url_suffix
    try:
        response = requests.get(full_url)
        soup = BeautifulSoup(response.text, "html.parser")
        imgs_ret = []
        content_ret = []
        images = soup.findAll('img')
        content = soup.findAll('p')
        for img in images:
            try:
                import imageio
                img_data = imageio.imread(img['src'])
                if len(img_data.shape) == 3:
                    height, width, channels = img_data.shape
                else:
                    height, width = img_data.shape
                if(height > 50 and width > 50):
                    imgs_ret.append(img['src'])
            except:
                continue
        for p in content:
            if p.contents:
                content_ret.append(p.contents[0])
        return imgs_ret, content_ret
    except:
        return [], []


def get_data_facebook(fb_link,link):
    """ Push Data for Facebook into the database
    """
    images, text = parse_urls(fb_link)
    if(len(images)!=0):
        post_type = "image"
    else:
        post_type = "text"

    post_data = {
        'link': link,
        'post_type': post_type,
        'post_text': text[0] if text else "No text found",
        'post_media': images[0] if images else ""
    }
    return post_data
