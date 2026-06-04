from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone
import random
import string

from ..db import db
from ..db.models import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'msg': '账号和密码不能为空'}), 400

    user = User.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({'msg': '账号或密码错误'}), 401

    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()})


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    email = data.get('email', '').strip()

    if not username or not password:
        return jsonify({'msg': '账号和密码不能为空'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'msg': '账号已存在'}), 409

    user = User(username=username, password=password, email=email)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({'token': token, 'user': user.to_dict()}), 201


@auth_bp.route('/send-code', methods=['POST'])
def send_verification_code():
    data = request.get_json() or {}
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'msg': '账号不能为空'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'msg': '账号不存在'}), 404

    code = ''.join(random.choices(string.digits, k=6))
    user.verification_code = code
    user.verification_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.commit()

    return jsonify({'msg': '验证码已发送', 'code': code, 'hint': '演示模式下验证码将显示在响应中'})


@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '').strip()

    if not username or not code or not new_password:
        return jsonify({'msg': '参数不完整'}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({'msg': '账号不存在'}), 404

    if not user.verification_code or user.verification_code != code:
        return jsonify({'msg': '验证码错误'}), 400

    if user.verification_expires:
        expires_at = user.verification_expires
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return jsonify({'msg': '验证码已过期'}), 400

    user.password = new_password
    user.verification_code = ''
    user.verification_expires = None
    db.session.commit()

    return jsonify({'msg': '密码重置成功'})


@auth_bp.route('/change-password', methods=['PUT'])
@jwt_required()
def change_password():
    uid = int(get_jwt_identity())
    data = request.get_json() or {}
    old_password = data.get('old_password', '').strip()
    new_password = data.get('new_password', '').strip()

    if not old_password or not new_password:
        return jsonify({'msg': '密码不能为空'}), 400

    user = User.query.get(uid)
    if not user:
        return jsonify({'msg': '用户不存在'}), 404

    if user.password != old_password:
        return jsonify({'msg': '原密码错误'}), 400

    user.password = new_password
    db.session.commit()

    return jsonify({'msg': '密码修改成功'})

