from flask import Blueprint, request, render_template, redirect, url_for, flash, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from src.extensions import db
from src.models.product import Product, ReferenceImage

products_bp = Blueprint("products", __name__, url_prefix="/products")

# Configurações para upload de arquivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "images", "products")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@products_bp.route("/")
def index():
    """Lista todos os produtos"""
    # Parâmetros de filtro
    search = request.args.get("search", "")
    status = request.args.get("status", "")
    
    # Consulta base
    query = db.session.query(Product)
    
    # Aplicar filtros
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%") | Product.code.ilike(f"%{search}%"))
    
    if status == "active":
        query = query.filter_by(active=True)
    elif status == "inactive":
        query = query.filter_by(active=False)
    
    # Ordenar por código
    query = query.order_by(Product.code)
    
    products = query.all()
    
    return render_template(
        "products/index.html",
        products=products,
        search=search,
        status=status
    )

@products_bp.route("/new")
def new():
    """Exibe formulário para criar novo produto"""
    return render_template("products/new.html")

@products_bp.route("/", methods=["POST"])
def create():
    """Cria um novo produto"""
    try:
        code = request.form.get("code")
        name = request.form.get("name")
        description = request.form.get("description", "")
        active = "active" in request.form
        
        # Verificar se código já existe
        existing_product = Product.query.filter_by(code=code).first()
        if existing_product:
            flash(f"Código {code} já está em uso por outro produto", "error")
            return redirect(url_for("products.new"))
        
        # Criar produto
        product = Product(
            code=code,
            name=name,
            description=description,
            active=active
        )
        
        db.session.add(product)
        db.session.commit()
        
        # Processar imagem de referência, se enviada
        if "reference_image" in request.files:
            file = request.files["reference_image"]
            if file and file.filename and allowed_file(file.filename):
                # Gerar nome único para o arquivo
                filename = str(uuid.uuid4()) + "." + file.filename.rsplit(".", 1)[1].lower()
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                # Salvar arquivo
                file.save(filepath)
                
                # Criar registro de imagem de referência
                image = ReferenceImage(
                    product_id=product.id,
                    path=f"images/products/{filename}",
                    is_primary=True
                )
                
                db.session.add(image)
                db.session.commit()
        
        flash(f"Produto {name} criado com sucesso!", "success")
        return redirect(url_for("products.show", id=product.id))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao criar produto: {str(e)}", "error")
        return redirect(url_for("products.new"))

@products_bp.route("/<int:id>")
def show(id):
    """Exibe detalhes de um produto específico"""
    product = db.session.query(Product).get_or_404(id)
    return render_template("products/show.html", product=product)

@products_bp.route("/<int:id>/edit")
def edit(id):
    """Exibe formulário para editar produto"""
    product = db.session.query(Product).get_or_404(id)
    return render_template("products/edit.html", product=product)

@products_bp.route("/<int:id>", methods=["POST"])
def update(id):
    """Atualiza um produto existente"""
    try:
        product = db.session.query(Product).get_or_404(id)
        
        code = request.form.get("code")
        name = request.form.get("name")
        description = request.form.get("description", "")
        active = "active" in request.form
        
        # Verificar se código já existe em outro produto
        existing_product = db.session.query(Product).filter_by(code=code).first()
        if existing_product and existing_product.id != id:
            flash(f"Código {code} já está em uso por outro produto", "error")
            return redirect(url_for("products.edit", id=id))
        
        # Atualizar produto
        product.code = code
        product.name = name
        product.description = description
        product.active = active
        
        # Processar imagem de referência, se enviada
        if "reference_image" in request.files:
            file = request.files["reference_image"]
            if file and file.filename and allowed_file(file.filename):
                # Gerar nome único para o arquivo
                filename = str(uuid.uuid4()) + "." + file.filename.rsplit(".", 1)[1].lower()
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                # Salvar arquivo
                file.save(filepath)
                
                # Verificar se já existe uma imagem principal
                primary_image = db.session.query(ReferenceImage).filter_by(product_id=id, is_primary=True).first()
                
                if primary_image:
                    # Atualizar caminho da imagem existente
                    primary_image.path = f"images/products/{filename}"
                else:
                    # Criar nova imagem de referência como principal
                    image = ReferenceImage(
                        product_id=id,
                        path=f"images/products/{filename}",
                        is_primary=True
                    )
                    db.session.add(image)
        
        db.session.commit()
        flash(f"Produto {name} atualizado com sucesso!", "success")
        return redirect(url_for("products.show", id=id))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao atualizar produto: {str(e)}", "error")
        return redirect(url_for("products.edit", id=id))

