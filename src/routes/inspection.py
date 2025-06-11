from flask import Blueprint, request, jsonify, render_template, url_for, redirect, flash, current_app
import os
import cv2
import numpy as np
import json
import uuid
import time
import logging
import traceback
from werkzeug.utils import secure_filename
from src.models.product import db, Product, ReferenceImage, Inspection

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

inspection_bp = Blueprint('inspection', __name__, url_prefix='/inspection')


# Configurações para upload de arquivos
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'uploads')
RESULTS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'results')

# Criar diretórios se não existirem
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@inspection_bp.route('/')
def index():
    """Exibe histórico de inspeções"""
    try:
        # Parâmetros de filtro
        product_id = request.args.get('product_id', type=int)
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # Consulta base
        query = Inspection.query
        
        # Aplicar filtros
        if product_id:
            query = query.filter_by(product_id=product_id)
        
        if status == 'approved':
            query = query.filter_by(approved=True)
        elif status == 'rejected':
            query = query.filter_by(approved=False)
        
        # Filtros de data
        # (implementação omitida para simplificar)
        
        # Ordenar por data, mais recente primeiro
        query = query.order_by(Inspection.created_at.desc())
        
        inspections = query.all()
        products = Product.query.all()
        
        return render_template(
            'inspection/history.html',
            inspections=inspections,
            products=products,
            selected_product_id=product_id,
            status=status,
            date_from=date_from,
            date_to=date_to
        )
    except Exception as e:
        logger.error(f"Erro ao carregar histórico: {str(e)}")
        logger.error(traceback.format_exc())
        flash(f'Erro ao carregar histórico: {str(e)}', 'error')
        return redirect(url_for('products.index'))

@inspection_bp.route('/inspect')
def inspect():
    """Exibe formulário para inspeção de produto"""
    try:
        # Obter todos os produtos ativos
        products = Product.query.filter_by(active=True).all()
        
        # Verificar se há um produto selecionado
        selected_product_id = request.args.get('product_id', type=int)
        selected_product = None
        
        if selected_product_id:
            selected_product = Product.query.get(selected_product_id)
            if not selected_product:
                flash(f'Produto com ID {selected_product_id} não encontrado', 'error')
        
        return render_template(
            'inspection/inspect.html',
            products=products,
            selected_product=selected_product,
            selected_product_id=selected_product_id
        )
    except Exception as e:
        logger.error(f"Erro ao carregar formulário de inspeção: {str(e)}")
        logger.error(traceback.format_exc())
        flash(f'Erro ao carregar página: {str(e)}', 'error')
        return redirect(url_for('products.index'))

