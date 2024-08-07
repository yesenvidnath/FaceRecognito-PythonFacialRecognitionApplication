
# FaceLib: Face Analysis Application with QR Code Authentication

## Overview

This application uses the FaceLib library for face detection, facial expression analysis, age and gender estimation, and face recognition with PyTorch. It incorporates a QR code scanning feature for authentication before starting the face recognition process.

## Features

- Face Detection
- Face Alignment
- Age & Gender Estimation
- Facial Expression Recognition
- Face Recognition
- QR Code Authentication for Access Control

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/your-repo/facelib-app.git
    ```

2. Navigate to the project directory:
    ```bash
    cd facelib-app
    ```

3. Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\\Scripts\\activate`
    ```

4. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Set up the face images and embeddings:
    - Place the face images in the `images` directory.
    - Ensure the `faces.xlsx` file in the `faces` directory contains the names and paths to the images.

2. Run the Flask application:
    ```bash
    python app.py
    ```

3. Use ngrok to expose your local server to the internet:
    ```bash
    ngrok http 5000
    ```

## QR Code Authentication

The application uses a QR code for authentication. The QR code is scanned using the device's camera, and the scanned code is sent to an API for verification. If the QR code is valid, the user is allowed to proceed to the face recognition process.

## API Details

- **URL**: `https://api.northstar.mv/api/gym-access/qr`
- **Method**: `POST`
- **Headers**:
    ```json
    {
        "Authorization": "Bearer aBcDeFgHiJkLmNoP"
    }
    ```
- **Body**:
    ```json
    {
        "QR": "94:3v3vs94g6lus"
    }
    ```

## File Structure

- `app.py`: Main application file.
- `templates/`: Contains the HTML templates.
    - `index.html`: QR code scanning and authentication page.
    - `face_recognition.html`: Face recognition page.
- `faces/`: Contains the `faces.xlsx` file with names and image paths.
- `images/`: Directory to store face images.
- `attendance/`: Directory to store attendance records.

## HTML5-QRCode Library

The application uses the `html5-qrcode` library for QR code scanning. The camera view is responsive, and users can switch between cameras on mobile devices.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.

## Acknowledgments
- [OpenCV](https://opencv.org/)
- [Dlib](http://dlib.net/)
- [Face Recognition Library](https://github.com/ageitgey/face_recognition)
