from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import cv2
import torch
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image
import numpy as np
from base64 import b64decode
from io import BytesIO
import pandas as pd
from datetime import datetime
import os
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from pyngrok import ngrok

app = Flask(__name__)
app.secret_key = ''

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
faces_df = pd.read_excel(data_file)
names = faces_df['Name'].tolist()

# Ensure paths are constructed correctly
image_folder = 'images'  # Adjust this path if your images are in a different directory
image_paths = [os.path.join(image_folder, path) for path in faces_df['Image_Path'].tolist()]

# Load images and compute embeddings
embeddings = []
for path in image_paths:
    img = Image.open(path)
    img_cropped = mtcnn(img)
    if img_cropped is not None:
        emb = resnet(img_cropped.unsqueeze(0).to(device)).detach()
        embeddings.append(emb)

# Data directory and file setup
data_dir = 'attendance'
if not os.path.exists(data_dir):
    os.makedirs(data_dir)
data_file = os.path.join(data_dir, 'attendance.xlsx')

# Initialize data structure and load existing data if available
try:
    df = pd.read_excel(data_file, index_col=None)
except FileNotFoundError:
    df = pd.DataFrame(columns=['Name', 'Date', 'Count', 'First Seen Time', 'Last Seen Time'])

def save_to_excel():
    df.to_excel(data_file, index=False)

def update_dataframe(name):
    today = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%H:%M:%S')
    if ((df['Name'] == name) & (df['Date'] == today)).any():
        df.loc[(df['Name'] == name) & (df['Date'] == today), 'Count'] += 1
        df.loc[(df['Name'] == name) & (df['Date'] == today), 'Last Seen Time'] = current_time
    else:
        df.loc[len(df)] = [name, today, 1, current_time, current_time]
    save_to_excel()

@app.route('/process_image', methods=['POST'])
def process_image():
    if not session.get('verified'):
        return jsonify({"message": "Unauthorized access"}), 401

    data = request.json['image']
    # Decode the image data
    header, encoded = data.split(",", 1)
    binary_data = b64decode(encoded)
    image = Image.open(BytesIO(binary_data))

    # Process the image
    img_cropped = mtcnn(image)
    if img_cropped is not None:
        captured_emb = resnet(img_cropped.unsqueeze(0).to(device)).detach()
        distances = [torch.nn.functional.cosine_similarity(captured_emb, emb) for emb in embeddings]
        max_distance = max(distances)
        if max_distance > 0.5:
            matched_index = distances.index(max_distance)
            name = names[matched_index]
            update_dataframe(name)
            return jsonify({"match": name, "confidence": max_distance.item(), "date": datetime.now().strftime('%Y-%m-%d')})
    return jsonify({"message": "No matching face found"})

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        qr_code = request.form['code']
        response = requests.post(API_URL, headers=API_HEADERS, json={"QR": qr_code})

        if response.status_code == 200:
            api_response = response.json()
            if api_response.get('FID'):
                session['verified'] = True
                return redirect(url_for('face_recognition'))
            else:
                return render_template('index.html', error='Invalid QR code or unauthorized access')
        else:
            return render_template('index.html', error='Failed to verify QR code')

    return render_template('index.html')

@app.route('/face_recognition')
def face_recognition():
    if not session.get('verified'):
        return redirect(url_for('index'))
    return render_template('face_recognition.html')

if __name__ == '__main__':
    # Setup ngrok
    ngrok.set_auth_token("")
    public_url = ngrok.connect(5000)
    print(f" * ngrok tunnel \"{public_url}\" -> \"http://127.0.0.1:5000\"")
    app.run()
