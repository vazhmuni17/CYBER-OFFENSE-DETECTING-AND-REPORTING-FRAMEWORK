#!/usr/bin/python3
"""
All functions related to Viraly go here
"""

def get_data_viraly(db,content_type,viraly_id):
    """ Push Data for viraly into the database
    """
    viraly_url = "http://192.168.12.209:3069/"
    if(content_type=="post"):
        post = db.get_viraly_post(viraly_id)
        if post and 'content' in post:
            post_content = {
                'content_type':content_type,
                'post_id': viraly_id,
                'post_type': post['content'].get('posttype', 'text'),
                'post_text': post['content'].get('postcontent', 'No content found'),
                'post_media': viraly_url + post['content'].get('medialink', '')
            }
        else:
            post_content = {
                'content_type':content_type,
                'post_id': viraly_id,
                'post_type': 'text',
                'post_text': 'Post not found',
                'post_media': ''
            }
    elif(content_type=="message"):
        import csv
        import os

        chat = db.get_viraly_chat(viraly_id)
        #Create user content folder
        if not os.path.exists("static/user-content"):
            os.makedirs("static/user-content")
        chat_csv = open("static/user-content/"+viraly_id+'.csv','w')
        writer =csv.writer(chat_csv)
        for message in chat:
            writer.writerow((message['date'],message['author'],message['content']))
        chat_csv.close()
        post_content = {
            'content_type':content_type,
            'chat_id': viraly_id,
            'chat_file':viraly_url+"static/user-content/"+viraly_id+'.csv'
        }
    else:
        pass

    return post_content

