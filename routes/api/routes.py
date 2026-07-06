from flask import request, jsonify, current_app
from . import api_bp
from extensions import db
from models.db_models import User
from services.deep_stego_service import process_deep_encode, process_deep_decode, bytes_to_secret, secret_text_to_bytes
from services.encryption import encrypt_data, decrypt_data
import io
from PIL import Image


@api_bp.route('/ping', methods=['GET'])
def ping():
    """
    Check API Health Status
    ---
    tags:
      - System
    responses:
      "200":
        description: "API is healthy"
        schema:
          type: object
          properties:
            status:
              type: string
              example: "ok"
            version:
              type: string
              example: "v1.0.0-research"
    """
    return jsonify({'status': 'ok', 'version': 'v1.0.0-research'})


@api_bp.route('/encode', methods=['POST'])
@api_bp.route('/hide/text', methods=['POST'])
def api_encode():
    """
    Encode secret text into an image
    ---
    tags:
      - Steganography
    consumes:
      - multipart/form-data
    parameters:
      - name: cover_image
        in: formData
        type: file
        required: true
        description: The image file to hide data inside
      - name: secret_text
        in: formData
        type: string
        required: true
        description: The text you want to hide
      - name: password
        in: formData
        type: string
        required: true
        description: Encryption password
    responses:
      "200":
        description: "Returns a JSON with success metrics"
      "400":
        description: "Missing parameters"
      "500":
        description: "Internal server error"
    """
    if 'cover_image' not in request.files or 'secret_text' not in request.form or 'password' not in request.form:
        return (jsonify({'error': 'Missing parameters. Required: cover_image, secret_text, password'}), 400)
    cover_file = request.files['cover_image']
    secret_text = request.form['secret_text']
    password = request.form['password']
    if not cover_file.filename:
        return (jsonify({'error': 'No selected file'}), 400)
    try:
        img = Image.open(cover_file.stream).convert('RGB')
        payload_bytes = secret_text_to_bytes(secret_text)
        encrypted_payload = encrypt_data(payload_bytes, password)
        (stego_img, psnr_db, ssim_val, appended_data) = process_deep_encode(
            img, encrypted_payload, password)
        out_buf = io.BytesIO()
        stego_img.save(out_buf, format='PNG', optimize=False)
        if appended_data:
            out_buf.write(appended_data)
        out_bytes = out_buf.getvalue()
        out_buf.seek(0)
        return jsonify({'status': 'success', 'message': 'Data hidden successfully', 'metrics': {'psnr': psnr_db, 'ssim': ssim_val}, 'image_size': out_buf.getbuffer().nbytes})
    except Exception as e:
        return (jsonify({'error': str(e)}), 500)


@api_bp.route('/decode', methods=['POST'])
@api_bp.route('/extract', methods=['POST'])
def api_decode():
    """
    Extract secret data from a stego image
    ---
    tags:
      - Steganography
    consumes:
      - multipart/form-data
    parameters:
      - name: stego_image
        in: formData
        type: file
        required: true
        description: The stego image containing hidden data
      - name: password
        in: formData
        type: string
        required: true
        description: Decryption password
    responses:
      "200":
        description: "Successfully extracted secret text"
        schema:
          type: object
          properties:
            status:
              type: string
            extracted_data:
              type: object
      "400":
        description: "Extraction failed or missing parameters"
    """
    if 'stego_image' not in request.files or 'password' not in request.form:
        return (jsonify({'error': 'Missing parameters. Required: stego_image, password'}), 400)
    stego_file = request.files['stego_image']
    password = request.form['password']
    try:
        stego_bytes = stego_file.read()
        stego_img = Image.open(io.BytesIO(stego_bytes)).convert('RGB')
        secret_bytes = process_deep_decode(stego_img, password, stego_bytes)
        secret_data = bytes_to_secret(secret_bytes)
        return jsonify({'status': 'success', 'extracted_data': secret_data})
    except Exception as e:
        return (jsonify({'error': str(e)}), 400)
