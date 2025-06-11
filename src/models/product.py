from datetime import datetime
from src.extensions import db

class Product(db.Model):
    """Modelo para produtos (PCIs de LED)"""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    reference_images = db.relationship("ReferenceImage", backref="product", lazy=True, cascade="all, delete-orphan")
    inspections = db.relationship("Inspection", backref="product", lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product {self.code}: {self.name}>"

class ReferenceImage(db.Model):
    """Modelo para imagens de referência dos produtos"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ReferenceImage {self.id} for Product {self.product_id}>"

class Inspection(db.Model):
    """Modelo para inspeções realizadas"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    result_image_path = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, nullable=False)
    defects_count = db.Column(db.Integer, default=0)
    defects_details = db.Column(db.Text)  # JSON serializado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Inspection {self.id} for Product {self.product_id}: {'APPROVED' if self.approved else 'REJECTED'}>"

