from db import db
from db import Post
from db import User
from flask import Flask, request
import json
from db import Asset
import os
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
from difflib import SequenceMatcher # for simple search

app = Flask(__name__)
db_filename = "foundit.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()

def success_response(body, code=200):
    return json.dumps(body), code

def failure_response(message, code=404):
    return json.dumps({'error': message}), code

@app.route("/")
def base():
    return "FoundIt"

@app.route("/api/users/")
def get_users():
    """
    Get all users
    """
    users = [users.serialize() for users in User.query.all()]

    return success_response({"users": users})

@app.route("/api/posts/found/")
def get_found():
    """
    Get all found posts
    """
    users = [user for user in User.query.all()]
    posts = []
    for user in users:
        for post in user.posts:
            if post.is_found:
                posts.append(post.serialize())
           
    return success_response({"posts": posts})

@app.route("/api/posts/lost/")
def get_lost():
    """
    Get all lost posts
    """
    users = [user for user in User.query.all()]
    posts = []
    for user in users:
        for post in user.posts:
            if not post.is_found:
                posts.append(post.serialize())
           
    return success_response({"posts": posts})

@app.route("/api/users/", methods=["POST"])
def create_user():
    """
    Creates user with name and netid
    """
    body = json.loads(request.data)
    netid=body.get('netid')
    name=body.get('name')
    users = User.query.all()

    if netid is None:
        return failure_response("NetID not found", 400)
    if name is None:
        return failure_response("Name not found", 400)
    for user in users:
        if(user.netid==netid):
            return success_response(user.serialize(), 201)

    new_user = User(netid=netid, name=name)

    db.session.add(new_user)
    db.session.commit()
    return success_response(new_user.serialize(), 201)

@app.route("/api/users/<int:user_id>/posts/", methods=["POST"])
def create_post(user_id):
    """
    Creates post for user user_id
    """
    user = User.query.get(user_id)
    if user is None:
        return failure_response("User not found!", 404)

    body = json.loads(request.data)
    description = body.get("description")
    is_found = body.get("is_found")
    image_data = body.get("image_data")

    if image_data is None:
        return failure_response("No base64 image found")

    if description is None:
        return failure_response("Please add description", 400)
    
    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()
    url = asset.serialize().get("url")

    new_post = Post(description=description, is_found=is_found, user_id=user_id, image_url=url)

    db.session.add(new_post)
    db.session.commit()

    return success_response(new_post.serialize(), 201)

@app.route("/api/posts/search/", methods=["POST"])
def search_posts():
    #Simple Search
    body = json.loads(request.data)
    description = body.get("description")
    status = body.get("is_found")
    if status:
        related_posts = Post.query.filter_by(is_found=False).all()
    else:
        related_posts = Post.query.filter_by(is_found=True).all()
    matches = []
    for post in related_posts:
        if similar(description, post.description) > 0.5:
            matches.append(post.serialize())
    return success_response(matches)
        
    
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()

@app.route("/api/posts/match/", methods=["POST"])
def match_posts():
    #Cross Search
    module_url = "https://tfhub.dev/google/universal-sentence-encoder/4" 
    model = hub.load(module_url)

    body = json.loads(request.data)
    status = body.get('is_found')
    if status:
        related_posts = Post.query.filter_by(is_found=True).all()
    else:
        related_posts = Post.query.filter_by(is_found=False).all()

    doc = [post.description for post in related_posts]
    bank_vec = model(doc)

    query_description = body.get('description')
    query_vec = model([query_description])

    correlation = np.transpose(np.inner(query_vec, bank_vec))
    top_posts = np.argmax(correlation, axis=1)

    matches = []

    for post in top_posts:
        if(correlation[post] > 0.5):
            match = related_posts[post]
            matches.append(match.serialize())

    if(len(matches)>0):
        return success_response(matches)
    else:
        return failure_response("No matching posts found", 200)
    

    # Version 1:
    # correlation = np.transpose(np.inner(query_vec, bank_vec))
    # first_similar = np.argmax(correlation, axis=0)[0]
    # second_similar = np.argmax(correlation, axis=0)[1]
    # third_similar = np.argmax(correlation, axis=0)[2]
    # if correlation[first_similar] > 0.5:
    #     if correlation[second_similar] > 0.5:
    #         if correlation[third_similar] > 0.5:
    #             suggested_post = lost_posts[first_similar, second_similar, third_similar]
    #             return success_response({"message": "Here are some suggested posts that matches your lost item", "suggested_post": suggested_post})
    #         suggested_post = lost_posts[first_similar, second_similar]
    #         return success_response({"message": "Here are some suggested posts that matches your lost item", "suggested_post": suggested_post})
    #     suggested_post = lost_posts[first_similar]
    #     return success_response({"message": "Here are some suggested posts that matches your lost item", "suggested_post": suggested_post})
    # else:
    #     return failure_response({"message": "No matching posts found"})

    # Version 2:
    # module_url = "https://tfhub.dev/google/universal-sentence-encoder/4" 
    # model = hub.load(module_url)
    # lost_posts = [Post.objects.filter(is_found=not is_found)] #change logic
    # doc = [lost_posts.description] # a list of descriptions
    # bank_vec = model(doc)
    # query = [description]
    # query_vec = model(query)
    # correlation = np.transpose(np.inner(query_vec,bank_vec))
    # location_of_top_similarly = doc[np.argmax(correlation, axis=0)[0]]
    # lost_posts[location_of_top_similarly]
    # if correlation > 0.5:
    #     return "here is a suggested post that matches your lost item" + lost_posts


@app.route("/api/users/<int:user_id>/")
def get_user(user_id):
    """
    Get user user_id
    """
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    return success_response(user.serialize())

@app.route("/api/posts/<int:post_id>/", methods=["DELETE"])
def delete_post(post_id):
    """
    Delete post post_id
    """
    post = Post.query.filter_by(id=post_id).first()
    if post is None:
        return failure_response("Post not found!")
    db.session.delete(post)
    db.session.commit()
    return success_response(post.serialize())

@app.route("/api/upload/", methods=["POST"])
def upload():
    """
    Uploads image to AWS
    """
    body = json.loads(request.data)
    image_data = body.get("image_data")

    if image_data is None:
        return failure_response("No base64 image found")
    
    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()

    return success_response(asset.serialize(), 201)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)