@inspection_bp.route('/analyze', methods=['POST'])
def analyze():
    """Analisa uma imagem de produto"""
    try:
        logger.info("Iniciando análise de imagem")
        
        if 'image' not in request.files:
            logger.warning("Nenhuma imagem enviada na requisição")
            return jsonify({'error': 'Nenhuma imagem enviada'}), 400
        
        file = request.files['image']
        product_id = request.form.get('product_id', type=int)
        
        logger.info(f"Analisando imagem para produto ID: {product_id}")
        
        if not product_id:
            logger.warning("ID do produto não especificado")
            return jsonify({'error': 'Produto não especificado'}), 400
        
        product = Product.query.get(product_id)
        if not product:
            logger.warning(f"Produto com ID {product_id} não encontrado")
            return jsonify({'error': f'Produto com ID {product_id} não encontrado'}), 404
        
        # Verificar se o produto tem imagem de referência
        primary_image = None
        for img in product.reference_images:
            if img.is_primary:
                primary_image = img
                break
        
        if not primary_image:
            logger.warning(f"Produto {product.name} (ID: {product_id}) não possui imagem de referência")
            return jsonify({'error': 'Produto não possui imagem de referência'}), 400
        
        if file.filename == '':
            logger.warning("Nome do arquivo vazio")
            return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
        if not allowed_file(file.filename):
            logger.warning(f"Tipo de arquivo não permitido: {file.filename}")
            return jsonify({'error': 'Tipo de arquivo não permitido. Use apenas JPG, PNG ou GIF'}), 400
        
        # Gerar nome único para o arquivo
        filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        logger.info(f"Salvando arquivo em: {filepath}")
        file.save(filepath)
        
        # Verificar se o arquivo foi salvo corretamente
        if not os.path.exists(filepath):
            logger.error(f"Falha ao salvar arquivo em {filepath}")
            return jsonify({'error': 'Falha ao salvar arquivo'}), 500
        
        # Processar a imagem
        reference_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', primary_image.path)
        
        if not os.path.exists(reference_path):
            logger.error(f"Imagem de referência não encontrada: {reference_path}")
            return jsonify({'error': 'Imagem de referência não encontrada'}), 500
        
        logger.info(f"Processando imagem com referência: {reference_path}")
        result = process_image(filepath, reference_path)
        
        if not result:
            logger.error("Falha no processamento da imagem")
            return jsonify({'error': 'Falha no processamento da imagem'}), 500
        
        # Salvar resultado da inspeção no banco de dados
        try:
            inspection = Inspection(
                product_id=product_id,
                image_path=f"images/uploads/{filename}",
                result_image_path=result['defect_image'].replace('/static/', ''),
                approved=result['approved'],
                defects_count=len(result['defects']),
                defects_details=json.dumps(result['defects'])
            )
            
            db.session.add(inspection)
            db.session.commit()
            logger.info(f"Inspeção salva com sucesso. ID: {inspection.id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar inspeção no banco de dados: {str(e)}")
            logger.error(traceback.format_exc())
            # Continuar mesmo com erro no banco de dados, apenas logar
        
        logger.info(f"Análise concluída. Resultado: {'APROVADO' if result['approved'] else 'REPROVADO'}")
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Erro durante análise de imagem: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@inspection_bp.route('/<int:id>')
def show(id):
    """Exibe detalhes de uma inspeção específica"""
    try:
        inspection = Inspection.query.get_or_404(id)
        
        # Converter defects_details de JSON para lista
        defects = []
        if inspection.defects_details:
            try:
                defects = json.loads(inspection.defects_details)
            except json.JSONDecodeError:
                logger.warning(f"Erro ao decodificar JSON de defeitos para inspeção {id}")
        
        return render_template(
            'inspection/show.html',
            inspection=inspection,
            defects=defects
        )
    except Exception as e:
        logger.error(f"Erro ao mostrar detalhes da inspeção {id}: {str(e)}")
        logger.error(traceback.format_exc())
        flash(f'Erro ao carregar detalhes: {str(e)}', 'error')
        return redirect(url_for('inspection.index'))

def normalize_image(image):
    """
    Normaliza a imagem para reduzir variações de iluminação
    """
    try:
        # Verificar se a imagem é válida
        if image is None or image.size == 0:
            logger.error("Imagem inválida para normalização")
            return None
            
        # Converter para LAB para separar luminância (L) das cores (A,B)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Aplicar CLAHE (Contrast Limited Adaptive Histogram Equalization) no canal L
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        
        # Mesclar canais normalizados
        merged = cv2.merge([cl, a, b])
        
        # Converter de volta para BGR
        normalized = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        
        return normalized
    except Exception as e:
        logger.error(f"Erro na normalização da imagem: {str(e)}")
        logger.error(traceback.format_exc())
        return image  # Retorna a imagem original em caso de erro

