from db import db
from db import Post
from db import User
from flask import Flask, request
import json
import os

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

    if description is None:
        return failure_response("Please add description", 400)

    new_post = Post(description=description, is_found=is_found, user_id=user_id)

    db.session.add(new_post)
    db.session.commit()

    return success_response(new_post.serialize(), 201)

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)