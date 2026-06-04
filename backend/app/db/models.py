import json
from datetime import datetime, timezone
from . import db


class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), default='')
    real_name = db.Column(db.String(50), default='')
    phone = db.Column(db.String(20), default='')
    gender = db.Column(db.Enum('男', '女', '保密'), default='保密')
    age = db.Column(db.Integer, default=0)
    avatar_url = db.Column(db.String(255), default='')
    full_photo = db.Column(db.String(255), default='')
    member_level = db.Column(db.String(20), default='普通会员')
    user_type = db.Column(db.Enum('admin', 'user'), default='user')
    health_goal = db.Column(db.Enum('减重', '增肌', '控糖', '均衡'), default='均衡')
    daily_calorie_target = db.Column(db.Integer, default=2000)
    weight_kg = db.Column(db.Float, default=0)
    height_cm = db.Column(db.Float, default=0)
    activity_level = db.Column(db.String(20), default='轻度')
    verification_code = db.Column(db.String(10), default='')
    verification_expires = db.Column(db.DateTime, default=None)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    diet_records = db.relationship('DietRecord', backref='user', lazy=True)
    analysis_records = db.relationship('AnalysisRecord', backref='user', lazy=True)
    nutrition_assessments = db.relationship('NutritionAssessment', backref='user', lazy=True)

    @property
    def bmi(self):
        if self.height_cm and self.weight_kg:
            h = self.height_cm / 100
            return round(self.weight_kg / (h * h), 1)
        return 0

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'real_name': self.real_name,
            'phone': self.phone,
            'gender': self.gender,
            'age': self.age,
            'avatar_url': self.avatar_url,
            'full_photo': self.full_photo,
            'member_level': self.member_level,
            'user_type': self.user_type,
            'health_goal': self.health_goal,
            'daily_calorie_target': self.daily_calorie_target,
            'weight_kg': self.weight_kg,
            'height_cm': self.height_cm,
            'activity_level': self.activity_level,
            'bmi': self.bmi,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else '',
        }


class FoodCategory(db.Model):
    __tablename__ = 'food_category'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    food_items = db.relationship('FoodItem', backref='category', lazy=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}


class FoodItem(db.Model):
    __tablename__ = 'food_item'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('food_category.id'))
    cooking_method = db.Column(db.String(50), default='')
    ingredients = db.Column(db.Text, default='')
    nutrition_score = db.Column(db.Integer, default=5)
    calories = db.Column(db.Float, default=0)
    protein = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    carb = db.Column(db.Float, default=0)
    fiber = db.Column(db.Float, default=0)
    sodium = db.Column(db.Float, default=0)
    image_url = db.Column(db.String(255), default='')
    description = db.Column(db.Text, default='')
    preparation_process = db.Column(db.Text, default='')
    click_count = db.Column(db.Integer, default=0)
    added_by = db.Column(db.String(50), default='admin')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    diet_records = db.relationship('DietRecord', backref='food_item', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else '',
            'cooking_method': self.cooking_method,
            'ingredients': self.ingredients,
            'nutrition_score': self.nutrition_score,
            'calories': self.calories,
            'protein': self.protein,
            'fat': self.fat,
            'carb': self.carb,
            'fiber': self.fiber,
            'sodium': self.sodium,
            'image_url': self.image_url,
            'description': self.description,
            'preparation_process': self.preparation_process,
            'click_count': self.click_count,
            'added_by': self.added_by,
            'created_at': self.created_at.strftime('%Y-%m-%d') if self.created_at else '',
        }


class DietRecord(db.Model):
    __tablename__ = 'diet_record'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('food_item.id'))
    food_name = db.Column(db.String(100), default='')
    image_url = db.Column(db.String(255), default='')
    meal_type = db.Column(db.Enum('早餐', '午餐', '晚餐', '加餐'), default='午餐')
    portion_g = db.Column(db.Float, default=100)
    calories = db.Column(db.Float, default=0)
    protein = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    carb = db.Column(db.Float, default=0)
    fiber = db.Column(db.Float, default=0)
    sodium = db.Column(db.Float, default=0)
    record_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'food_id': self.food_id,
            'food_name': self.food_name,
            'image_url': self.image_url,
            'meal_type': self.meal_type,
            'portion_g': self.portion_g,
            'calories': self.calories,
            'protein': self.protein,
            'fat': self.fat,
            'carb': self.carb,
            'fiber': self.fiber,
            'sodium': self.sodium,
            'record_date': self.record_date.strftime('%Y-%m-%d') if self.record_date else '',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
        }


class NutritionAssessment(db.Model):
    __tablename__ = 'nutrition_assessment'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    weight_kg = db.Column(db.Float, default=0)
    height_cm = db.Column(db.Float, default=0)
    bmi = db.Column(db.Float, default=0)
    assessment_date = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())
    status = db.Column(db.String(20), default='正常')
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else '',
            'real_name': self.user.real_name if self.user else '',
            'avatar_url': self.user.avatar_url if self.user else '',
            'weight_kg': self.weight_kg,
            'height_cm': self.height_cm,
            'bmi': self.bmi,
            'assessment_date': self.assessment_date.strftime('%Y-%m-%d') if self.assessment_date else '',
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
        }


class AnalysisRecord(db.Model):
    __tablename__ = 'analysis_record'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    image_url = db.Column(db.String(255))
    food_name = db.Column(db.String(100))
    calories = db.Column(db.Float, default=0)
    protein = db.Column(db.Float, default=0)
    fat = db.Column(db.Float, default=0)
    carb = db.Column(db.Float, default=0)
    fiber = db.Column(db.Float, default=0)
    sodium = db.Column(db.Float, default=0)
    ingredients = db.Column(db.Text)
    suggestions = db.Column(db.Text)
    portion_g = db.Column(db.Float, default=100)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'food_name': self.food_name,
            'calories': self.calories,
            'protein': self.protein,
            'fat': self.fat,
            'carb': self.carb,
            'fiber': self.fiber,
            'sodium': self.sodium,
            'portion_g': self.portion_g,
            'ingredients': json.loads(self.ingredients) if self.ingredients else [],
            'suggestions': json.loads(self.suggestions) if self.suggestions else [],
            'image_url': self.image_url,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else '',
            'date': self.created_at.strftime('%Y-%m-%d') if self.created_at else '',
        }

