from flask import Flask
from pymongo import MongoClient
import gridfs

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['recipeKitchenette']
fs = gridfs.GridFS(db)

# Hardcoded recipe data
recipes = [
    {
        'recipe_name': 'Avocado ToastB',
        'time': '5 mins',
        'description': 'Healthy recipe for Avocado with bread',
        'image_path': r'E:\George Mason University\sem3\INFS 740\project\recipekitchenette\rk\static\images\avocado_toast.jpg'
    },
    {
        'recipe_name': 'Spaghetti CarbonaraB',
        'time': '20 mins',
        'description': 'Classic Italian pasta dish with bacon and eggs',
        'image_path': r'E:\George Mason University\sem3\INFS 740\project\recipekitchenette\rk\static\images\spaghetti.jpg'
    },
    # Add more recipes as needed
]

# Insert hardcoded recipe data into MongoDB if it doesn't already exist
for recipe in recipes:
    existing_recipe = db.recipes.find_one({'recipe_name': recipe['recipe_name']})
    if not existing_recipe:
        with open(recipe['image_path'], 'rb') as f:
            image_data = f.read()
            image_id = fs.put(image_data, filename=f.name)
        recipe['image_id'] = image_id
        db.recipes.insert_one(recipe)

if __name__ == '__main__':
    app.run(debug=True)
