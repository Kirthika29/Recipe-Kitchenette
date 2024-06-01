from flask import Flask
from pymongo import MongoClient
import gridfs

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['recipeKitchenette']
fs = gridfs.GridFS(db)

# Hardcoded recipe data
ingre = [
            {
        "name": "Chicken",
        "category": "Protein",
        "allergens": [],
        "calories": 165,
        "image": r"E:\George Mason University\sem3\INFS 740\project\recipekitchenette\rk\static\images\chicken.jpg"
        },
        {
        "name": "Beef",
        "category": "Protein",
        "allergens": ["gluten"],
        "calories": 240,
        "image": r"E:\George Mason University\sem3\INFS 740\project\recipekitchenette\rk\static\images\beef.jpg"
        },
        {
        "name": "Potatoes",
        "category": "Vegetable",
        "allergens": [],
        "calories": 93,
        "image": r"E:\George Mason University\sem3\INFS 740\project\recipekitchenette\rk\static\images\potato.jpg"
        }
    # Add more recipes as needed
]

# Insert hardcoded recipe data into MongoDB if it doesn't already exist
for ingre in ingre:
    existing_ingre = db.ingredients.find_one({'name': ingre['name']})
    if not existing_ingre:
        with open(ingre['image'], 'rb') as f:
            image_data = f.read()
            image_id = fs.put(image_data, filename=f.name)
        ingre['image_id'] = image_id
        db.ingredients.insert_one(ingre)

if __name__ == '__main__':
    app.run(debug=True)
