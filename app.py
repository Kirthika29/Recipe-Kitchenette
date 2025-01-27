from flask import Flask, render_template, url_for, request, session, redirect, jsonify
from flask_pymongo import PyMongo
import bcrypt
from pymongo import TEXT
import gridfs
import base64
from bson.objectid import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env file
app = Flask(__name__, static_folder='static')

app.config['MONGO_DBNAME'] = 'recipeKitchenette'
#app.config['MONGO_URI'] = 'mongodb://localhost:27017/recipeKitchenette'
app.config['MONGO_URI'] = os.getenv('MONGO_URI')

mongo = PyMongo(app)

# Drop the existing text index if it exists
users = mongo.db.users
recipes_collection = mongo.db.recipes
recipe_steps_collection = mongo.db.recipe_steps
ingredients_collection = mongo.db.ingredients
nutrition_collection = mongo.db.nutrition
favorites_collection = mongo.db.favorites


# Create a text index on the 'recipe_name' and 'description' fields
recipes_collection.create_index([('recipe_name', TEXT), ('description', TEXT)], name='recipe_name_text_description_text')
ingredients_collection.create_index([("name", "text"), ("category", "text")])
nutrition_collection.create_index([("recipe_name", "text"), ("allergens", "text")])


# Initialize GridFS
fs = gridfs.GridFS(mongo.db)
def get_recipe_by_name(recipe_name):
    recipes_collection = mongo.db.recipes
    recipe = recipes_collection.find_one({'recipe_name': recipe_name})
    return recipe
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/ingredients')
def ingredients():
    all_ingredients = list(ingredients_collection.find())
    return render_template('all_ingre.html', ingredients=all_ingredients)

@app.route('/ingredient/<ingredient_id>/edit', methods=['GET', 'POST'])
def edit_ingredient(ingredient_id):
    if request.method == 'POST':
        # Retrieve the updated values from the request
        name = request.form['name']
        category = request.form['category']
        calories = request.form['calories']
        popularity = request.form['popularity']

        # Update the ingredient in the database
        ingredients_collection.update_one(
            {'_id': ObjectId(ingredient_id)},
            {'$set': {
                'name': name,
                'category': category,
                'calories': calories,
                'popularity': popularity
            }}
        )

        # Redirect the user back to the ingredient list page
        return redirect(url_for('ingredients'))
    else:
        # Fetch the ingredient details and render the edit form
        ingredient = ingredients_collection.find_one({'_id': ObjectId(ingredient_id)})
        return render_template('edit_ingredient.html', ingredient=ingredient)

@app.route('/ingredient/<ingredient_id>/delete', methods=['POST'])
def delete_ingredient(ingredient_id):
    result = ingredients_collection.delete_one({'_id': ObjectId(ingredient_id)})
    if result.deleted_count > 0:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "error": "Ingredient not found"}), 404

@app.route('/ingredient/add', methods=['GET', 'POST'])
def add_ingredient():
    if request.method == 'POST':
        # Retrieve the new ingredient details from the form
        name = request.form['name']
        category = request.form['category']
        calories = request.form['calories']
        popularity = request.form['popularity']
        ingre_image = request.files['ingre_image']

        # Save the ingredient image to GridFS
        if ingre_image:
            image_id = fs.put(ingre_image.read(), filename=ingre_image.filename)
        else:
            image_id = None

        # Save the new ingredient to the database
        ingredients_collection.insert_one({
            'name': name,
            'category': category,
            'calories': calories,
            'popularity': popularity,
            'image_id': image_id
        })

        return redirect(url_for('ingredients'))
    else:
        return render_template('add_ingredient.html')

@app.route('/ingredient_calories')
def ingredient_calories():
    top_ingredients = list(ingredients_collection.find().sort("popularity", 1).limit(3))
    ingredient_data = [
        {
            "name": ingredient["name"],
            "calories": ingredient["calories"]
        }
        for ingredient in top_ingredients
    ]
    return jsonify(ingredient_data)

