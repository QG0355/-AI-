import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..db import db
from ..db.models import FoodItem, FoodCategory, User

foods_bp = Blueprint('foods', __name__)


def _is_admin(user_id):
    u = User.query.get(user_id)
    return u and u.user_type == 'admin'


@foods_bp.route('/categories', methods=['GET'])
def list_categories():
    cats = FoodCategory.query.all()
    return jsonify([c.to_dict() for c in cats])


@foods_bp.route('/categories', methods=['POST'])
@jwt_required()
def add_category():
    uid = int(get_jwt_identity())
    if not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'msg': '分类名不能为空'}), 400
    if FoodCategory.query.filter_by(name=name).first():
        return jsonify({'msg': '分类已存在'}), 400
    c = FoodCategory(name=name)
    db.session.add(c)
    db.session.commit()
    return jsonify(c.to_dict()), 201


@foods_bp.route('/categories/<int:cid>', methods=['PUT'])
@jwt_required()
def update_category(cid):
    uid = int(get_jwt_identity())
    if not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403
    c = FoodCategory.query.get_or_404(cid)
    name = request.json.get('name', '').strip()
    if not name:
        return jsonify({'msg': '分类名不能为空'}), 400
    c.name = name
    db.session.commit()
    return jsonify(c.to_dict())


@foods_bp.route('/categories/<int:cid>', methods=['DELETE'])
@jwt_required()
def del_category(cid):
    uid = int(get_jwt_identity())
    if not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403
    c = FoodCategory.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'msg': '删除成功'})


@foods_bp.route('/foods', methods=['GET'])
def list_foods():
    keyword = request.args.get('keyword', '').strip()
    cat_id = request.args.get('category_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)
    recommend = request.args.get('recommend', '')

    q = FoodItem.query
    if keyword:
        q = q.filter(FoodItem.name.like(f'%{keyword}%'))
    if cat_id:
        q = q.filter_by(category_id=cat_id)
    if recommend:
        q = q.order_by(FoodItem.nutrition_score.desc(), FoodItem.click_count.desc())
    else:
        q = q.order_by(FoodItem.id.asc())

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            'items': [f.to_dict() for f in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
        }
    )


@foods_bp.route('/foods/<int:fid>', methods=['GET'])
def get_food(fid):
    food = FoodItem.query.get_or_404(fid)
    food.click_count += 1
    db.session.commit()
    return jsonify(food.to_dict())


@foods_bp.route('/foods', methods=['POST'])
@jwt_required()
def add_food():
    uid = int(get_jwt_identity())
    d = request.json or {}
    operator = User.query.get(uid)

    food = FoodItem(
        name=d.get('name', ''),
        category_id=d.get('category_id'),
        cooking_method=d.get('cooking_method', ''),
        ingredients=d.get('ingredients', ''),
        nutrition_score=d.get('nutrition_score', 5),
        calories=d.get('calories', 0),
        protein=d.get('protein', 0),
        fat=d.get('fat', 0),
        carb=d.get('carb', 0),
        fiber=d.get('fiber', 0),
        sodium=d.get('sodium', 0),
        image_url=d.get('image_url', ''),
        description=d.get('description', ''),
        preparation_process=d.get('preparation_process', ''),
        added_by=operator.username if operator else 'user',
    )
    db.session.add(food)
    db.session.commit()
    return jsonify(food.to_dict()), 201


@foods_bp.route('/foods/<int:fid>', methods=['PUT'])
@jwt_required()
def update_food(fid):
    uid = int(get_jwt_identity())
    food = FoodItem.query.get_or_404(fid)
    operator = User.query.get(uid)

    if not _is_admin(uid) and food.added_by != operator.username:
        return jsonify({'msg': '只能修改自己添加的食品'}), 403

    d = request.json or {}
    for field in (
        'name',
        'category_id',
        'cooking_method',
        'ingredients',
        'nutrition_score',
        'calories',
        'protein',
        'fat',
        'carb',
        'fiber',
        'sodium',
        'image_url',
        'description',
        'preparation_process',
    ):
        if field in d:
            setattr(food, field, d[field])
    db.session.commit()
    return jsonify(food.to_dict())


@foods_bp.route('/foods/<int:fid>', methods=['DELETE'])
@jwt_required()
def del_food(fid):
    uid = int(get_jwt_identity())
    food = FoodItem.query.get_or_404(fid)
    operator = User.query.get(uid)

    if not _is_admin(uid) and food.added_by != operator.username:
        return jsonify({'msg': '只能删除自己添加的食品'}), 403

    db.session.delete(food)
    db.session.commit()
    return jsonify({'msg': '删除成功'})


@foods_bp.route('/my-foods', methods=['GET'])
@jwt_required()
def list_my_foods():
    uid = int(get_jwt_identity())
    operator = User.query.get(uid)
    if not operator:
        return jsonify({'items': [], 'total': 0})

    keyword = request.args.get('keyword', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    q = FoodItem.query.filter_by(added_by=operator.username)
    if keyword:
        q = q.filter(FoodItem.name.like(f'%{keyword}%'))

    pagination = q.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(
        {
            'items': [f.to_dict() for f in pagination.items],
            'total': pagination.total,
            'pages': pagination.pages,
            'page': page,
        }
    )


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@foods_bp.route('/upload-food-image', methods=['POST'])
@jwt_required()
def upload_food_image():
    uid = int(get_jwt_identity())
    if not _is_admin(uid):
        return jsonify({'msg': '无权限'}), 403

    if 'file' not in request.files:
        return jsonify({'msg': '未选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'msg': '未选择文件'}), 400

    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f'{uuid.uuid4().hex}.{ext}'
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return jsonify({'url': f'/uploads/{filename}'})

    return jsonify({'msg': '不支持的文件格式'}), 400

