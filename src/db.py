from flask_sqlalchemy import SQLAlchemy
import datetime
import base64
import boto3
import io
from io import BytesIO
from mimetypes import guess_type, guess_extension
import os
from PIL import Image
import random
import re
import string
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()

EXTENSIONS = ["png", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-1.amazonaws.com"

class Asset(db.Model):
    """
    Asset model
    """
    __tablename__ = "asset"
    id = db.Column(db.Integer, primary_key=True)
    base_url = db.Column(db.String, nullable=False)
    salt = db.Column(db.String, nullable=False)
    extension = db.Column(db.String, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes an Asset
        """
        self.create(kwargs.get("image_data"))

    def serialize(self):
        return {
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created-at": str(self.created_at)
        }

    def create(self, image_data):
        try:
            ext = guess_extension(guess_type(image_data)[0])[1:]

            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} is not valid")
            
            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )

            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.created_at = datetime.datetime.now()

            img_filename = f"{self.salt}.{self.extension}"
            
            self.upload(img, img_filename)


        except Exception as e:
            print("Error when creating image: {e}")

    def upload(self, img, img_filename):
        """
        Attempts to upload the image into the specified S3 bucket
        """
        try:
            img_temp_loc = f"{BASE_DIR}/{img_filename}"
            img.save(img_temp_loc)

            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temp_loc, S3_BUCKET_NAME, img_filename)

            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET_NAME, img_filename)
            object_acl.put(ACL = "public-read")

            os.remove(img_temp_loc)

        except Exception as e:
            print(f"Error when uploading image: {e}")

class Post(db.Model):
    __tablename__ = "post"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship("User", back_populates="posts")
    timestamp = db.Column(db.DateTime, nullable=False)
    is_found = db.Column(db.Boolean, nullable=False)
    image_url = db.Column(db.String, nullable=True)

    def __init__(self, **kwargs):
        """
        Initialize a Post
        """
        self.description = kwargs.get("description")
        self.user_id = kwargs.get("user_id")
        self.is_found = kwargs.get("is_found")
        self.timestamp = datetime.datetime.now()
        self.image_url = kwargs.get("image_url")
    
    def serialize(self):
        return {
            "id": self.id,
            "description": self.description,
            "is_found": self.is_found,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "image_url": self.image_url
        }
    
    def serializeNoUser(self):
        return {
            "id": self.id,
            "description": self.description,
            "is_found": self.is_found,
            "timestamp": self.timestamp.isoformat(),
            "image_url": self.image_url
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