@app.route('/edit_recipe/<recipe_id>', methods=['GET', 'POST'])
def edit_recipe(recipe_id):
    if 'user_id' in session:
        user_id = ObjectId(session['user_id'])

        if request.method == 'POST':
            recipe_name1 = request.form['recipe_name']
            recipe_name = recipes_collection.find_one({'_id': ObjectId(recipe_id)}, {'recipe_name': 1})['recipe_name']
            recipe_description = request.form['recipe_description']
            recipe_time = request.form['recipe_time']
            recipe_image = request.files['recipe_image']
            recipe_instructions = request.form['recipe_instructions'].split('\n')

            # Save the recipe image to GridFS
            if recipe_image:
                # Save the recipe image to GridFS
                image_id = fs.put(recipe_image.read(), filename=recipe_image.filename)
            else:
                # Use the existing image_id from the recipes_collection document
                recipe = recipes_collection.find_one({'_id': ObjectId(recipe_id)})
                image_id = recipe.get('image_id')

            # Update the recipe in the recipes_collection
            recipes_collection.update_one(
                {'_id': ObjectId(recipe_id)},
                {'$set': {
                    'recipe_name': recipe_name1,
                    'description': recipe_description,
                    'time': recipe_time,
                    'image_id': image_id
                }}
            )

            # Update the recipe steps in the recipe_steps_collection
            recipe_steps_collection.update_one(
                {'recipe_name': recipe_name},
                {'$set': {
                    'recipe_name': recipe_name1,
                    'instructions': [step.strip() for step in recipe_instructions]
                }}
            )

            # Update the nutrition information in the nutrition_collection
            nutrition_collection.update_one(
                {'recipe_name': recipe_name},
                {'$set': {
                    'recipe_name': recipe_name1
                }}
            )

            return redirect(url_for('recipe_details', recipe_name=recipe_name1))
        else:
            recipe = recipes_collection.find_one({'_id': ObjectId(recipe_id)})
            recipe_steps = recipe_steps_collection.find_one({'recipe_name': recipe['recipe_name']})
            nutrition = nutrition_collection.find_one({'recipe_name': recipe['recipe_name']})

            return render_template('edit_recipe.html', recipe=recipe, recipe_steps=recipe_steps, nutrition=nutrition)
    else:
        return redirect(url_for('login'))

@app.route('/delete_recipe/<recipe_id>', methods=['GET', 'POST'])
def delete_recipe(recipe_id):
    if 'user_id' in session:
        user_id = ObjectId(session['user_id'])

        # Fetch the recipe details
        recipe = recipes_collection.find_one({'_id': ObjectId(recipe_id)})

        if request.method == 'POST':
            # Delete the recipe from the recipes_collection
            recipes_collection.delete_one({'_id': ObjectId(recipe_id)})

            # Delete the recipe steps from the recipe_steps_collection
            recipe_steps_collection.delete_one({'recipe_name': recipe['recipe_name']})

            # Delete the nutrition information from the nutrition_collection
            nutrition_collection.delete_one({'recipe_name': recipe['recipe_name']})

            # Delete the recipe from the user's favorites
            favorites_collection.delete_many({'recipe_id': ObjectId(recipe_id)})

            return redirect(url_for('recipe'))
        
        return redirect(url_for('login'))


@app.route('/login', methods=['POST'])
def login():
    users = mongo.db.users
    login_user = users.find_one({'name': request.form['username']})

    if login_user:
        if bcrypt.checkpw(request.form['pass'].encode('utf-8'), login_user['password']):
            session['username'] = request.form['username']
            session['user_id'] = str(login_user['_id'])
            return redirect(url_for('index'))
    return render_template('index.html', invalid_cred=True)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))



@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'name': request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form['pass'].encode('utf-8'), bcrypt.gensalt())
            users.insert_one({'name': request.form['username'], 'password': hashpass})
            session['username'] = request.form['username']
            session['user_id'] = str(users.inserted_id)
            return redirect(url_for('index'))

        return render_template('register.html', username_exists=True)

    return render_template('register.html')

@app.route('/recipe')
def recipe():
    recipes_from_db = recipes_collection.find()
    recipes_with_images = []
    for recipe in recipes_from_db:
        image_id = recipe.get('image_id')
        if image_id:
            image_data = fs.get(image_id).read()
            image_data_base64 = base64.b64encode(image_data).decode('utf-8')
            recipe['image_data_base64'] = image_data_base64
        recipes_with_images.append(recipe)

    # Get the user's favorite recipes
    favorite_recipes = []
    if 'user_id' in session:
        user_id = ObjectId(session['user_id'])
        for favorite in favorites_collection.find({'user_id': user_id}):
            recipe = recipes_collection.find_one({'_id': favorite['recipe_id']})
            if recipe:
                recipe['image_data_base64'] = get_recipe_image_data(recipe)
                favorite_recipes.append(recipe)

     # Get the user's recipes          
    user_recipes = list(recipes_collection.find({'user_id': user_id}))
    for recipe in user_recipes:
        recipe['image_data_base64'] = get_recipe_image_data(recipe)

    return render_template('recipe.html', recipes=recipes_with_images, favorite_recipes=favorite_recipes, user_recipes=user_recipes)

def get_recipe_image_data(recipe):
    image_id = recipe.get('image_id')
    if image_id:
        image_data = fs.get(image_id).read()
        return base64.b64encode(image_data).decode('utf-8')
    return None

