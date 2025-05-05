import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/deva')
JWT_SECRET = os.getenv('JWT_SECRET', 'your_jwt_secret')
