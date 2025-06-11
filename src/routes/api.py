from flask import Blueprint, request, jsonify, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from src.extensions import db
from src.models.product import Product, ReferenceImage

api_bp = Blueprint("api", __name__, url_prefix="/api")

# Configurações para upload de arquivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "products")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@api_bp.route("/products", methods=["GET"])
def get_products():
    """Retorna a lista de produtos em formato JSON"""
    products = db.session.query(Product).all()
    result = []
    
    for product in products:
        # Encontrar a imagem principal, se existir
        primary_image = None
        for img in product.reference_images:
            if img.is_primary:
                primary_image = img.path
                break
        
        result.append({
            "id": product.id,
            "code": product.code,
            "name": product.name,
            "description": product.description,
            "active": product.active,
            "primary_image": primary_image,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None
        })
    
    return jsonify({"products": result})

@api_bp.route("/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    """Retorna os detalhes de um produto específico em formato JSON"""
    product = db.session.query(Product).get_or_404(product_id)
    
    # Preparar lista de imagens
    images = []
    for img in product.reference_images:
        images.append({
            "id": img.id,
            "path": img.path,
            "is_primary": img.is_primary,
            "created_at": img.created_at.isoformat() if img.created_at else None
        })
    
    # Preparar lista de inspeções
    inspections = []
    for insp in product.inspections:
        inspections.append({
            "id": insp.id,
            "image_path": insp.image_path,
            "result_image_path": insp.result_image_path,
            "approved": insp.approved,
            "defects_count": insp.defects_count,
            "defects_details": insp.defects_details,
            "created_at": insp.created_at.isoformat() if insp.created_at else None
        })
    
    result = {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "description": product.description,
        "active": product.active,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
        "images": images,
        "inspections": inspections
    }
    
    return jsonify(result)

@api_bp.route("/products/<int:product_id>/images", methods=["POST"])
def upload_image(product_id):
    """API para upload de imagem de referência para um produto"""
    try:
        product = db.session.query(Product).get_or_404(product_id)
        
        # Verificar se há arquivo na requisição
        if "image" not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400
        
        file = request.files["image"]
        
        if not file or not file.filename:
            return jsonify({"error": "Nenhum arquivo selecionado"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Tipo de arquivo não permitido. Use apenas JPG, PNG ou GIF"}), 400
        
        # Gerar nome único para o arquivo
        filename = str(uuid.uuid4()) + "." + file.filename.rsplit(".", 1)[1].lower()
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Salvar arquivo
        file.save(filepath)
        
        # Verificar se deve ser a imagem principal
        is_primary = request.form.get("is_primary", "false").lower() == "true"
        
        # Se for definida como principal, atualizar as outras imagens
        if is_primary:
            for image in product.reference_images:
                image.is_primary = False
        
        # Se não houver outras imagens, tornar esta a principal independentemente da escolha
        if not product.reference_images:
            is_primary = True
        
        # Criar registro de imagem de referência
        image = ReferenceImage(
            product_id=product_id,
            path=f"images/products/{filename}",
            is_primary=is_primary
        )
        
        db.session.add(image)
        db.session.commit()
        
        return jsonify({
            "message": "Imagem de referência adicionada com sucesso",
            "image": {
                "id": image.id,
                "path": image.path,
                "is_primary": image.is_primary,
                "created_at": image.created_at.isoformat() if image.created_at else None
            }
        }), 201
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao adicionar imagem: {str(e)}")
        return jsonify({"error": f"Erro ao adicionar imagem: {str(e)}"}), 500

@api_bp.route("/products/<int:product_id>/images/<int:image_id>", methods=["DELETE"])
def delete_image(product_id, image_id):
    """API para excluir uma imagem de referência"""
    try:
        product = db.session.query(Product).get_or_404(product_id)
        image = db.session.query(ReferenceImage).get_or_404(image_id)
        
        # Verificar se a imagem pertence ao produto
        if image.product_id != product_id:
            return jsonify({"error": "Imagem não pertence a este produto"}), 400
        
        # Verificar se é a única imagem
        if len(product.reference_images) == 1:
            return jsonify({"error": "Não é possível excluir a única imagem de referência do produto"}), 400
        
        # Se for a imagem principal, definir outra como principal
        if image.is_primary and len(product.reference_images) > 1:
            # Encontrar outra imagem para ser a principal
            for other_image in product.reference_images:
                if other_image.id != image_id:
                    other_image.is_primary = True
                    break
        
        # Tentar excluir arquivo físico
        try:
            file_path = os.path.join(current_app.static_folder, image.path)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            current_app.logger.error(f"Erro ao excluir arquivo de imagem: {str(e)}")
        
        # Excluir registro da imagem
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({"message": "Imagem de referência excluída com sucesso"}), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao excluir imagem: {str(e)}")
        return jsonify({"error": f"Erro ao excluir imagem: {str(e)}"}), 500

@api_bp.route("/products/<int:product_id>/images/<int:image_id>/set-primary", methods=["PUT"])
def set_primary_image(product_id, image_id):
    """API para definir uma imagem como principal"""
    try:
        product = db.session.query(Product).get_or_404(product_id)
        image = db.session.query(ReferenceImage).get_or_404(image_id)
        
        # Verificar se a imagem pertence ao produto
        if image.product_id != product_id:
            return jsonify({"error": "Imagem não pertence a este produto"}), 400
        
        # Atualizar todas as imagens do produto
        for img in product.reference_images:
            img.is_primary = (img.id == image_id)
        
        db.session.commit()
        
        return jsonify({"message": "Imagem principal definida com sucesso"}), 200
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao definir imagem principal: {str(e)}")
        return jsonify({"error": f"Erro ao definir imagem principal: {str(e)}"}), 500

