import io
import base64
import os
import uuid
from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from . import hide_bp
from extensions import db
from models.db_models import History
from services.deep_stego_service import process_deep_encode, secret_text_to_bytes, secret_image_to_bytes, secret_3d_to_bytes
from services.cover_3d import embed_in_3d, is_3d_file
from PIL import Image
SUPPORTED_IMAGE_FORMATS = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}
SUPPORTED_3D_FORMATS = {'obj', 'npy', 'npz', 'bin', 'ply', 'stl', 'glb', 'fbx'}
SECRET_IMAGE_FORMATS = {'png', 'jpg', 'jpeg', 'bmp'}


def get_file_extension(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


@hide_bp.route('/')
@login_required
def hide_page():
    return render_template('hide.html')


@hide_bp.route('/process', methods=['POST'])
@login_required
def process_hiding_request():
    try:
        cover_file = request.files.get('cover_image')
        password = request.form.get('password', '').strip()
        secret_type = request.form.get('secret_type', 'text')
        cover_mode = request.form.get('cover_mode', 'Universal')
        if not cover_file or not cover_file.filename:
            return (jsonify({'error': 'Please select a cover file first.'}), 400)
        if len(password) < 4:
            return (jsonify({'error': 'For security, use a password with at least 4 characters.'}), 400)
        ext = get_file_extension(cover_file.filename)
        is_3d = ext in SUPPORTED_3D_FORMATS
        is_img = ext in SUPPORTED_IMAGE_FORMATS
        if not is_3d and (not is_img):
            return (jsonify({'error': f'Format .{ext} is not supported. Try PNG, JPG, or standard 3D files.'}), 400)
        cover_bytes = cover_file.read()
        if secret_type == 'text':
            text = request.form.get('secret_text', '').strip()
            if not text:
                return (jsonify({'error': 'You forgot to enter the secret text!'}), 400)
            secret_data = secret_text_to_bytes(text)
        elif secret_type == 'image':
            img_file = request.files.get('secret_image')
            if not img_file or get_file_extension(img_file.filename) not in SECRET_IMAGE_FORMATS:
                return (jsonify({'error': 'Please upload a valid image to hide.'}), 400)
            secret_data = secret_image_to_bytes(img_file.stream)
        elif secret_type == '3d':
            file_3d = request.files.get('secret_3d')
            if not file_3d:
                return (jsonify({'error': 'Please upload the 3D file you wish to hide.'}), 400)
            secret_data = secret_3d_to_bytes(
                file_3d.stream, ext=get_file_extension(file_3d.filename))
        else:
            return (jsonify({'error': 'Unknown secret type requested.'}), 400)

        def format_size(num_bytes):
            if num_bytes < 1024:
                return f'{num_bytes} B'
            elif num_bytes < 1048576:
                return f'{num_bytes / 1024:.2f} KB'
            else:
                return f'{num_bytes / 1048576:.2f} MB'
        cover_size_str = format_size(len(cover_bytes))
        secret_size_str = format_size(len(secret_data))
        output_filename = f'stego_{uuid.uuid4()}_{cover_file.filename}'
        tmp_dir = os.path.join(current_app.static_folder, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)
        file_path = os.path.join(tmp_dir, output_filename)
        (psnr, ssim, robustness) = (None, None, None)
        if is_img:
            input_image = Image.open(io.BytesIO(cover_bytes))
            (stego_img, psnr, ssim, extra_data) = process_deep_encode(
                input_image, secret_data, password)
            final_path = os.path.splitext(file_path)[0] + '.png'
            final_filename = os.path.basename(final_path)
            stego_img.save(final_path, format='PNG')
            if extra_data:
                with open(final_path, 'ab') as f:
                    f.write(extra_data)
            robustness = ssim * 100
            result = {
                'success': True,
                'cover_type': 'image',
                'stego_image': f'/static/tmp/{final_filename}',
                'stego_filename': f'stego_{os.path.splitext(cover_file.filename)[0]}.png',
                'psnr': f'{psnr:.2f}' if psnr else 'N/A',
                'ssim': f'{ssim:.4f}' if ssim else 'N/A',
                'robustness': f'{robustness:.1f}%',
                'model_used': f'{cover_mode} Neural Engine',
                'secret_type': secret_type,
                'cover_size': cover_size_str,
                'secret_size': secret_size_str
            }
        else:
            stego_3d_bytes = embed_in_3d(
                cover_bytes, secret_data, password, cover_file.filename)
            with open(file_path, 'wb') as f:
                f.write(stego_3d_bytes)
            result = {
                'success': True,
                'cover_type': '3d',
                'stego_3d_url': f'/static/tmp/{output_filename}',
                'stego_filename': f'stego_{cover_file.filename}',
                'stego_ext': ext,
                'model_used': f'3D Geometry AI ({ext.upper()})',
                'secret_type': secret_type,
                'cover_size': cover_size_str,
                'secret_size': secret_size_str
            }
        new_history_entry = History(user_id=current_user.id, operation='hide', file_name=cover_file.filename, model_used=result.get(
            'model_used', 'Unknown'), psnr_value=psnr, robustness_score=robustness, result_type=secret_type)
        db.session.add(new_history_entry)
        db.session.commit()
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (jsonify({'error': f'Something went wrong during processing: {str(e)}'}), 500)
