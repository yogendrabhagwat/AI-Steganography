from flask import render_template, jsonify
from flask_login import login_required, current_user
from . import history_bp
from models.db_models import History


@history_bp.route('/')
@login_required
def history_page():
    records = History.query.filter_by(user_id=current_user.id).order_by(
        History.timestamp.desc()).limit(100).all()
    return render_template('history.html', records=records)


@history_bp.route('/delete/<int:record_id>', methods=['POST'])
@login_required
def delete_record(record_id):
    from extensions import db
    record = History.query.filter_by(
        id=record_id, user_id=current_user.id).first()
    if record:
        db.session.delete(record)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Record not found'}), 404


@history_bp.route('/clear', methods=['POST'])
@login_required
def clear_history():
    from extensions import db
    History.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return jsonify({'success': True})


@history_bp.route('/download')
@login_required
def download_history():
    import csv
    import io
    from flask import Response
    records = History.query.filter_by(user_id=current_user.id).order_by(
        History.timestamp.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Operation', 'File Name', 'Model Used',
                    'PSNR (dB)', 'Type', 'Timestamp'])
    for r in records:
        writer.writerow([r.operation.upper(), r.file_name, r.model_used,
                        f"{r.psnr_value:.2f}" if r.psnr_value else 'N/A', r.result_type, r.timestamp.strftime('%Y-%m-%d %H:%M')])
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=steganography_history.csv'})


@history_bp.route('/api')
@login_required
def history_api():
    records = History.query.filter_by(user_id=current_user.id).order_by(
        History.timestamp.desc()).limit(100).all()
    data = [
        {
            'id': r.id,
            'operation': r.operation,
            'file_name': r.file_name,
            'model_used': r.model_used,
            'psnr_value': r.psnr_value,
            'robustness_score': r.robustness_score,
            'result_type': r.result_type,
            'timestamp': r.timestamp.strftime('%Y-%m-%d %H:%M')
        }
        for r in records
    ]
    return jsonify(data)
