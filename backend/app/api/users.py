from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import uuid

from ..db import db
from ..db.models import User

users_bp = Blueprint('users', __name__)


def _is_admin(user_id):
    u = User.query.get(user_id)
    return u and u.user_type == 'admin'


@users_bp.route('/users', methods=['GET'])
@jwt_required()
def list_users():
    uid = int(get_jwt_identity())
    if not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403

    keyword = request.args.get('keyword', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    q = User.query
    if keyword:
        q = q.filter((User.username.like(f'%{keyword}%')) | (User.real_name.like(f'%{keyword}%')))
    q = q.order_by(User.id.asc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({'items': [u.to_dict() for u in pagination.items], 'total': pagination.total, 'pages': pagination.pages, 'page': page})


@users_bp.route('/users/<int:uid2>', methods=['GET'])
@jwt_required()
def get_user(uid2):
    uid = int(get_jwt_identity())
    if uid != uid2 and not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403
    u = User.query.get_or_404(uid2)
    return jsonify(u.to_dict())


@users_bp.route('/users/<int:uid2>', methods=['PUT'])
@jwt_required()
def update_user(uid2):
    uid = int(get_jwt_identity())
    if uid != uid2 and not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403
    u = User.query.get_or_404(uid2)
    d = request.json or {}
    for field in (
        'gender',
        'age',
        'avatar_url',
        'full_photo',
        'real_name',
        'phone',
        'health_goal',
        'daily_calorie_target',
        'weight_kg',
        'height_cm',
        'activity_level',
        'email',
    ):
        if field in d:
            setattr(u, field, d[field])
    if _is_admin(uid):
        if 'user_type' in d:
            u.user_type = d['user_type']
        if 'member_level' in d:
            u.member_level = d['member_level']
    db.session.commit()
    return jsonify(u.to_dict())


@users_bp.route('/users/<int:uid2>', methods=['DELETE'])
@jwt_required()
def del_user(uid2):
    uid = int(get_jwt_identity())
    if not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403
    u = User.query.get_or_404(uid2)
    from ..db.models import DietRecord, NutritionAssessment, AnalysisRecord

    DietRecord.query.filter_by(user_id=uid2).delete()
    NutritionAssessment.query.filter_by(user_id=uid2).delete()
    AnalysisRecord.query.filter_by(user_id=uid2).delete()
    db.session.delete(u)
    db.session.commit()
    return jsonify({'msg': '删除成功'})


@users_bp.route('/users/<int:uid2>/reset-password', methods=['PUT'])
@jwt_required()
def reset_password(uid2):
    uid = int(get_jwt_identity())
    if not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403
    u = User.query.get_or_404(uid2)
    new_pwd = request.json.get('password', '123456')
    u.password = new_pwd
    db.session.commit()
    return jsonify({'msg': '密码重置成功'})


@users_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    uid = int(get_jwt_identity())
    u = User.query.get_or_404(uid)
    return jsonify(u.to_dict())


@users_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    uid = int(get_jwt_identity())
    u = User.query.get_or_404(uid)
    d = request.json or {}
    for field in (
        'gender',
        'age',
        'avatar_url',
        'full_photo',
        'real_name',
        'phone',
        'health_goal',
        'daily_calorie_target',
        'weight_kg',
        'height_cm',
        'activity_level',
        'email',
    ):
        if field in d:
            setattr(u, field, d[field])
    if 'password' in d and d['password']:
        u.password = d['password']
    db.session.commit()
    return jsonify(u.to_dict())


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@users_bp.route('/upload-avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    uid = int(get_jwt_identity())
    if 'file' not in request.files:
        return jsonify({'msg': '未找到文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'msg': '未选择文件'}), 400
    if not allowed_file(file.filename):
        return jsonify({'msg': '不支持的文件格式'}), 400
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    avatar_folder = os.path.join(upload_folder, 'avatars')
    os.makedirs(avatar_folder, exist_ok=True)
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'avatar_{uid}_{uuid.uuid4().hex}.{ext}'
    filepath = os.path.join(avatar_folder, filename)
    file.save(filepath)
    return jsonify({'url': f'/uploads/avatars/{filename}'})


@users_bp.route('/upload-user-photo', methods=['POST'])
@jwt_required()
def upload_user_photo():
    uid = int(get_jwt_identity())
    if 'file' not in request.files:
        return jsonify({'msg': '未找到文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'msg': '未选择文件'}), 400
    if not allowed_file(file.filename):
        return jsonify({'msg': '不支持的文件格式'}), 400
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    photo_folder = os.path.join(upload_folder, 'user_photos')
    os.makedirs(photo_folder, exist_ok=True)
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f'photo_{uid}_{uuid.uuid4().hex}.{ext}'
    filepath = os.path.join(photo_folder, filename)
    file.save(filepath)
    return jsonify({'url': f'/uploads/user_photos/{filename}'})

