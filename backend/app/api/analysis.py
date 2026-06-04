import os
import uuid
import json
import threading

from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..db import db
from ..db.models import User, AnalysisRecord
from ..cache import set_task, get_task, delete_task
from ..models.preprocess import preprocess_image
from ..models.food_classifier import classify_food
from ..models.ingredient_inference import infer_ingredients
from ..models.portion_estimator import estimate_portion
from ..models.nutrition_calculator import calculate_nutrition

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload():
    if 'image' not in request.files:
        return jsonify({'msg': '未上传图片'}), 400

    file = request.files['image']
    if not file.filename:
        return jsonify({'msg': '文件名无效'}), 400

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('jpg', 'jpeg', 'png', 'webp', 'gif'):
        return jsonify({'msg': '仅支持 jpg/png/webp 格式'}), 400

    text_description = request.form.get('text_description', '')
    ingredients_hint = request.form.get('ingredients_hint', '')
    cooking_method_hint = request.form.get('cooking_method_hint', '')
    portion_hint = request.form.get('portion_hint', '')
    food_name = request.form.get('food_name', '')

    task_id = uuid.uuid4().hex[:12]
    upload_dir = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
    os.makedirs(upload_dir, exist_ok=True)

    filename = f'{task_id}.{ext}'
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)

    user_id = int(get_jwt_identity())
    set_task(task_id, {'status': 'processing'})

    thread = threading.Thread(
        target=_run_pipeline,
        args=(
            task_id,
            filepath,
            f'/uploads/{filename}',
            user_id,
            current_app._get_current_object(),
            text_description,
            ingredients_hint,
            cooking_method_hint,
            portion_hint,
            food_name,
        ),
        daemon=True,
    )
    thread.start()

    return jsonify({'task_id': task_id})


def _run_pipeline(
    task_id: str,
    filepath: str,
    image_url: str,
    user_id: int,
    app,
    text_description: str = '',
    ingredients_hint: str = '',
    cooking_method_hint: str = '',
    portion_hint: str = '',
    food_name: str = '',
):
    with app.app_context():
        try:
            user = User.query.get(user_id)
            health_goal = user.health_goal if user else '减重'

            preprocess_image(filepath)

            top3 = classify_food(filepath)
            if food_name.strip():
                confidence = 0.95
                top3 = [{'food': food_name.strip(), 'confidence': confidence}] + top3[1:]
            else:
                food_name = top3[0]['food']
                confidence = top3[0]['confidence']

            ingredients = infer_ingredients(food_name)

            if ingredients_hint:
                ingredients = list(
                    set(ingredients + [x.strip() for x in ingredients_hint.split(',') if x.strip()])
                )

            portion_info = estimate_portion(filepath, food_name)

            if portion_hint:
                try:
                    portion_info['grams'] = float(portion_hint)
                except:
                    pass

            if cooking_method_hint:
                portion_info['cooking_method'] = cooking_method_hint

            nutrition_result = calculate_nutrition(food_name, portion_info, health_goal)

            set_task(
                task_id,
                {
                    'status': 'done',
                    'food': food_name,
                    'confidence': confidence,
                    'top3': top3,
                    'ingredients': ingredients,
                    'portion': portion_info,
                    'nutrients': nutrition_result['nutrients'],
                    'per_100g': nutrition_result['per_100g'],
                    'dri': nutrition_result['dri'],
                    'suggestions': nutrition_result['suggestions'],
                    'data_source': nutrition_result['data_source'],
                    'image_url': image_url,
                    'user_id': user_id,
                    'text_description': text_description,
                },
            )
        except Exception as e:
            set_task(task_id, {'status': 'error', 'msg': str(e)})


@analysis_bp.route('/analyze', methods=['GET'])
@jwt_required()
def get_result():
    task_id = request.args.get('task_id', '')
    task = get_task(task_id) if task_id else None
    if task is None:
        return jsonify({'msg': '任务不存在'}), 404
    return jsonify(task)


