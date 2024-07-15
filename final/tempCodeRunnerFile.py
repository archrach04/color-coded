from flask import Flask, render_template, request, jsonify, send_from_directory
import pandas as pd
import openai
from flask_cors import CORS
import logging
import os

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Set your OpenAI API key from environment variables
openai.api_key = 'apikey'

# Route for the initial page
@app.route('/')
def index():
    return render_template('body1.html')

# Route for body type calculation
@app.route('/calculate_body_type', methods=['POST'])
def calculate_body_type():
    if request.method == 'POST':
        try:
            shoulders = float(request.form['shoulders'])
            bust = float(request.form['bust'])
            waist = float(request.form['waist'])
            hips = float(request.form['hips'])

            body_type = determine_body_type(shoulders, bust, waist, hips)
            recommendations = get_dress_recommendations(body_type)

            return render_template('body2.html', body_type=body_type, recommendations=recommendations)
        except ValueError:
            return "Invalid input. Please enter numerical values.", 400

def determine_body_type(shoulders, bust, waist, hips):
    shoulder_to_waist_ratio = shoulders / waist
    bust_to_waist_ratio = bust / waist
    waist_to_hips_ratio = waist / hips
    hips_to_shoulders_ratio = hips / shoulders

    if 0.9 <= shoulder_to_waist_ratio <= 1.1 and 0.9 <= waist_to_hips_ratio <= 1.1:
        return "Rectangle"
    elif hips_to_shoulders_ratio > 1.05 and waist_to_hips_ratio < 0.85:
        return "Triangle/Pear"
    elif shoulder_to_waist_ratio > 1.05 and 0.75 <= waist_to_hips_ratio < 0.95:
        return "Inverted Triangle"
    elif shoulders / hips >= 0.9 and shoulders / hips <= 1.1 and waist / shoulders < 0.75 and waist / hips < 0.75:
        return "Hourglass"
    elif bust / hips > 1.05 and waist_to_hips_ratio > 0.75:
        return "Round/Apple"
    else:
        return "Undefined body type"

def get_dress_recommendations(body_type):
    recommendations = {
        "Rectangle": "Mandarin Collar, Square Neck, Round Neck, Keyhole Neck, Boat Neck, V-Neck, Sweetheart Neck, Shirt Collar, Scoop Neck, Tie-Up Neck, Cowl Neck, Band Collar, Halter Neck, Shoulder Straps, U-Neck, One Shoulder, Shawl Neck, High Neck, Off-Shoulder, Peter Pan Collar, Choker Neck, Jewel Neck, Hood, Strapless, Above the Keyboard Collar, Polo Collar, Turtle Neck, Mock Collar, Shawl Collar, Lapel Collar",
        "Triangle/Pear": "A-Line Dresses, Fit-and-Flare Dresses, Off-the-Shoulder Dresses, Boat Neck Dresses, Empire Waist Dresses",
        "Inverted Triangle": "A-Line Dresses, V-Neck Dresses, Wrap Dresses, Peplum Dresses, Fit-and-Flare Dresses",
        "Hourglass": "Wrap Dresses, Bodycon Dresses, Sheath Dresses, Fit-and-Flare Dresses, Peplum Dresses",
        "Round/Apple": "Empire Waist Dresses, A-Line Dresses, V-Neck Dresses, Wrap Dresses, Shift Dresses"
    }
    return recommendations.get(body_type, "No recommendations available for this body type.")

# Route for color page
@app.route('/color')
def color():
    return render_template('color.html')

# Route for serving color.js
@app.route('/color.js')
def serve_js():
    return send_from_directory('', 'color.js')

# Route for color palette
@app.route('/getPalette', methods=['POST'])
def get_palette():
    try:
        data = request.get_json()
        app.logger.debug(f"Received data: {data}")
        eye = data.get('eye')
        hair = data.get('hair')
        skin = data.get('skin')
        lips = data.get('lips')

        prompt = f"""
        I have the following colors for eye, hair, skin, and lips:
        Eye color: {eye}
        Hair color: {hair}
        Skin color: {skin}
        Lips color: {lips}
        Based on these colors, what is my skin tone color palette in terms of spring, summer, autumn, or winter? Please also suggest suitable clothing colors. ['Black' 'Orange' 'Navy Blue' 'Red' 'Beige' 'Yellow' 'Green' 'Pink'
        'Mustard' 'Teal' 'Peach' 'Maroon' 'Blue' 'Sea Green' 'Lime Green'
        'Burgundy' 'Fluorescent Green' 'Lavender' 'Magenta' 'Purple' 'White'
        'Off White' 'Charcoal' 'Cream' 'Copper' 'Multi' 'Mauve' 'Grey' 'Brown'
        'Turquoise Blue' 'Rust' 'Violet' 'Assorted' nan 'Fuchsia' 'Olive' 'Coral'
        'Grey Melange' 'Rose' 'Gold' 'Khaki' 'Tan' 'Coffee Brown' 'Silver' 'Nude'
        'Camel Brown' 'Taupe' 'Bronze' 'Champagne' 'Rose Gold']. output should be in an array
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )

        result = response.choices[0].message['content'].strip()
        app.logger.debug(f"OpenAI response: {result}")

        lines = result.split('\n', 1)
        palette = lines[0] if len(lines) > 0 else 'Unknown'
        suggestions = lines[1] if len(lines) > 1 else 'No suggestions available'

        return jsonify({'palette': palette, 'suggestions': suggestions})
    
    except Exception as e:
        app.logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

# Route for search page
@app.route('/search')
def search():
    return render_template('search.html')

# Route for performing search
@app.route('/perform_search', methods=['POST'])
def perform_search():
    keyword = request.form['keyword']
    app.logger.debug(f"Search keyword: {keyword}")
    products = get_relevant_products(keyword)
    app.logger.debug(f"Filtered products: {products.head()}")
    return render_template('sresults.html', products=products.to_dict(orient='records'))

def get_relevant_products(keyword):
    try:
        df = pd.read_csv('Fashion Dataset.csv')
        app.logger.debug(f"DataFrame loaded with shape: {df.shape}")
        
        df_lower = df.apply(lambda x: x.astype(str).str.lower())
        mask = df_lower.apply(lambda row: row.str.contains(keyword.lower()).any(), axis=1)
        relevant_products = df[mask]
        
        app.logger.debug(f"Relevant products shape: {relevant_products.shape}")
        return relevant_products
    
    except FileNotFoundError:
        app.logger.error("File not found: Fashion Dataset.csv")
        return pd.DataFrame()  # Return an empty DataFrame if file is not found

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True)