def detect_leds(image):
    """
    Detecta e segmenta os LEDs na imagem usando múltiplos métodos
    para maior robustez
    """
    try:
        # Verificar se a imagem é válida
        if image is None or image.size == 0:
            logger.error("Imagem inválida para detecção de LEDs")
            return None
        
        # Converter para HSV para melhor segmentação de cor
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Definir múltiplas faixas de cor para LEDs amarelos/brancos
        # Faixa para LEDs amarelos
        lower_yellow = np.array([15, 70, 100])
        upper_yellow = np.array([45, 255, 255])
        
        # Faixa para LEDs brancos/brilhantes
        lower_white = np.array([0, 0, 180])
        upper_white = np.array([180, 30, 255])
        
        # Criar máscaras para cada faixa de cor
        mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        
        # Combinar as máscaras
        mask = cv2.bitwise_or(mask_yellow, mask_white)
        
        # Aplicar operações morfológicas para limpar a máscara
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Método adicional: detecção baseada em brilho
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, bright_mask = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Combinar com a máscara baseada em cor
        mask = cv2.bitwise_or(mask, bright_mask)
        
        # Limpar novamente
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        return mask
    except Exception as e:
        logger.error(f"Erro na detecção de LEDs: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def compare_led_patterns(ref_image, test_image):
    """
    Compara padrões de LEDs entre imagem de referência e imagem de teste
    usando técnicas de correspondência de padrões
    """
    try:
        # Converter para escala de cinza
        ref_gray = cv2.cvtColor(ref_image, cv2.COLOR_BGR2GRAY)
        test_gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
        
        # Aplicar threshold para destacar os LEDs
        _, ref_thresh = cv2.threshold(ref_gray, 200, 255, cv2.THRESH_BINARY)
        _, test_thresh = cv2.threshold(test_gray, 200, 255, cv2.THRESH_BINARY)
        
        # Encontrar contornos dos LEDs na imagem de referência
        ref_contours, _ = cv2.findContours(ref_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrar contornos pequenos
        ref_contours = [c for c in ref_contours if cv2.contourArea(c) > 50]
        
        # Criar máscara para cada LED na imagem de referência
        defects = []
        defect_image = test_image.copy()
        
        # Para cada LED na referência, verificar se existe na imagem de teste
        for i, contour in enumerate(ref_contours):
            # Obter região de interesse (ROI) do LED
            x, y, w, h = cv2.boundingRect(contour)
            
            # Expandir um pouco a ROI para garantir que todo o LED seja capturado
            x_expanded = max(0, x - 5)
            y_expanded = max(0, y - 5)
            w_expanded = min(ref_thresh.shape[1] - x_expanded, w + 10)
            h_expanded = min(ref_thresh.shape[0] - y_expanded, h + 10)
            
            # Extrair ROI da imagem de referência
            ref_roi = ref_thresh[y_expanded:y_expanded+h_expanded, x_expanded:x_expanded+w_expanded]
            
            # Extrair ROI correspondente da imagem de teste
            test_roi = test_thresh[y_expanded:y_expanded+h_expanded, x_expanded:x_expanded+w_expanded]
            
            # Calcular diferença entre as ROIs
            diff_roi = cv2.absdiff(ref_roi, test_roi)
            
            # Calcular porcentagem de diferença
            diff_percentage = (cv2.countNonZero(diff_roi) / (w_expanded * h_expanded)) * 100
            
            # Se a diferença for significativa, considerar como defeito
            if diff_percentage > 30:  # Ajustar este limiar conforme necessário
                defects.append(f"Defeito #{len(defects)+1}: LED com anomalia na posição ({x}, {y})")
                cv2.rectangle(defect_image, (x_expanded, y_expanded), 
                             (x_expanded + w_expanded, y_expanded + h_expanded), (0, 0, 255), 2)
        
        return defects, defect_image
    except Exception as e:
        logger.error(f"Erro na comparação de padrões de LEDs: {str(e)}")
        logger.error(traceback.format_exc())
        return [], test_image

def process_image(image_path, reference_path):
    """
    Processa a imagem para detectar defeitos comparando com a referência
    Versão completamente reestruturada para maior precisão e robustez
    """
    try:
        logger.info(f"Iniciando processamento de imagem: {image_path}")
        logger.info(f"Usando referência: {reference_path}")
        
        # Carregar imagens
        test_image = cv2.imread(image_path)
        reference_image = cv2.imread(reference_path)
        
        # Verificar se as imagens foram carregadas corretamente
        if test_image is None:
            logger.error(f"Falha ao carregar imagem de teste: {image_path}")
            return None
            
        if reference_image is None:
            logger.error(f"Falha ao carregar imagem de referência: {reference_path}")
            return None
        
        logger.info(f"Imagens carregadas. Teste: {test_image.shape}, Referência: {reference_image.shape}")
        
        # Redimensionar imagem de teste para corresponder à referência
        test_image = cv2.resize(test_image, (reference_image.shape[1], reference_image.shape[0]))
        logger.info(f"Imagem de teste redimensionada para: {test_image.shape}")
        
        # Normalizar iluminação em ambas as imagens
        ref_norm = normalize_image(reference_image)
        test_norm = normalize_image(test_image)
        
        if ref_norm is None or test_norm is None:
            logger.error("Falha na normalização das imagens")
            return None
            
        # Detectar LEDs em ambas as imagens
        test_leds = detect_leds(test_norm)
        ref_leds = detect_leds(ref_norm)
        
        if test_leds is None or ref_leds is None:
            logger.error("Falha na detecção de LEDs")
            return None
        
        # Comparar padrões de LEDs
        defects, defect_image = compare_led_patterns(ref_norm, test_norm)
        
        # Salvar imagem com marcações de defeitos
        result_filename = f"defect_{os.path.basename(image_path)}"
        result_path = os.path.join(RESULTS_FOLDER, result_filename)
        cv2.imwrite(result_path, defect_image)
        
        # Determinar se a peça é aprovada ou não
        approved = len(defects) == 0
        
        # Preparar resultado
        result = {
            'approved': approved,
            'defects': defects,
            'defect_count': len(defects),
            'defect_image': f"/static/images/results/{result_filename}",
            'analyzed_image': f"/static/images/uploads/{os.path.basename(image_path)}"
        }
        
        return result
    except Exception as e:
        logger.error(f"Erro no processamento de imagem: {str(e)}")
        logger.error(traceback.format_exc())
        return None
