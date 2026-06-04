import os
import threading

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from .config import Config
from .db import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, resources={r'/api/*': {'origins': '*'}})
    JWTManager(app)
    db.init_app(app)

    from .cache import init_redis
    init_redis(app)

    from .api.auth import auth_bp
    from .api.analysis import analysis_bp
    from .api.history import history_bp
    from .api.foods import foods_bp
    from .api.users import users_bp
    from .api.diet import diet_bp
    from .api.assess import assess_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(analysis_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/api')
    app.register_blueprint(foods_bp, url_prefix='/api')
    app.register_blueprint(users_bp, url_prefix='/api')
    app.register_blueprint(diet_bp, url_prefix='/api')
    app.register_blueprint(assess_bp, url_prefix='/api')

    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        upload_dir = os.path.abspath(app.config['UPLOAD_FOLDER'])
        return send_from_directory(upload_dir, filename)

    with app.app_context():
        if os.environ.get('RESET_DB', 'false').lower() == 'true':
            db.drop_all()
        db.create_all()
        _seed_data()

    def _preload_model():
        try:
            from .models.food_classifier import _load_clip_model
            _load_clip_model()
        except Exception:
            pass

    threading.Thread(target=_preload_model, daemon=True).start()

    return app


def _seed_data():
    from .db.models import User, FoodCategory, FoodItem

    if not User.query.filter_by(username='admin').first():
        db.session.add(
            User(
                username='admin',
                password='<REDACTED>',
                user_type='admin',
                health_goal='均衡',
                daily_calorie_target=2000,
                gender='男',
                age=30,
            )
        )
        db.session.commit()

    categories = ['炒菜', '汤类', '主食', '小吃', '水果', '沙拉', '西餐', '饮品']
    for cname in categories:
        if not FoodCategory.query.filter_by(name=cname).first():
            db.session.add(FoodCategory(name=cname))
    db.session.commit()

    if not FoodItem.query.filter_by(name='番茄炒鸡蛋').first():
        cat = FoodCategory.query.filter_by(name='炒菜').first()
        db.session.add(
            FoodItem(
                name='番茄炒鸡蛋',
                category_id=cat.id if cat else None,
                cooking_method='炒',
                ingredients='西红柿,鸡蛋,葱',
                nutrition_score=9,
                calories=95,
                protein=6.8,
                fat=5.5,
                carb=7.2,
                fiber=1.2,
                sodium=380,
                image_url='/images/foods/tomato_egg.jpg',
                description='家常经典菜，营养丰富，酸甜可口，老少皆宜。',
                added_by='admin',
            )
        )
        db.session.commit()

