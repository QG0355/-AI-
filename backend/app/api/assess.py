from datetime import date, datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..db import db
from ..db.models import NutritionAssessment, User

assess_bp = Blueprint('assess', __name__)


def _bmi_status(bmi):
    if bmi < 18.5:
        return '偏瘦'
    if bmi < 24.0:
        return '正常'
    if bmi < 28.0:
        return '超重'
    return '肥胖'


@assess_bp.route('/assessments', methods=['GET'])
@jwt_required()
def list_assessments():
    uid = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    keyword = request.args.get('keyword', '').strip()

    u = User.query.get(uid)
    if u and u.user_type == 'admin':
        q = NutritionAssessment.query
        if keyword:
            q = q.join(User).filter((User.username.like(f'%{keyword}%')) | (User.real_name.like(f'%{keyword}%')))
    else:
        q = NutritionAssessment.query.filter_by(user_id=uid)

    q = q.order_by(NutritionAssessment.assessment_date.desc(), NutritionAssessment.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    from sqlalchemy import func

    count_map = {
        row.user_id: row.cnt
        for row in db.session.query(NutritionAssessment.user_id, func.count(NutritionAssessment.id).label('cnt'))
        .group_by(NutritionAssessment.user_id)
        .all()
    }

    items = []
    for a in pagination.items:
        d = a.to_dict()
        d['progress_days'] = count_map.get(a.user_id, 1)
        items.append(d)

    return jsonify({'items': items, 'total': pagination.total, 'pages': pagination.pages, 'page': page})


@assess_bp.route('/assessments/me', methods=['GET'])
@jwt_required()
def my_latest():
    uid = int(get_jwt_identity())
    a = NutritionAssessment.query.filter_by(user_id=uid).order_by(NutritionAssessment.assessment_date.desc()).first()
    if not a:
        return jsonify({})
    return jsonify(a.to_dict())


@assess_bp.route('/assessments', methods=['POST'])
@jwt_required()
def add_assessment():
    uid = int(get_jwt_identity())
    d = request.json or {}

    weight_kg = float(d.get('weight_kg', 0))
    height_cm = float(d.get('height_cm', 0))
    bmi = round(weight_kg / ((height_cm / 100) ** 2), 1) if height_cm else 0
    status = _bmi_status(bmi)

    date_str = d.get('assessment_date', date.today().isoformat())
    try:
        adate = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        adate = date.today()

    a = NutritionAssessment(
        user_id=uid,
        weight_kg=weight_kg,
        height_cm=height_cm,
        bmi=bmi,
        assessment_date=adate,
        status=status,
        notes=d.get('notes', ''),
    )
    db.session.add(a)

    u = User.query.get(uid)
    if u:
        u.weight_kg = weight_kg
        u.height_cm = height_cm

    db.session.commit()
    return jsonify(a.to_dict()), 201


@assess_bp.route('/assessments/<int:aid>', methods=['DELETE'])
@jwt_required()
def del_assessment(aid):
    uid = int(get_jwt_identity())
    a = NutritionAssessment.query.get_or_404(aid)
    u = User.query.get(uid)
    if a.user_id != uid and (not u or u.user_type != 'admin'):
        return jsonify({'msg': '无权限'}), 403
    db.session.delete(a)
    db.session.commit()
    return jsonify({'msg': '删除成功'})

