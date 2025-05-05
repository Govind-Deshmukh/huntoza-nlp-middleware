import jwt
from config import JWT_SECRET
from models.db import users_collection, plans_collection

def verify_user(token):
    """Verify user authentication token and check plan"""
    if not token:
        return None, "No token provided"
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload.get('id')
        
        # Find user in database
        user = users_collection.find_one({"_id": user_id})
        if not user:
            return None, "User not found"
        
        # Check if user has an active plan that allows job extraction
        plan = plans_collection.find_one({"_id": user.get("currentPlan")})
        if not plan or not plan.get("features", {}).get("jobExtraction", False):
            return None, "User plan does not include job extraction feature"
        
        return user, None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"
    except Exception as e:
        return None, f"Authentication error: {str(e)}"