@products_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id):
    """Exclui um produto"""
    try:
        product = db.session.query(Product).get_or_404(id)
        name = product.name
        
        # Excluir imagens de referência
        for image in product.reference_images:
            # Tentar excluir arquivo físico
            try:
                file_path = os.path.join(current_app.static_folder, image.path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                current_app.logger.error(f"Erro ao excluir arquivo de imagem: {str(e)}")
        
        # Excluir produto (as imagens serão excluídas em cascata)
        db.session.delete(product)
        db.session.commit()
        
        flash(f"Produto {name} excluído com sucesso!", "success")
        return redirect(url_for("products.index"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao excluir produto: {str(e)}", "error")
        return redirect(url_for("products.show", id=id))

@products_bp.route("/<int:id>/add-image", methods=["POST"])
def add_image(id):
    """Adiciona uma nova imagem de referência ao produto"""
    try:
        product = db.session.query(Product).get_or_404(id)
        
        if "image" not in request.files:
            flash("Nenhum arquivo enviado", "error")
            return redirect(url_for("products.edit", id=id))
        
        file = request.files["image"]
        
        if not file or not file.filename:
            flash("Nenhum arquivo selecionado", "error")
            return redirect(url_for("products.edit", id=id))
        
        if not allowed_file(file.filename):
            flash("Tipo de arquivo não permitido. Use apenas JPG, PNG ou GIF", "error")
            return redirect(url_for("products.edit", id=id))
        
        # Gerar nome único para o arquivo
        filename = str(uuid.uuid4()) + "." + file.filename.rsplit(".", 1)[1].lower()
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Salvar arquivo
        file.save(filepath)
        
        # Verificar se deve ser a imagem principal
        is_primary = "is_primary" in request.form
        
        # Se for definida como principal, atualizar as outras imagens
        if is_primary:
            for image in product.reference_images:
                image.is_primary = False
        
        # Se não houver outras imagens, tornar esta a principal independentemente da escolha
        if not product.reference_images:
            is_primary = True
        
        # Criar registro de imagem de referência
        image = ReferenceImage(
            product_id=id,
            path=f"images/products/{filename}",
            is_primary=is_primary
        )
        
        db.session.add(image)
        db.session.commit()
        
        flash("Imagem de referência adicionada com sucesso!", "success")
        return redirect(url_for("products.edit", id=id))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao adicionar imagem: {str(e)}", "error")
        return redirect(url_for("products.edit", id=id))

@products_bp.route("/<int:id>/images/<int:image_id>/set-primary", methods=["POST"])
def set_primary_image(id, image_id):
    """Define uma imagem como principal"""
    try:
        product = db.session.query(Product).get_or_404(id)
        image = db.session.query(ReferenceImage).get_or_404(image_id)
        
        # Verificar se a imagem pertence ao produto
        if image.product_id != id:
            flash("Imagem não pertence a este produto", "error")
            return redirect(url_for("products.edit", id=id))
        
        # Atualizar todas as imagens do produto
        for img in product.reference_images:
            img.is_primary = (img.id == image_id)
        
        db.session.commit()
        
        flash("Imagem principal definida com sucesso!", "success")
        return redirect(url_for("products.edit", id=id))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Erro ao definir imagem principal: {str(e)}", "error")
        return redirect(url_for("products.edit", id=id))