@analysis_bp.route('/save', methods=['POST'])
@jwt_required()
def save_record():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    task_id = data.get('task_id', '')

    task = get_task(task_id) if task_id else None
    if task is None:
        return jsonify({'msg': '任务不存在'}), 404

    if task.get('status') != 'done':
        return jsonify({'msg': '分析尚未完成'}), 400

    nutrients = task['nutrients']
    portion_info = task.get('portion', {})
    portion_g = data.get('portion_g') or portion_info.get('grams', 100)
    record = AnalysisRecord(
        user_id=user_id,
        image_url=task.get('image_url'),
        food_name=task.get('food'),
        calories=nutrients.get('calories', 0),
        protein=nutrients.get('protein', 0),
        fat=nutrients.get('fat', 0),
        carb=nutrients.get('carb', 0),
        fiber=nutrients.get('fiber', 0),
        sodium=nutrients.get('sodium', 0),
        portion_g=portion_g,
        ingredients=json.dumps(task.get('ingredients', []), ensure_ascii=False),
        suggestions=json.dumps(task.get('suggestions', []), ensure_ascii=False),
    )
    db.session.add(record)
    db.session.commit()

    delete_task(task_id)

    return jsonify({'msg': '保存成功', 'record_id': record.id})


@analysis_bp.route('/export-pdf', methods=['POST'])
@jwt_required()
def export_pdf():
    from ..utils.pdf_generator import generate_nutrition_pdf
    import io

    data = request.get_json() or {}

    task_id = data.get('task_id')
    task = get_task(task_id) if task_id else None
    if task is not None:
        if task.get('status') != 'done':
            return jsonify({'msg': '分析尚未完成'}), 400
        pdf_data = {
            'food': task.get('food'),
            'confidence': task.get('confidence', 0),
            'nutrients': task.get('nutrients', {}),
            'suggestions': task.get('suggestions', []),
            'health_goal': task.get('health_goal', '均衡饮食'),
            'date': data.get('date'),
        }
    else:
        pdf_data = {
            'food': data.get('food', '未知食物'),
            'confidence': data.get('confidence', 0),
            'nutrients': data.get('nutrients', {}),
            'suggestions': data.get('suggestions', []),
            'health_goal': data.get('health_goal', '均衡饮食'),
            'date': data.get('date'),
        }

    try:
        pdf_bytes = generate_nutrition_pdf(pdf_data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"营养报告_{pdf_data['food']}.pdf",
        )
    except Exception as e:
        return jsonify({'msg': f'PDF 生成失败: {str(e)}'}), 500


@analysis_bp.route('/batch-upload', methods=['POST'])
@jwt_required()
def batch_upload():
    if 'images' not in request.files:
        return jsonify({'msg': '未上传图片'}), 400

    files = request.files.getlist('images')
    if not files or len(files) == 0:
        return jsonify({'msg': '未上传图片'}), 400

    if len(files) > 10:
        return jsonify({'msg': '最多支持同时上传10张图片'}), 400

    user_id = int(get_jwt_identity())
    task_ids = []

    for i, file in enumerate(files):
        if not file.filename:
            continue

        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else 'jpg'
        if ext not in ('jpg', 'jpeg', 'png', 'webp', 'gif'):
            continue

        text_description = request.form.get(f'text_description_{i}', '')
        ingredients_hint = request.form.get(f'ingredients_hint_{i}', '')
        cooking_method_hint = request.form.get(f'cooking_method_hint_{i}', '')
        portion_hint = request.form.get(f'portion_hint_{i}', '')
        food_name = request.form.get(f'food_name_{i}', '')

        task_id = uuid.uuid4().hex[:12]
        upload_dir = os.path.abspath(current_app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_dir, exist_ok=True)

        filename = f'{task_id}.{ext}'
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        set_task(task_id, {'status': 'processing'})

        thread = threading.Thread(
            target=_run_pipeline,
            args=(
                task_id,
                filepath,
                f'/uploads/{filename}',
                user_id,
                current_app._get_current_object(),
                text_description,
                ingredients_hint,
                cooking_method_hint,
                portion_hint,
                food_name,
            ),
            daemon=True,
        )
        thread.start()
        task_ids.append({'index': i, 'task_id': task_id, 'filename': file.filename})

    return jsonify({'msg': f'已提交 {len(task_ids)} 个任务', 'tasks': task_ids})


@analysis_bp.route('/batch-results', methods=['GET'])
@jwt_required()
def get_batch_results():
    task_ids_str = request.args.get('task_ids', '')
    if not task_ids_str:
        return jsonify({'msg': '缺少task_ids参数'}), 400

    task_ids = task_ids_str.split(',')
    results = []

    for tid in task_ids:
        tid = tid.strip()
        task = get_task(tid) if tid else None
        if task:
            results.append(
                {
                    'task_id': tid,
                    'status': task.get('status'),
                    'data': task if task.get('status') == 'done' else None,
                }
            )
        else:
            results.append({'task_id': tid, 'status': 'not_found', 'data': None})

    return jsonify({'results': results})

