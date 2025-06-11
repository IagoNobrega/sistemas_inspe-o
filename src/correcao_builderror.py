"""
Script de correção completa para o sistema de inspeção de PCIs

Este script corrige os problemas identificados:
1. BuildError no endpoint 'products.delete_image'
2. Fluxo de upload e vínculo de imagens de referência
3. Templates com chamadas para rotas inexistentes

Compatível com Python 3.13.3
"""

import os
import sys

# Conteúdo corrigido para o arquivo products.py (routes)
PRODUCTS_ROUTES_CONTENT = """from flask import Blueprint, request, render_template, redirect, url_for, flash, current_app
import os
import uuid
from werkzeug.utils import secure_filename
from src.db import db
from src.models.product import Product, ReferenceImage, Inspection

products_bp = Blueprint('products', __name__, url_prefix='/products')

@products_bp.route('/')
def index():
    \"\"\"Lista todos os produtos cadastrados\"\"\"
    products = Product.query.order_by(Product.code).all()
    return render_template('products/index.html', products=products)

@products_bp.route('/new')
def new():
    \"\"\"Exibe formulário para cadastro de novo produto\"\"\"
    return render_template('products/new.html')

@products_bp.route('/create', methods=['POST'])
def create():
    \"\"\"Processa o formulário de cadastro de produto\"\"\"
    code = request.form.get('code')
    name = request.form.get('name')
    description = request.form.get('description', '')
    active = 'active' in request.form
    
    # Verificar se já existe produto com o mesmo código
    existing_product = Product.query.filter_by(code=code).first()
    if existing_product:
        flash(f'Já existe um produto com o código {code}', 'danger')
        return redirect(url_for('products.new'))
    
    # Criar novo produto
    product = Product(code=code, name=name, description=description, active=active)
    db.session.add(product)
    db.session.commit()
    
    # Processar imagem de referência, se enviada
    if 'reference_image' in request.files and request.files['reference_image'].filename:
        file = request.files['reference_image']
        filename = secure_filename(file.filename)
        # Gerar nome único para o arquivo
        unique_filename = f"{uuid.uuid4()}_{filename}"
        # Definir caminho para salvar o arquivo
        file_path = os.path.join('images', 'products', unique_filename)
        full_path = os.path.join(current_app.static_folder, file_path)
        # Salvar arquivo
        file.save(full_path)
        
        # Criar registro da imagem de referência
        reference_image = ReferenceImage(
            product_id=product.id,
            path=file_path,
            is_primary=True  # Primeira imagem é sempre a principal
        )
        db.session.add(reference_image)
        db.session.commit()
    
    flash(f'Produto {name} cadastrado com sucesso!', 'success')
    return redirect(url_for('products.show', id=product.id))

@products_bp.route('/<int:id>')
def show(id):
    \"\"\"Exibe detalhes de um produto específico\"\"\"
    product = Product.query.get_or_404(id)
    return render_template('products/show.html', product=product)

@products_bp.route('/<int:id>/edit')
def edit(id):
    \"\"\"Exibe formulário para edição de produto\"\"\"
    product = Product.query.get_or_404(id)
    return render_template('products/edit.html', product=product)

@products_bp.route('/<int:id>/update', methods=['POST'])
def update(id):
    \"\"\"Processa o formulário de edição de produto\"\"\"
    product = Product.query.get_or_404(id)
    
    product.code = request.form.get('code')
    product.name = request.form.get('name')
    product.description = request.form.get('description', '')
    product.active = 'active' in request.form
    
    db.session.commit()
    
    # Processar nova imagem de referência, se enviada
    if 'reference_image' in request.files and request.files['reference_image'].filename:
        file = request.files['reference_image']
        filename = secure_filename(file.filename)
        # Gerar nome único para o arquivo
        unique_filename = f"{uuid.uuid4()}_{filename}"
        # Definir caminho para salvar o arquivo
        file_path = os.path.join('images', 'products', unique_filename)
        full_path = os.path.join(current_app.static_folder, file_path)
        # Salvar arquivo
        file.save(full_path)
        
        # Se for definida como principal, desmarcar as outras
        is_primary = 'is_primary' in request.form
        if is_primary:
            for image in product.reference_images:
                image.is_primary = False
        
        # Criar registro da imagem de referência
        reference_image = ReferenceImage(
            product_id=product.id,
            path=file_path,
            is_primary=is_primary
        )
        db.session.add(reference_image)
        db.session.commit()
    
    flash(f'Produto {product.name} atualizado com sucesso!', 'success')
    return redirect(url_for('products.show', id=product.id))

@products_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    \"\"\"Exclui um produto\"\"\"
    product = Product.query.get_or_404(id)
    
    # Excluir imagens de referência do sistema de arquivos
    for image in product.reference_images:
        try:
            os.remove(os.path.join(current_app.static_folder, image.path))
        except:
            pass  # Ignorar erros ao excluir arquivos
    
    db.session.delete(product)
    db.session.commit()
    
    flash(f'Produto {product.name} excluído com sucesso!', 'success')
    return redirect(url_for('products.index'))

@products_bp.route('/delete_image/<int:id>/<int:image_id>', methods=['POST'])
def delete_image(id, image_id):
    \"\"\"Exclui uma imagem de referência\"\"\"
    product = Product.query.get_or_404(id)
    image = ReferenceImage.query.get_or_404(image_id)
    
    # Verificar se a imagem pertence ao produto
    if image.product_id != product.id:
        flash('Imagem não pertence a este produto!', 'danger')
        return redirect(url_for('products.show', id=product.id))
    
    # Excluir arquivo do sistema de arquivos
    try:
        os.remove(os.path.join(current_app.static_folder, image.path))
    except:
        pass  # Ignorar erros ao excluir arquivo
    
    # Se a imagem excluída era a principal, definir outra como principal
    was_primary = image.is_primary
    
    # Excluir registro do banco de dados
    db.session.delete(image)
    db.session.commit()
    
    # Se a imagem excluída era a principal e existem outras imagens, definir a primeira como principal
    if was_primary:
        remaining_image = ReferenceImage.query.filter_by(product_id=product.id).first()
        if remaining_image:
            remaining_image.is_primary = True
            db.session.commit()
    
    flash('Imagem excluída com sucesso!', 'success')
    return redirect(url_for('products.edit', id=product.id))

@products_bp.route('/<int:id>/set_primary_image/<int:image_id>', methods=['POST'])
def set_primary_image(id, image_id):
    \"\"\"Define uma imagem como principal\"\"\"
    product = Product.query.get_or_404(id)
    image = ReferenceImage.query.get_or_404(image_id)
    
    # Verificar se a imagem pertence ao produto
    if image.product_id != product.id:
        flash('Imagem não pertence a este produto!', 'danger')
        return redirect(url_for('products.edit', id=product.id))
    
    # Desmarcar todas as imagens como principal
    for img in product.reference_images:
        img.is_primary = False
    
    # Marcar a imagem selecionada como principal
    image.is_primary = True
    db.session.commit()
    
    flash('Imagem definida como principal com sucesso!', 'success')
    return redirect(url_for('products.edit', id=product.id))
"""

