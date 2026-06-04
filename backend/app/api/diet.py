from datetime import date, datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..db import db
from ..db.models import DietRecord, FoodItem, User

diet_bp = Blueprint('diet', __name__)


@diet_bp.route('/diet-records', methods=['GET'])
@jwt_required()
def list_records():
    uid = int(get_jwt_identity())
    date_str = request.args.get('date', date.today().isoformat())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    try:
        record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        record_date = date.today()

    q = DietRecord.query.filter_by(user_id=uid, record_date=record_date)
    q = q.order_by(DietRecord.created_at.desc())
    pagination = q.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({'items': [r.to_dict() for r in pagination.items], 'total': pagination.total, 'date': record_date.isoformat()})


VALID_MEAL_TYPES = ('早餐', '午餐', '晚餐', '加餐')


@diet_bp.route('/diet-records', methods=['POST'])
@jwt_required()
def add_record():
    uid = int(get_jwt_identity())
    d = request.json or {}

    food_id = d.get('food_id')
    food_name = d.get('food_name', '')
    portion_g_val = d.get('portion_g')
    portion_g = float(portion_g_val) if portion_g_val not in (None, '', 0) else 100
    meal_type = d.get('meal_type', '午餐')
    if meal_type not in VALID_MEAL_TYPES:
        meal_type = '午餐'
    image_url = d.get('image_url', '')

    calories = protein = fat = carb = fiber = sodium = 0
    if food_id:
        food = FoodItem.query.get(food_id)
        if food:
            ratio = portion_g / 100.0
            calories = round(food.calories * ratio, 1)
            protein = round(food.protein * ratio, 1)
            fat = round(food.fat * ratio, 1)
            carb = round(food.carb * ratio, 1)
            fiber = round(food.fiber * ratio, 1) if food.fiber else 0
            sodium = round(food.sodium * ratio, 1) if food.sodium else 0
            food_name = food_name or food.name
            image_url = image_url or food.image_url
    else:
        calories = float(d.get('calories', 0))
        protein = float(d.get('protein', 0))
        fat = float(d.get('fat', 0))
        carb = float(d.get('carb', 0))
        fiber = float(d.get('fiber', 0))
        sodium = float(d.get('sodium', 0))

    date_str = d.get('record_date', date.today().isoformat())
    record_date = datetime.strptime(date_str, '%Y-%m-%d').date()

    record_time = d.get('record_time')
    created_at = datetime.utcnow()
    if record_time:
        try:
            hour, minute = map(int, record_time.split(':'))
            created_at = datetime(record_date.year, record_date.month, record_date.day, hour, minute)
        except (ValueError, AttributeError):
            pass

    r = DietRecord(
        user_id=uid,
        food_id=food_id,
        food_name=food_name,
        image_url=image_url,
        meal_type=meal_type,
        portion_g=portion_g,
        calories=calories,
        protein=protein,
        fat=fat,
        carb=carb,
        fiber=fiber,
        sodium=sodium,
        record_date=record_date,
        created_at=created_at,
    )
    db.session.add(r)
    db.session.commit()
    return jsonify(r.to_dict()), 201


@diet_bp.route('/diet-records/<int:rid>', methods=['PUT'])
@jwt_required()
def update_record(rid):
    uid = int(get_jwt_identity())
    r = DietRecord.query.get_or_404(rid)
    if r.user_id != uid:
        return jsonify({'msg': '无权限'}), 403

    d = request.json or {}

    if 'food_name' in d:
        r.food_name = d['food_name']
    if 'portion_g' in d:
        r.portion_g = float(d['portion_g'])
    if 'meal_type' in d:
        if d['meal_type'] in VALID_MEAL_TYPES:
            r.meal_type = d['meal_type']
    if 'calories' in d:
        r.calories = float(d['calories'])
    if 'protein' in d:
        r.protein = float(d['protein'])
    if 'fat' in d:
        r.fat = float(d['fat'])
    if 'carb' in d:
        r.carb = float(d['carb'])
    if 'fiber' in d:
        r.fiber = float(d['fiber'])
    if 'sodium' in d:
        r.sodium = float(d['sodium'])

    if r.food_id and r.portion_g:
        food = FoodItem.query.get(r.food_id)
        if food:
            ratio = r.portion_g / 100.0
            r.calories = round(food.calories * ratio, 1)
            r.protein = round(food.protein * ratio, 1)
            r.fat = round(food.fat * ratio, 1)
            r.carb = round(food.carb * ratio, 1)
            r.fiber = round(food.fiber * ratio, 1) if food.fiber else 0
            r.sodium = round(food.sodium * ratio, 1) if food.sodium else 0

    db.session.commit()
    return jsonify(r.to_dict())


@diet_bp.route('/diet-records/<int:rid>', methods=['DELETE'])
@jwt_required()
def del_record(rid):
    uid = int(get_jwt_identity())
    r = DietRecord.query.get_or_404(rid)
    if r.user_id != uid:
        return jsonify({'msg': '无权限'}), 403
    db.session.delete(r)
    db.session.commit()
    return jsonify({'msg': '删除成功'})


