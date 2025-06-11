import os
import sys
import cv2
import numpy as np
import json
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("test_inspection")

# Adicionar diretório pai ao path para importar módulos do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar funções de processamento de imagem
from src.routes.inspection import normalize_image, detect_leds

def test_image_processing(good_image_path, defective_image_path):
    """
    Testa o processamento de imagens com amostras boas e defeituosas
    """
    logger.info("Iniciando teste de processamento de imagens")
    logger.info(f"Imagem boa: {good_image_path}")
    logger.info(f"Imagem defeituosa: {defective_image_path}")
    
    # Verificar se os arquivos existem
    if not os.path.exists(good_image_path):
        logger.error(f"Arquivo não encontrado: {good_image_path}")
        return False
    
    if not os.path.exists(defective_image_path):
        logger.error(f"Arquivo não encontrado: {defective_image_path}")
        return False
    
    # Carregar imagens
    good_image = cv2.imread(good_image_path)
    defective_image = cv2.imread(defective_image_path)
    
    if good_image is None:
        logger.error(f"Falha ao carregar imagem: {good_image_path}")
        return False
    
    if defective_image is None:
        logger.error(f"Falha ao carregar imagem: {defective_image_path}")
        return False
    
    logger.info("Imagens carregadas com sucesso")
    
    # Redimensionar imagem defeituosa para corresponder à boa
    defective_image = cv2.resize(defective_image, (good_image.shape[1], good_image.shape[0]))
    
    # Testar normalização
    logger.info("Testando normalização de imagens...")
    good_norm = normalize_image(good_image)
    defective_norm = normalize_image(defective_image)
    
    if good_norm is None or defective_norm is None:
        logger.error("Falha na normalização das imagens")
        return False
    
    logger.info("Normalização concluída com sucesso")
    
    # Testar detecção de LEDs
    logger.info("Testando detecção de LEDs...")
    good_leds = detect_leds(good_norm)
    defective_leds = detect_leds(defective_norm)
    
    if good_leds is None or defective_leds is None:
        logger.error("Falha na detecção de LEDs")
        return False
    
    logger.info("Detecção de LEDs concluída com sucesso")
    
    # Encontrar diferenças
    logger.info("Calculando diferenças entre imagens...")
    diff = cv2.absdiff(good_leds, defective_leds)
    
    # Aplicar threshold para destacar apenas diferenças significativas
    _, diff_thresh = cv2.threshold(diff, 50, 255, cv2.THRESH_BINARY)
    
    # Aplicar operações morfológicas para reduzir ruído
    kernel = np.ones((7, 7), np.uint8)
    diff_cleaned = cv2.morphologyEx(diff_thresh, cv2.MORPH_OPEN, kernel)
    
    # Encontrar contornos das diferenças
    contours, _ = cv2.findContours(diff_cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    logger.info(f"Encontrados {len(contours)} contornos de diferenças")
    
    # Calcular área média dos LEDs para referência
    led_contours, _ = cv2.findContours(good_leds, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    led_areas = [cv2.contourArea(c) for c in led_contours if cv2.contourArea(c) > 50]
    avg_led_area = np.mean(led_areas) if led_areas else 500
    
    # Ajustar o limite mínimo com base na área média dos LEDs
    min_defect_area = max(50, avg_led_area * 0.10)  # Reduzido para maior sensibilidade
    logger.info(f"Área média dos LEDs: {avg_led_area}, Limite mínimo para defeitos: {min_defect_area}")
    
    # Contar defeitos significativos
    significant_defects = 0
    defect_image = defective_image.copy()
    
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        if area > min_defect_area:
            # Verificar se o contorno está dentro de um LED na imagem de referência
            mask = np.zeros_like(good_leds)
            cv2.drawContours(mask, [contour], -1, 255, -1)
            overlap = cv2.bitwise_and(good_leds, mask)
            overlap_area = cv2.countNonZero(overlap)
            
            # Se houver sobreposição significativa com um LED, considerar como defeito
            if overlap_area > 0:
                significant_defects += 1
                cv2.drawContours(defect_image, [contour], -1, (0, 0, 255), 2)
                x, y, w, h = cv2.boundingRect(contour)
                logger.info(f"Defeito #{significant_defects} detectado na posição ({x}, {y}), área: {area}")
    
    # MÉTODO ADICIONAL: Comparação de histogramas de cores
    logger.info("Aplicando método adicional: Comparação de histogramas de cores")
    
    # Dividir a imagem em uma grade para análise local
    grid_size = 4  # Dividir em 4x4 = 16 regiões
    h, w = good_norm.shape[:2]
    cell_h, cell_w = h // grid_size, w // grid_size
    
    histogram_defects = 0
    
    for i in range(grid_size):
        for j in range(grid_size):
            # Definir região da grade
            y1, y2 = i * cell_h, (i + 1) * cell_h
            x1, x2 = j * cell_w, (j + 1) * cell_w
            
            # Extrair região da grade para ambas as imagens
            ref_cell = good_norm[y1:y2, x1:x2]
            test_cell = defective_norm[y1:y2, x1:x2]
            
            # Calcular histogramas para cada canal de cor
            channels = [0, 1, 2]  # B, G, R
            hist_size = [32, 32, 32]
            ranges = [0, 256, 0, 256, 0, 256]
            
            ref_hist = cv2.calcHist([ref_cell], channels, None, hist_size, ranges)
            test_hist = cv2.calcHist([test_cell], channels, None, hist_size, ranges)
            
            # Normalizar histogramas
            cv2.normalize(ref_hist, ref_hist, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(test_hist, test_hist, 0, 1, cv2.NORM_MINMAX)
            
            # Comparar histogramas
            hist_diff = cv2.compareHist(ref_hist, test_hist, cv2.HISTCMP_CORREL)
            
            # Se a correlação for baixa, considerar como defeito
            if hist_diff < 0.7:  # Ajustar este limiar conforme necessário
                histogram_defects += 1
                cv2.rectangle(defect_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
                logger.info(f"Defeito de histograma detectado na região ({x1}, {y1}), Correlação: {hist_diff}")
    
    logger.info(f"Método de histograma encontrou {histogram_defects} defeitos")
    
    # Combinar resultados dos métodos
    total_defects = significant_defects + histogram_defects
    
    # Salvar imagens de resultado para inspeção visual
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "src", "static", "images", "test_results")
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cv2.imwrite(os.path.join(output_dir, f"good_norm_{timestamp}.jpg"), good_norm)
    cv2.imwrite(os.path.join(output_dir, f"defective_norm_{timestamp}.jpg"), defective_norm)
    cv2.imwrite(os.path.join(output_dir, f"good_leds_{timestamp}.jpg"), good_leds)
    cv2.imwrite(os.path.join(output_dir, f"defective_leds_{timestamp}.jpg"), defective_leds)
    cv2.imwrite(os.path.join(output_dir, f"diff_{timestamp}.jpg"), diff_cleaned)
    cv2.imwrite(os.path.join(output_dir, f"result_{timestamp}.jpg"), defect_image)
    
    logger.info(f"Imagens de resultado salvas em: {output_dir}")
    
    # Verificar resultados
    if total_defects > 0:
        logger.info(f"TESTE BEM-SUCEDIDO: Detectados {total_defects} defeitos na imagem defeituosa")
        return True
    else:
        logger.warning("TESTE FALHOU: Nenhum defeito detectado na imagem defeituosa")
        return False

if __name__ == "__main__":
    # Caminhos para as imagens de teste
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    good_image = os.path.join(base_dir, "src", "static", "images", "test_images", "good_sample.png")
    defective_image = os.path.join(base_dir, "src", "static", "images", "test_images", "defective_sample.jpg")
    
    # Executar teste
    success = test_image_processing(good_image, defective_image)
    
    if success:
        logger.info("Todos os testes concluídos com sucesso!")
        sys.exit(0)
    else:
        logger.error("Falha nos testes!")
        sys.exit(1)