# Template corrigido para products/show.html
PRODUCTS_SHOW_TEMPLATE = """{% extends 'base.html' %}

{% block title %}Detalhes do Produto - Sistema de Inspeção de PCIs{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <h1>{{ product.name }}</h1>
    <div>
        <a href="{{ url_for('inspection.inspect_form', product_id=product.id) }}" class="btn btn-success">
            <i class="bi bi-search"></i> Inspecionar Este Produto
        </a>
        <a href="{{ url_for('products.edit', id=product.id) }}" class="btn btn-primary">
            <i class="bi bi-pencil"></i> Editar
        </a>
        <a href="{{ url_for('products.index') }}" class="btn btn-secondary">
            <i class="bi bi-arrow-left"></i> Voltar para Lista
        </a>
    </div>
</div>

<div class="row">
    <div class="col-md-6">
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Informações do Produto</h5>
            </div>
            <div class="card-body">
                <table class="table table-striped">
                    <tbody>
                        <tr>
                            <th style="width: 30%">Código:</th>
                            <td>{{ product.code }}</td>
                        </tr>
                        <tr>
                            <th>Nome:</th>
                            <td>{{ product.name }}</td>
                        </tr>
                        <tr>
                            <th>Descrição:</th>
                            <td>{{ product.description or 'Não informada' }}</td>
                        </tr>
                        <tr>
                            <th>Status:</th>
                            <td>
                                {% if product.active %}
                                    <span class="badge bg-success">Ativo</span>
                                {% else %}
                                    <span class="badge bg-danger">Inativo</span>
                                {% endif %}
                            </td>
                        </tr>
                        <tr>
                            <th>Data de Cadastro:</th>
                            <td>{{ product.created_at.strftime('%d/%m/%Y %H:%M') }}</td>
                        </tr>
                        <tr>
                            <th>Última Atualização:</th>
                            <td>{{ product.updated_at.strftime('%d/%m/%Y %H:%M') }}</td>
                        </tr>
                    </tbody>
                </table>
                
                <form method="post" action="{{ url_for('products.delete', id=product.id) }}" onsubmit="return confirm('Tem certeza que deseja excluir este produto? Esta ação não pode ser desfeita.');" class="mt-3">
                    <button type="submit" class="btn btn-danger">
                        <i class="bi bi-trash"></i> Excluir Produto
                    </button>
                </form>
            </div>
        </div>
    </div>
    
    <div class="col-md-6">
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Imagens de Referência</h5>
            </div>
            <div class="card-body">
                {% if product.reference_images %}
                    <div class="row">
                        {% for image in product.reference_images %}
                            <div class="col-md-6 mb-3">
                                <div class="card h-100">
                                    <img src="{{ url_for('static', filename=image.path) }}" class="card-img-top" alt="{{ product.name }}">
                                    <div class="card-body">
                                        <h6 class="card-title">
                                            {% if image.is_primary %}
                                                <span class="badge bg-success">Principal</span>
                                            {% else %}
                                                <span class="badge bg-secondary">Secundária</span>
                                            {% endif %}
                                        </h6>
                                    </div>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                    
                    <div class="d-grid gap-2 mt-3">
                        <a href="{{ url_for('products.edit', id=product.id) }}" class="btn btn-outline-primary">
                            <i class="bi bi-images"></i> Gerenciar Imagens
                        </a>
                    </div>
                {% else %}
                    <div class="alert alert-warning">
                        <i class="bi bi-exclamation-triangle"></i> Este produto não possui imagens de referência.
                    </div>
                    
                    <div class="d-grid gap-2">
                        <a href="{{ url_for('products.edit', id=product.id) }}" class="btn btn-primary">
                            <i class="bi bi-plus-circle"></i> Adicionar Imagem de Referência
                        </a>
                    </div>
                {% endif %}
            </div>
        </div>
        
        <div class="card mb-4">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">Histórico de Inspeções</h5>
            </div>
            <div class="card-body">
                {% if product.inspections %}
                    <table class="table table-striped table-hover">
                        <thead>
                            <tr>
                                <th>Data</th>
                                <th>Resultado</th>
                                <th>Defeitos</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for inspection in product.inspections[:5] %}
                                <tr>
                                    <td>{{ inspection.created_at.strftime('%d/%m/%Y %H:%M') }}</td>
                                    <td>
                                        {% if inspection.approved %}
                                            <span class="badge bg-success">APROVADO</span>
                                        {% else %}
                                            <span class="badge bg-danger">REPROVADO</span>
                                        {% endif %}
                                    </td>
                                    <td>{{ inspection.defects_count }}</td>
                                    <td>
                                        <a href="{{ url_for('inspection.show', id=inspection.id) }}" class="btn btn-sm btn-outline-primary">
                                            <i class="bi bi-eye"></i> Ver
                                        </a>
                                    </td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    
                    {% if product.inspections|length > 5 %}
                        <div class="d-grid gap-2 mt-3">
                            <a href="{{ url_for('inspection.history', product_id=product.id) }}" class="btn btn-outline-primary">
                                <i class="bi bi-clock-history"></i> Ver Histórico Completo
                            </a>
                        </div>
                    {% endif %}
                {% else %}
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i> Nenhuma inspeção realizada para este produto.
                    </div>
                    
                    <div class="d-grid gap-2">
                        <a href="{{ url_for('inspection.inspect_form', product_id=product.id) }}" class="btn btn-success">
                            <i class="bi bi-search"></i> Realizar Inspeção
                        </a>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

def aplicar_correcoes(base_dir):
    """Aplica as correções nos arquivos do projeto"""
    
    # Caminhos dos arquivos
    products_routes_path = os.path.join(base_dir, 'src', 'routes', 'products.py')
    products_show_path = os.path.join(base_dir, 'src', 'templates', 'products', 'show.html')
    
    # Aplicar correção no arquivo de rotas
    with open(products_routes_path, 'w', encoding='utf-8') as f:
        f.write(PRODUCTS_ROUTES_CONTENT)
    print(f"✓ Arquivo corrigido: {products_routes_path}")
    
    # Aplicar correção no template
    with open(products_show_path, 'w', encoding='utf-8') as f:
        f.write(PRODUCTS_SHOW_TEMPLATE)
    print(f"✓ Arquivo corrigido: {products_show_path}")

def main():
    """Função principal"""
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        base_dir = input("Digite o caminho para o diretório do projeto: ")
    
    if not os.path.isdir(base_dir):
        print(f"Erro: Diretório {base_dir} não encontrado!")
        return
    
    try:
        aplicar_correcoes(base_dir)
        print("\n✅ Todas as correções foram aplicadas com sucesso!")
        print("\nProblemas corrigidos:")
        print("- BuildError no endpoint 'products.delete_image'")
        print("- Fluxo de upload e vínculo de imagens de referência")
        print("- Templates com chamadas para rotas inexistentes")
        print("\nAgora você pode executar o sistema normalmente:")
        print(f"python {os.path.join(base_dir, 'src', 'main.py')}")
        
    except Exception as e:
        print(f"Erro ao aplicar correções: {e}")

if __name__ == "__main__":
    main()
