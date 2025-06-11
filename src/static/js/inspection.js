/**
 * Sistema de Inspeção Visual para PCIs de LED
 * Módulo JavaScript para gerenciamento da interface de inspeção
 */

document.addEventListener('DOMContentLoaded', function() {
    // Elementos do DOM
    const productSelect = document.getElementById('product_id');
    const uploadArea = document.getElementById('uploadArea');
    const imageInput = document.getElementById('imageInput');
    const browseButton = document.getElementById('browseButton');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const resultContainer = document.getElementById('resultContainer');
    const resultStatus = document.getElementById('resultStatus');
    const originalImage = document.getElementById('originalImage');
    const defectsImage = document.getElementById('defectsImage');
    const defectsList = document.getElementById('defectsList');
    const newInspectionButton = document.getElementById('newInspectionButton');
    const errorContainer = document.getElementById('errorContainer');

    // Redirecionamento ao selecionar produto
    if (productSelect) {
        productSelect.addEventListener('change', function() {
            if (this.value) {
                window.location.href = "/inspection/inspect?product_id=" + this.value;
            }
        });
    }

    // Função para mostrar erros
    function showError(message) {
        if (errorContainer) {
            errorContainer.innerHTML = `
                <div class="alert alert-danger alert-dismissible fade show">
                    <i class="bi bi-exclamation-triangle-fill"></i> <strong>Erro:</strong> ${message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            `;
            errorContainer.style.display = 'block';

            // Log do erro no console para debugging
            console.error("Erro na inspeção:", message);
        }
    }

    // Função para limpar erros
    function clearError() {
        if (errorContainer) {
            errorContainer.innerHTML = '';
            errorContainer.style.display = 'none';
        }
    }

    // Funcionalidade de upload de imagem
    if (uploadArea && imageInput && browseButton) {
        // Abrir seletor de arquivo ao clicar no botão
        browseButton.addEventListener('click', function() {
            imageInput.click();
        });

        // Abrir seletor de arquivo ao clicar na área de upload
        uploadArea.addEventListener('click', function(e) {
            if (e.target === uploadArea || e.target.parentElement === uploadArea) {
                imageInput.click();
            }
        });

        // Efeito visual ao arrastar arquivo sobre a área
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, function(e) {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, function() {
                uploadArea.classList.add('highlight');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, function() {
                uploadArea.classList.remove('highlight');
            }, false);
        });

        // Processar arquivo ao soltar na área
        uploadArea.addEventListener('drop', function(e) {
            const dt = e.dataTransfer;
            const files = dt.files;

            if (files.length) {
                handleFile(files[0]);
            }
        }, false);

        // Processar arquivo ao selecionar via input
        imageInput.addEventListener('change', function() {
            if (this.files.length) {
                handleFile(this.files[0]);
            }
        });

        // Função para processar o arquivo
        function handleFile(file) {
            // Limpar erros anteriores
            clearError();

            // Verificar tipo de arquivo
            if (!file.type.match('image.*')) {
                showError('Por favor, selecione uma imagem válida (JPEG, PNG ou GIF).');
                return;
            }

            // Verificar tamanho do arquivo (máximo 10MB)
            if (file.size > 10 * 1024 * 1024) {
                showError('A imagem é muito grande. O tamanho máximo permitido é 10MB.');
                return;
            }

            // Mostrar loading
            loadingOverlay.style.display = 'flex';
            uploadArea.style.display = 'none';
            resultContainer.style.display = 'none';

            // Criar FormData para envio
            const formData = new FormData();
            formData.append('image', file);

            // Obter ID do produto do select ou do data attribute
            const productId = productSelect ? productSelect.value : document.querySelector('[data-product-id]').dataset.productId;
            formData.append('product_id', productId);

            // Log para debugging
            console.log("Enviando análise para produto ID:", productId);
            console.log("Arquivo:", file.name, "Tipo:", file.type, "Tamanho:", file.size);

            // Enviar para o servidor com timeout de 60 segundos
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 60000);

            fetch('/inspection/analyze', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            })
            .then(response => {
                clearTimeout(timeoutId);

                if (!response.ok) {
                    // Tentar obter mensagem de erro do servidor
                    return response.json().then(data => {
                        throw new Error(data.error || 'Erro ao processar imagem');
                    }).catch(err => {
                        throw new Error(`Erro ${response.status}: ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                // Ocultar loading
                loadingOverlay.style.display = 'none';

                // Mostrar resultados
                resultContainer.style.display = 'block';

                // Definir status
                if (data.approved) {
                    resultStatus.className = 'alert alert-success';
                    resultStatus.innerHTML = '<i class="bi bi-check-circle-fill"></i> <strong>APROVADO</strong> - Nenhum defeito detectado';
                } else {
                    resultStatus.className = 'alert alert-danger';
                    resultStatus.innerHTML = `<i class="bi bi-x-circle-fill"></i> <strong>REPROVADO</strong> - ${data.defects.length} defeito(s) detectado(s)`;
                }

                // Mostrar imagens
                console.log("Imagem original:", data.analyzed_image);
                console.log("Imagem de defeitos:", data.defect_image);

                // Pré-carregar as imagens para garantir que elas sejam exibidas corretamente
                const preloadOriginal = new Image();
                preloadOriginal.onload = function() {
                    originalImage.src = data.analyzed_image;
                    originalImage.style.display = 'block';
                };
                preloadOriginal.onerror = function() {
                    console.error("Erro ao carregar imagem original:", data.analyzed_image);
                    showError('Erro ao carregar a imagem original.');
                };
                preloadOriginal.src = data.analyzed_image;

                const preloadDefects = new Image();
                preloadDefects.onload = function() {
                    defectsImage.src = data.defect_image;
                    defectsImage.style.display = 'block';
                };
                preloadDefects.onerror = function() {
                    console.error("Erro ao carregar imagem de defeitos:", data.defect_image);
                    showError('Erro ao carregar a imagem de defeitos.');
                };
                preloadDefects.src = data.defect_image;

                // Listar defeitos
                if (data.defects.length > 0) {
                    let defectsHtml = '<ul class="list-group">';
                    data.defects.forEach(defect => {
                        defectsHtml += `<li class="list-group-item">${defect}</li>`;
                    });
                    defectsHtml += '</ul>';
                    defectsList.innerHTML = defectsHtml;
                } else {
                    defectsList.innerHTML = '<p class="text-success">Nenhum defeito detectado.</p>';
                }

                // Log para debugging
                console.log("Análise concluída:", data);
            })
            .catch(error => {
                console.error('Erro na análise:', error);
                loadingOverlay.style.display = 'none';
                uploadArea.style.display = 'block';

                // Mostrar mensagem de erro amigável
                if (error.name === 'AbortError') {
                    showError('A análise demorou muito tempo e foi cancelada. Por favor, tente novamente com uma imagem menor ou verifique sua conexão.');
                } else {
                    showError(error.message || 'Erro ao processar a imagem. Por favor, tente novamente.');
                }
            });
        }

        // Nova inspeção
        if (newInspectionButton) {
            newInspectionButton.addEventListener('click', function() {
                resultContainer.style.display = 'none';
                uploadArea.style.display = 'block';
                imageInput.value = '';
                clearError();
            });
        }
    }
});