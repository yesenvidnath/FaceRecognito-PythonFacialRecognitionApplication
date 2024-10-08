from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image, ImageOps
import numpy as np
from base64 import b64decode
from io import BytesIO
import pandas as pd
from datetime import datetime
import os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from pyngrok import ngrok
import logging

app = Flask(__name__)
app.secret_key = '2jnO19ZhRu0XgZhaSSj3pUaYFqC_4NgVXQ7tDETn1gEUjXqu6'

# Set up logging
logging.basicConfig(level=logging.INFO)

# API details
API_URL = "https://api.northstar.mv/api/gym-access/qr"
API_HEADERS = {
    "Authorization": "Bearer aBcDeFgHiJkLmNoP"
}

# Initialize the models
device = 'cuda' if torch.cuda.is_available() else 'cpu'
mtcnn = MTCNN(image_size=160, margin=0, min_face_size=20, thresholds=[0.6, 0.7, 0.7], factor=0.709, post_process=True, device=device)
resnet = InceptionResnetV1(pretrained='vggface2').eval().to(device)

# Load names and image paths from Excel
data_dir = 'faces'
data_file = os.path.join(data_dir, 'faces.xlsx')

# Ensure the images directory exists
image_folder = 'images'
if not os.path.exists(image_folder):
    os.makedirs(image_folder)

def load_faces_df():
    try:
        return pd.read_excel(data_file)
    except FileNotFoundError:
        return pd.DataFrame(columns=['Name', 'Image_Path'])

@app.route('/process_image', methods=['POST'])
def process_image():
    if not session.get('verified'):
        return jsonify({"message": "Unauthorized access"}), 401

    try:
        data = request.json['image']
        # Decode the image data
        header, encoded = data.split(",", 1)
        binary_data = b64decode(encoded)
        image = Image.open(BytesIO(binary_data))

        # Process the image
        img_cropped = mtcnn(image)
        if img_cropped is not None:
            captured_emb = resnet(img_cropped.unsqueeze(0).to(device)).detach()
            faces_df = load_faces_df()
            names = faces_df['Name'].tolist()
            embeddings = []
            for path in faces_df['Image_Path']:
                img = Image.open(os.path.join(image_folder, path))
                img_cropped = mtcnn(img)
                if img_cropped is not None:
                    emb = resnet(img_cropped.unsqueeze(0).to(device)).detach()
                    embeddings.append(emb)
            distances = [torch.nn.functional.cosine_similarity(captured_emb, emb) for emb in embeddings]
            max_distance = max(distances)
            if max_distance > 0.5:
                matched_index = distances.index(max_distance)
                name = names[matched_index]
                return jsonify({"match": name, "confidence": max_distance.item(), "date": datetime.now().strftime('%Y-%m-%d')})
        return jsonify({"message": "No matching face found"})
    except Exception as e:
        logging.error(f"Error in process_image: {e}")
        return jsonify({"message": "Internal server error"}), 500

@app.route('/take_photo', methods=['GET', 'POST'])
def take_photo():
    if request.method == 'POST':
        try:
            data = request.json['image']
            # Decode the image data
            header, encoded = data.split(",", 1)
            binary_data = b64decode(encoded)
            image = Image.open(BytesIO(binary_data))

            # Resize while maintaining aspect ratio and pad to make square
            desired_size = max(image.size)
            image = ImageOps.pad(image, (desired_size, desired_size), color=(0, 0, 0))

            # Save the image with a unique name
            photo_count = len(os.listdir(image_folder))
            new_image_name = f"{photo_count + 1:04d}.jpg"  # Adding 1 to ensure a unique name
            image.save(os.path.join(image_folder, new_image_name))

            # Load the Excel file again to avoid potential conflicts
            faces_df = load_faces_df()

            # Update faces.xlsx
            new_row = pd.DataFrame({'Name': [photo_count + 1], 'Image_Path': [new_image_name]})
            faces_df = pd.concat([faces_df, new_row], ignore_index=True)
            faces_df.to_excel(data_file, index=False)  # Save the DataFrame to Excel

            # Set session as verified
            session['verified'] = True

            return jsonify({"message": "Photo taken and saved", "image_name": new_image_name})
        except Exception as e:
            logging.error(f"Error in take_photo: {e}")
            return jsonify({"message": "Internal server error"}), 500

    return render_template('take_photo.html')

@app.route('/direct_face_recognition')
def direct_face_recognition():
    # Directly redirect to face recognition without QR scanning
    session['verified'] = True  # Assuming direct recognition should skip any verification
    return redirect(url_for('face_recognition'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        qr_code = request.get_json().get('code')
        try:
            response = requests.post(API_URL, headers=API_HEADERS, json={"QR": qr_code})

            if response.status_code == 200:
                api_response = response.json()
                if api_response.get('QR') and api_response.get('FID'):
                    return jsonify({"redirect": url_for('take_photo')})
                elif api_response.get('QR') and not api_response.get('FID'):
                    session['verified'] = True
                    return jsonify({"redirect": url_for('face_recognition')})
                else:
                    return jsonify({"message": "Invalid QR code"})
            else:
                return jsonify({"message": "Failed to verify QR code"})
        except Exception as e:
            logging.error(f"Error in index: {e}")
            return jsonify({"message": "Internal server error"})

    return render_template('index.html')

@app.route('/qr_scan')
def qr_scan():
    # Render the QR scanning interface
    return render_template('qr_scan.html')

@app.route('/face_recognition')
def face_recognition():
    if not session.get('verified'):
        return redirect(url_for('index'))
    return render_template('face_recognition.html')

if __name__ == '__main__':
    # Setup ngrok
    ngrok.set_auth_token("2jnO19ZhRu0XgZhaSSj3pUaYFqC_4NgVXQ7tDETn1gEUjXqu6")
    public_url = ngrok.connect(5000)
    print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:5000\"")
    app.run()
