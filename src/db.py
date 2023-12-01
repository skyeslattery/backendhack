from flask_sqlalchemy import SQLAlchemy
import datetime

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = "post"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", back_populates="posts")
    timestamp = db.Column(db.DateTime, nullable=False)
    is_found = db.Column(db.Boolean, nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a Post
        """
        self.description = kwargs.get("description")
        self.user_id = kwargs.get("user_id")
        self.is_found = kwargs.get("is_found")
        self.timestamp = datetime.datetime.now()
    
    def serialize(self):
        return {
            "id": self.id,
            "description": self.description,
            "is_found": self.is_found,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat()
        }
    
    def serializeNoUser(self):
        return {
            "id": self.id,
            "description": self.description,
            "is_found": self.is_found,
            "timestamp": self.timestamp.isoformat()
        }



class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    netid = db.Column(db.String, nullable=False)
    posts = db.relationship("Post") 

    def __init__(self, **kwargs):
        """
        Initialize a User object
        """
        self.name = kwargs.get("name", "")
        self.netid = kwargs.get("netid", "")

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "netid": self.netid,
            "posts": [post.serializeNoUser() for post in self.posts]
        }
    
    def serializeNoPosts(self):
        return {
            "id": self.id,
            "name": self.name,
            "netid": self.netid
        }