@app.route('/recipe/<recipe_name>', methods=['GET', 'POST', 'DELETE'])
def recipe_details(recipe_name):
    recipe = recipes_collection.find_one({'recipe_name': recipe_name})
    if recipe:
        image_id = recipe.get('image_id')
        if image_id:
            image_data = fs.get(image_id).read()
            image_data_base64 = base64.b64encode(image_data).decode('utf-8')
            recipe['image_data_base64'] = image_data_base64

        # Check if the recipe is already in the user's favorites
        existing_favorite = None
        if 'user_id' in session:
            user_id = ObjectId(session['user_id'])
            recipe_id = recipe['_id']
            existing_favorite = favorites_collection.find_one({'user_id': user_id, 'recipe_id': recipe_id})

    if request.method == 'POST':
        if 'user_id' in session:
            user_id = ObjectId(session['user_id'])
            recipe_id = recipe['_id']

            # Check if the recipe is already in the user's favorites
            existing_favorite = favorites_collection.find_one({'user_id': user_id, 'recipe_id': recipe_id})
            if not existing_favorite:
                # Add the recipe to the user's favorites
                favorites_collection.insert_one({'user_id': user_id, 'recipe_id': recipe_id})
                # Redirect the user to the recipe details page
                return redirect(url_for('recipe_details', recipe_name=recipe_name))
            else:
                # remove from favorites
                favorites_collection.delete_one({'_id': ObjectId(existing_favorite['_id'])})
                return redirect(url_for('recipe_details', recipe_name=recipe_name))
        else:
            # The user is not logged in, redirect to the login page
            return redirect(url_for('login'))

    # Fetch the recipe steps from the 'recipe_steps' collection
    recipe_steps = recipe_steps_collection.find_one({'recipe_name': recipe_name})

    if recipe and recipe_steps:
        return render_template('recipe_details.html', recipe=recipe, recipe_steps=recipe_steps, existing_favorite=existing_favorite)
    else:
        return render_template('404.html'), 404

@app.route('/favorites', methods=['GET', 'POST', 'DELETE'])
def favorites():
    if 'user_id' in session:
        user_id = ObjectId(session['user_id'])

        if request.method == 'POST':
            # Add a recipe to the user's favorites
            recipe_id = request.form['recipe_id']
            existing_favorite = favorites_collection.find_one({'user_id': user_id, 'recipe_id': ObjectId(recipe_id)})
            if not existing_favorite:
                favorites_collection.insert_one({'user_id': user_id, 'recipe_id': ObjectId(recipe_id)})
            return redirect(url_for('recipe'))

        elif request.method == 'DELETE':
            # Remove a recipe from the user's favorites
            recipe_id = request.form['recipe_id']
            print(recipe_id)
            existing_favorite = favorites_collection.find_one({'user_id': user_id, 'recipe_id': ObjectId(recipe_id)})
            if existing_favorite:
                #favorites_collection.delete_one({'_id': ObjectId(existing_favorite)})
                favorites_collection.delete_one({'_id': ObjectId(existing_favorite['_id'])})
            #return redirect(url_for('recipe'))
            return render_template('index.html')

        # Fetch the user's favorite recipes
        favorite_recipes = []
        for favorite in favorites_collection.find({'user_id': user_id}):
            recipe = recipes_collection.find_one({'_id': favorite['recipe_id']})
            if recipe:
                recipe['image_data_base64'] = get_recipe_image_data(recipe)
                favorite_recipes.append(recipe)
        return render_template('recipe.html', favorite_recipes=favorite_recipes)

    else:
        # The user is not logged in, redirect to the login page
        return redirect(url_for('login'))
def get_recipe_name_by_id(recipe_id):
    recipe = recipes_collection.find_one({'_id': ObjectId(recipe_id)})
    if recipe:
        return recipe['recipe_name']
    return None
def get_recipe_image_data(recipe):
    image_id = recipe.get('image_id')
    if image_id:
        image_data = fs.get(image_id).read()
        return base64.b64encode(image_data).decode('utf-8')
    return None

