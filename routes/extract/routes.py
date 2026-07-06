import io
import os
import uuid
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from . import extract_bp
from extensions import db
from models.db_models import History
from services.deep_stego_service import process_deep_decode, bytes_to_secret
from services.cover_3d import extract_from_3d
from PIL import Image
VALID_IMAGE_STEGO = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}
VALID_3D_STEGO = {'obj', 'npy', 'npz', 'bin', 'ply', 'stl', 'glb', 'fbx'}


def get_extension(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


@extract_bp.route('/')
@login_required
def extract_page():
    return render_template('extract.html')


@extract_bp.route('/process', methods=['POST'])
@login_required
def process_extraction():
    try:
        stego_file = request.files.get('stego_image')
        password = request.form.get('password', '').strip()
        if not stego_file or not stego_file.filename:
            return (jsonify({'error': 'Please upload a file to extract from.'}), 400)
        if not password:
            return (jsonify({'error': 'A password is required to unlock the data.'}), 400)
        ext = get_extension(stego_file.filename)
        stego_bytes = stego_file.read()
        if ext in VALID_3D_STEGO:
            raw_secret_bytes = extract_from_3d(
                stego_bytes, password, stego_file.filename)
            model_name = '3D Vertex Decoder'
        elif ext in VALID_IMAGE_STEGO:
            stego_img = Image.open(io.BytesIO(stego_bytes))
            raw_secret_bytes = process_deep_decode(
                stego_img, password, stego_bytes)
            model_name = 'Neural AI U-Net Decoder'
        else:
            return (jsonify({'error': f'The format .{ext} is not supported. Use PNG, JPG, JPEG or supported 3D formats.'}), 400)
        result = bytes_to_secret(raw_secret_bytes)
        if 'raw_bytes' in result:
            file_id = str(uuid.uuid4())
            file_name = f"extracted_{file_id}.{result.get('ext', 'bin')}"
            tmp_path = os.path.join(
                current_app.static_folder, 'tmp', file_name)
            os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
            with open(tmp_path, 'wb') as f:
                f.write(result['raw_bytes'])
            result['download_url'] = f'/static/tmp/{file_name}'
            del result['raw_bytes']
            if 'data' in result:
                del result['data']
            if result['type'] == 'image' and len(result.get('content', '')) > 2 * 1024 * 1024:
                result['content'] = result['download_url']
        log_entry = History(user_id=current_user.id, operation='extract', file_name=stego_file.filename,
                            model_used=model_name, result_type=result.get('type', 'Unknown'))
        db.session.add(log_entry)
        db.session.commit()
        return jsonify({'success': True, 'result': result})
    except ValueError as e:
        return (jsonify({'error': str(e)}), 400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (jsonify({'error': 'Extraction failed. The file might be corrupted or the password incorrect.'}), 400)
