# Import statements
from roboflow import Roboflow
from PIL import Image, ImageOps
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import numpy as np
import cv2
from tensorflow.keras.models import load_model
from board import *

# Initialize the Flask app and other configurations
app = Flask(__name__)
CORS(app)
app.secret_key = 'I am Aviral Katiyar.'

# Load models
model = load_model('model/chess_fen.h5')
rf = Roboflow(api_key="XwD4XNlX5B4Dq2zCLsYE")
project = rf.workspace().project("chessboard-detection-x5kxd")
model_detection = project.version(1).model


def resize_image(input_path, max_size=(800, 800)):
    """
    Resize the image to a maximum size.
    """
    image = Image.open(input_path)
    image.thumbnail(max_size, Image.ANTIALIAS)
    image.save(input_path)
    return image


def detect_chessboard(input_path, output_path):
    """
    Detect the chessboard using the Roboflow model and crop the detected area.
    """
    image = resize_image(input_path)

    # Perform object detection using the model
    json_data = model_detection.predict(input_path, confidence=40, overlap=30).json()

    # Extract bounding box coordinates
    x = json_data['predictions'][0]['x']
    y = json_data['predictions'][0]['y']
    w = json_data['predictions'][0]['width']
    h = json_data['predictions'][0]['height']

    # Crop the resized image
    cropped_image = image.crop((int(x - w / 2), int(y - h / 2), int(x + w / 2), int(y + h / 2)))
    cropped_image.convert('RGB').save(output_path)


def apply_padding(input_path, output_path, padding_size=30):
    """
    Apply padding to an image.
    """
    try:
        # Open the input image
        img = Image.open(input_path).convert("RGB")

        # Add padding to the image
        padded_img = ImageOps.expand(img, border=padding_size, fill='black')

        # Save the padded image
        padded_img.save(output_path)
        return True
    except Exception as e:
        print("Error applying padding to the image:", e)
        return False


def fen_from_onehot(one_hot):
    """
    Convert one-hot encoded predictions to FEN notation.
    """
    piece_symbols = 'prbnkqPRBNKQ'
    output = ''
    for i in range(64):
        j = np.argmax(one_hot[i])
        output += '1' if j == 12 else piece_symbols[j]
        if (i + 1) % 8 == 0:
            output += '-'

    compressed_fen = output[:-1]
    expanded_fen = []
    for char in compressed_fen:
        if char.isdigit() and '2' <= char <= '8':
            con = ord(char) - ord('0')
            expanded_fen.extend('1' for _ in range(con))
        else:
            expanded_fen.append(char)
    return ''.join(expanded_fen)


def preprocess_image(img_path):
    """
    Preprocess the image to feed into the CNN model.
    """
    try:
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"Error loading image at path: {img_path}")

        # Convert and resize the image
        image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        gray_image = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        gray_image = cv2.resize(gray_image, (400, 400))

        # Normalize the image
        gray_image = (gray_image - np.min(gray_image)) / (np.max(gray_image) - np.min(gray_image))

        # Split image into 8x8 grid and reshape for the model
        squares = [gray_image[i*50:(i+1)*50, j*50:(j+1)*50] for i in range(8) for j in range(8)]
        return np.array(squares).reshape(-1, 50, 50, 1)
    except Exception as e:
        print(f"Error processing image {img_path}: {e}")
        return None


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/camera/', methods=['GET', 'POST'])
def camera():
    """
    Route to handle chessboard detection from a camera upload.
    """
    print("Camera route triggered")
    input_path = "temp.png"
    output_path = "crop.jpg"

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({'error': 'No selected file'})

        file.save(input_path)

        # Apply padding to the image
        if not apply_padding(input_path, input_path):
            return jsonify({'error': 'Error applying padding to the image'})

        try:
            detect_chessboard(input_path, output_path)
        except Exception as e:
            print("Chessboard detection error:", e)
            detect_chessboard(input_path, output_path)  # Fallback to YOLO model
        
        preprocessed_image = preprocess_image(output_path)
        if preprocessed_image is None:
            return jsonify({'error': 'Error processing image for model input'})

        fen_prediction = model.predict(preprocessed_image)
        fen = fen_from_onehot(fen_prediction).replace('-', '/')
        print("FEN:", fen)
        return jsonify({'fen': fen})

    return jsonify({'message': 'Welcome to the Chessboard Detection API'})


@app.route('/screenshot/', methods=['GET', 'POST'])
def screen_shot():
    """
    Route to handle chessboard detection from a screenshot upload.
    """
    print("Screenshot route triggered")
    input_path = "temp.png"
    output_path = "crop.jpg"

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            return jsonify({'error': 'No selected file'})

        file.save(input_path)
        detect_chessboard(input_path, output_path)

        preprocessed_image = preprocess_image(output_path)
        if preprocessed_image is None:
            return jsonify({'error': 'Error processing image for model input'})

        fen_prediction = model.predict(preprocessed_image)
        fen = fen_from_onehot(fen_prediction).replace('-', '/')
        print("FEN:", fen)
        return jsonify({'fen': fen})

    return jsonify({'message': 'Welcome to the Chessboard Detection API'})


if __name__ == "__main__":
    app.run(debug=True, port=27777)