@app.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    if 'user_id' in session:
        user_id = ObjectId(session['user_id'])

        if request.method == 'POST':
            recipe_name = request.form['recipe_name']
            recipe_description = request.form['recipe_description']
            recipe_time = request.form['recipe_time']
            recipe_image = request.files['recipe_image']
            recipe_ingredients = request.form['recipe_ingredients'].split(',')
            recipe_instructions = request.form['recipe_instructions'].split('\n')
            nutri_cal = request.form['nutri_cal']
            label_nutrition = request.form['label_nutrition'].split(',')
            allergen_nutrition = request.form['allergen_nutrition'].split(',')
            # Save the recipe image to GridFS
            image_id = fs.put(recipe_image.read(), filename=recipe_image.filename)

            # Insert the new recipe into the recipes_collection
            new_recipe = {
                'recipe_name': recipe_name,
                'time': recipe_time,
                'description': recipe_description,
                'image_id': image_id,
                'user_id': user_id
                
            }
            recipe_id = recipes_collection.insert_one(new_recipe).inserted_id

            # Insert the recipe steps into the recipe_steps_collection
            new_recipe_steps = {
                'recipe_name': recipe_name,
                'description': recipe_description,
                'ingredients': [{'name': ingredient.strip(), 'amount': '', 'unit': ''} for ingredient in recipe_ingredients],
                'instructions': [step.strip() for step in recipe_instructions]
                
            }
            recipe_steps_id = recipe_steps_collection.insert_one(new_recipe_steps).inserted_id

            # Insert the nutrition information into the nutrition_collection
            new_nutrition = {
                'recipe_name': recipe_name,
                'total_calories': int(nutri_cal),
                'label': [step.strip() for step in label_nutrition],
                'allergens': [step.strip() for step in allergen_nutrition]
            }
            nutrition_id = nutrition_collection.insert_one(new_nutrition).inserted_id

            recipes_collection.update_one(
                {'_id': recipe_id},
                {'$set': {'step_id': recipe_steps_id, 'nutrition_id': nutrition_id}}
            )

            return redirect(url_for('recipe'))
        else:
            return render_template('add_recipe.html')
    else:
        return redirect(url_for('login'))

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    if query:
        # Search recipes
        recipe_results = list(recipes_collection.find({
            '$text': {'$search': query},
            '$or': [
                {'recipe_name': {'$regex': query, '$options': 'i'}},
                {'description': {'$regex': query, '$options': 'i'}}
            ]
        }, {
            '_id': 1, 'recipe_name': 1, 'description': 1, 'image_path': 1
        }))

        # Search ingredients
        ingredient_results = list(ingredients_collection.find({
            '$text': {'$search': query},
            '$or': [
                {'name': {'$regex': query, '$options': 'i'}},
                {'category': {'$regex': query, '$options': 'i'}}
            ]
        }, {
            '_id': 1, 'name': 1, 'category': 1, 'image': 1
        }))

        # Search nutrition information
        nutrition_results = list(nutrition_collection.find({
            '$text': {'$search': query},
            '$or': [
                {'recipe_name': {'$regex': query, '$options': 'i'}},
                {'allergens': {'$in': [query]}}
            ]
        }, {
            '_id': 1, 'recipe_name': 1, 'calories': 1, 'allergens': 1
        }))

        # Render the search_results.html template and pass the results
        return render_template('search_results.html', recipe_results=recipe_results, ingredient_results=ingredient_results, nutrition_results=nutrition_results)
    else:
        return render_template('400.html'), 400


@app.route('/nutrition/<nutrition_id>', methods=['GET'])
def nutrition_details(nutrition_id):
    nutrition = nutrition_collection.find_one({'_id': ObjectId(nutrition_id)})
    if nutrition:
        recipe = recipes_collection.find_one({'recipe_name': nutrition['recipe_name']})
        if recipe:
            image_id = recipe.get('image_id')
            if image_id:
                image_data = fs.get(image_id).read()
                image_data_base64 = base64.b64encode(image_data).decode('utf-8')
                recipe['image_data_base64'] = image_data_base64
        return render_template('nutrition_details.html', nutrition=nutrition, recipe=recipe)
    else:
        return 'Nutrition information not found', 404

@app.route('/ingredient/<ingredient_id>', methods=['GET'])
def ingredient_details(ingredient_id):
    ingredient = ingredients_collection.find_one({'_id': ObjectId(ingredient_id)})
    if ingredient:
        image_id = ingredient.get('image_id')
        if image_id:
            image_data = fs.get(image_id).read()
            image_data_base64 = base64.b64encode(image_data).decode('utf-8')
            ingredient['image_data_base64'] = image_data_base64

        recipe_results = []
        for recipe_step in recipe_steps_collection.find():
            for ingredient_in_step in recipe_step.get('ingredients', []):
                if ingredient_in_step.get('ingredient_id') == ObjectId(ingredient_id):
                    recipe = recipes_collection.find_one({'recipe_name': recipe_step['recipe_name']})
                    if recipe:
                        recipe_results.append(recipe)
                        break  # Stop searching for this recipe once it's found

        return render_template('ingredient_details.html', ingredient=ingredient, recipe_results=recipe_results)
    else:
        return 'Ingredient not found', 404




if __name__ == '__main__':
    app.secret_key = 'mysecret'
    app.run(debug=True)
