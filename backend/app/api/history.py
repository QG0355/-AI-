from datetime import datetime, timedelta
import csv
from io import StringIO

from flask import Blueprint, request, jsonify, make_response, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..db.models import AnalysisRecord, DietRecord

history_bp = Blueprint('history', __name__)


@history_bp.route('/history', methods=['GET'])
@jwt_required()
def get_history():
    user_id = int(get_jwt_identity())
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = AnalysisRecord.query.filter_by(user_id=user_id)

    if start_date:
        query = query.filter(AnalysisRecord.created_at >= start_date)
    if end_date:
        query = query.filter(AnalysisRecord.created_at <= end_date + ' 23:59:59')

    records = query.order_by(AnalysisRecord.created_at.desc()).limit(100).all()
    return jsonify([r.to_dict() for r in records])


@history_bp.route('/history/trend', methods=['GET'])
@jwt_required()
def get_trend():
    user_id = int(get_jwt_identity())
    period = request.args.get('period', 'week')

    now = datetime.now()
    delta_map = {'day': timedelta(days=1), 'week': timedelta(weeks=1), 'month': timedelta(days=30)}
    start = now - delta_map.get(period, timedelta(weeks=1))

    records = (
        AnalysisRecord.query.filter(AnalysisRecord.user_id == user_id, AnalysisRecord.created_at >= start)
        .order_by(AnalysisRecord.created_at.asc())
        .all()
    )

    daily: dict = {}
    for r in records:
        key = r.created_at.strftime('%Y-%m-%d') if r.created_at else ''
        if key not in daily:
            daily[key] = {'date': key, 'calories': 0, 'protein': 0, 'fat': 0, 'carb': 0, 'count': 0}
        daily[key]['calories'] = round(daily[key]['calories'] + (r.calories or 0), 1)
        daily[key]['protein'] = round(daily[key]['protein'] + (r.protein or 0), 1)
        daily[key]['fat'] = round(daily[key]['fat'] + (r.fat or 0), 1)
        daily[key]['carb'] = round(daily[key]['carb'] + (r.carb or 0), 1)
        daily[key]['count'] += 1

    return jsonify(list(daily.values()))


@history_bp.route('/history/export', methods=['GET'])
@jwt_required()
def export_records():
    user_id = int(get_jwt_identity())
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    export_type = request.args.get('type', 'all')

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(['记录类型', '食物名称', '餐次', '分量(g)', '热量(kcal)', '蛋白质(g)', '脂肪(g)', '碳水(g)', '日期'])

    if export_type in ('all', 'analysis'):
        query = AnalysisRecord.query.filter_by(user_id=user_id)
        if start_date:
            query = query.filter(AnalysisRecord.created_at >= start_date)
        if end_date:
            query = query.filter(AnalysisRecord.created_at <= end_date + ' 23:59:59')
        analysis_records = query.order_by(AnalysisRecord.created_at.desc()).limit(500).all()
        for r in analysis_records:
            writer.writerow(
                [
                    '分析记录',
                    r.food_name,
                    '',
                    r.portion_g or '',
                    r.calories or 0,
                    r.protein or 0,
                    r.fat or 0,
                    r.carb or 0,
                    r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '',
                ]
            )

    if export_type in ('all', 'diet'):
        query = DietRecord.query.filter_by(user_id=user_id)
        if start_date:
            query = query.filter(DietRecord.record_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
        if end_date:
            query = query.filter(DietRecord.record_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
        diet_records = query.order_by(DietRecord.record_date.desc(), DietRecord.created_at.desc()).limit(500).all()
        for r in diet_records:
            writer.writerow(
                [
                    '饮食记录',
                    r.food_name,
                    r.meal_type or '',
                    r.portion_g or '',
                    r.calories or 0,
                    r.protein or 0,
                    r.fat or 0,
                    r.carb or 0,
                    r.record_date.strftime('%Y-%m-%d') if r.record_date else '',
                ]
            )

    output.seek(0)
    csv_content = output.getvalue()
    csv_content = '\ufeff' + csv_content
    response = make_response(csv_content.encode('utf-8'))
    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename=饮食记录_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    return response


@history_bp.route('/history/export-pdf', methods=['GET'])
@jwt_required()
def export_diet_pdf():
    from ..utils.pdf_generator import generate_diet_record_pdf
    import io

    user_id = int(get_jwt_identity())
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = DietRecord.query.filter_by(user_id=user_id)
    if start_date:
        query = query.filter(DietRecord.record_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(DietRecord.record_date <= datetime.strptime(end_date, '%Y-%m-%d').date())

    diet_records = query.order_by(DietRecord.record_date.desc(), DietRecord.created_at.desc()).limit(500).all()

    records = []
    total_calories = 0
    total_protein = 0
    total_fat = 0
    total_carb = 0

    for r in diet_records:
        records.append(
            {
                'food_name': r.food_name,
                'meal_type': r.meal_type or '',
                'portion_g': r.portion_g or 0,
                'calories': r.calories or 0,
                'protein': r.protein or 0,
                'fat': r.fat or 0,
                'carb': r.carb or 0,
                'record_date': r.record_date.strftime('%Y-%m-%d') if r.record_date else '',
                'record_time': r.created_at.strftime('%H:%M') if r.created_at else '',
            }
        )
        total_calories += r.calories or 0
        total_protein += r.protein or 0
        total_fat += r.fat or 0
        total_carb += r.carb or 0

    user_name = '未知用户'
    try:
        from ..db.models import User

        u = User.query.get(user_id)
        user_name = u.username if u else user_name
    except:
        pass

    date_range = f'{start_date or "开始"} - {end_date or "结束"}'

    pdf_data = {
        'records': records,
        'summary': {
            'calories': round(total_calories, 1),
            'protein': round(total_protein, 1),
            'fat': round(total_fat, 1),
            'carb': round(total_carb, 1),
        },
        'date_range': date_range,
        'user_name': user_name,
    }

    try:
        pdf_bytes = generate_diet_record_pdf(pdf_data)
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'饮食记录_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
        )
    except Exception as e:
        return jsonify({'msg': f'PDF 生成失败: {str(e)}'}), 500


@history_bp.route('/history/quick-add', methods=['POST'])
@jwt_required()
def quick_add_from_history():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}

    record_ids = data.get('record_ids', [])
    record_type = data.get('record_type', 'analysis')
    meal_type = data.get('meal_type', '午餐')
    portion_g = float(data.get('portion_g', 100))
    record_date = data.get('record_date', datetime.now().date().isoformat())

    if not record_ids:
        return jsonify({'msg': '请选择要添加的记录'}), 400

    from ..db import db
    from ..db.models import DietRecord

    added = 0
    for rid in record_ids:
        if record_type == 'analysis':
            analysis_record = AnalysisRecord.query.get(rid)
            if analysis_record and analysis_record.user_id == user_id:
                r = DietRecord(
                    user_id=user_id,
                    food_name=analysis_record.food_name,
                    image_url=analysis_record.image_url,
                    meal_type=meal_type,
                    portion_g=portion_g,
                    calories=analysis_record.calories,
                    protein=analysis_record.protein,
                    fat=analysis_record.fat,
                    carb=analysis_record.carb,
                    record_date=datetime.strptime(record_date, '%Y-%m-%d').date(),
                )
                db.session.add(r)
                added += 1

    db.session.commit()
    return jsonify({'msg': f'成功添加 {added} 条到饮食记录', 'added': added}), 201