@diet_bp.route('/diet-records/summary', methods=['GET'])
@jwt_required()
def daily_summary():
    uid = int(get_jwt_identity())
    date_str = request.args.get('date', date.today().isoformat())
    try:
        record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        record_date = date.today()

    rows = DietRecord.query.filter_by(user_id=uid, record_date=record_date).all()
    totals = {'calories': 0, 'protein': 0, 'fat': 0, 'carb': 0, 'fiber': 0, 'sodium': 0}
    by_meal = {}
    for r in rows:
        for k in totals:
            totals[k] = round(totals[k] + getattr(r, k), 1)
        meal = r.meal_type
        if meal not in by_meal:
            by_meal[meal] = {'calories': 0, 'items': []}
        by_meal[meal]['calories'] = round(by_meal[meal]['calories'] + r.calories, 1)
        by_meal[meal]['items'].append({'id': r.id, 'name': r.food_name, 'calories': r.calories, 'portion_g': r.portion_g, 'image_url': r.image_url})

    return jsonify({'date': record_date.isoformat(), 'totals': totals, 'by_meal': by_meal, 'count': len(rows)})


@diet_bp.route('/diet-records/batch', methods=['POST'])
@jwt_required()
def batch_add():
    uid = int(get_jwt_identity())
    d = request.json or {}
    records = d.get('records', [])

    if not records:
        return jsonify({'msg': '没有要添加的记录'}), 400

    added = []
    for rec in records:
        food_id = rec.get('food_id')
        food_name = rec.get('food_name', '')
        portion_g = float(rec.get('portion_g', 100))
        meal_type = rec.get('meal_type', '午餐')
        record_date_str = rec.get('record_date', date.today().isoformat())
        image_url = rec.get('image_url', '')

        calories = protein = fat = carb = fiber = sodium = 0
        if food_id:
            food = FoodItem.query.get(food_id)
            if food:
                ratio = portion_g / 100.0
                calories = round(food.calories * ratio, 1)
                protein = round(food.protein * ratio, 1)
                fat = round(food.fat * ratio, 1)
                carb = round(food.carb * ratio, 1)
                fiber = round(food.fiber * ratio, 1) if food.fiber else 0
                sodium = round(food.sodium * ratio, 1) if food.sodium else 0
                food_name = food_name or food.name
                image_url = image_url or food.image_url

        try:
            record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
        except ValueError:
            record_date = date.today()

        r = DietRecord(
            user_id=uid,
            food_id=food_id,
            food_name=food_name,
            image_url=image_url,
            meal_type=meal_type,
            portion_g=portion_g,
            calories=calories,
            protein=protein,
            fat=fat,
            carb=carb,
            fiber=fiber,
            sodium=sodium,
            record_date=record_date,
        )
        db.session.add(r)
        added.append(r)

    db.session.commit()
    return jsonify({'msg': f'成功添加 {len(added)} 条记录', 'added': len(added)}), 201


@diet_bp.route('/diet-records/suggestions', methods=['GET'])
@jwt_required()
def get_suggestions():
    uid = int(get_jwt_identity())
    date_str = request.args.get('date', date.today().isoformat())
    try:
        record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        record_date = date.today()

    user = User.query.get(uid)
    if not user:
        return jsonify({'msg': '用户不存在'}), 404

    rows = DietRecord.query.filter_by(user_id=uid, record_date=record_date).all()
    totals = {'calories': 0, 'protein': 0, 'fat': 0, 'carb': 0}
    for r in rows:
        totals['calories'] += r.calories
        totals['protein'] += r.protein
        totals['fat'] += r.fat
        totals['carb'] += r.carb

    suggestions = []
    calorie_target = user.daily_calorie_target or 2000
    calorie_diff = totals['calories'] - calorie_target

    if calorie_diff > 200:
        suggestions.append(f'今日热量已超出目标 {abs(round(calorie_diff, 1))} kcal，建议减少高脂肪食物的摄入')
    elif calorie_diff < -200:
        suggestions.append('今日热量摄入偏低，建议适当补充优质蛋白和健康脂肪')

    protein_ratio = totals['protein'] / (totals['carb'] + 0.01)
    if protein_ratio < 0.15:
        suggestions.append('蛋白质摄入不足，建议增加鱼、肉、豆类等高蛋白食物')

    if totals['fat'] / (totals['carb'] + 0.01) > 1.5:
        suggestions.append('脂肪摄入偏高，建议减少油炸食品和肥肉的摄入')

    if not suggestions:
        suggestions.append('今日饮食结构良好，继续保持！')

    return jsonify({'date': record_date.isoformat(), 'totals': totals, 'target': calorie_target, 'suggestions': suggestions, 'health_goal': user.health_goal})

