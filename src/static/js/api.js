/**
 * API Client para o Sistema de Inspeção de LEDs
 */
class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
    }

    /**
     * Obtém a lista de produtos
     * @returns {Promise<Array>} Lista de produtos
     */
    async getProducts() {
        try {
            const response = await fetch(`${this.baseUrl}/api/products`);
            if (!response.ok) {
                throw new Error(`Erro ao buscar produtos: ${response.statusText}`);
            }
            const data = await response.json();
            return data.products;
        } catch (error) {
            console.error('Erro ao buscar produtos:', error);
            throw error;
        }
    }

    /**
     * Obtém detalhes de um produto específico
     * @param {number} productId - ID do produto
     * @returns {Promise<Object>} Detalhes do produto
     */
    async getProduct(productId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/products/${productId}`);
            if (!response.ok) {
                throw new Error(`Erro ao buscar produto: ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Erro ao buscar produto ${productId}:`, error);
            throw error;
        }
    }

    /**
     * Faz upload de uma imagem para um produto
     * @param {number} productId - ID do produto
     * @param {File} imageFile - Arquivo de imagem
     * @param {boolean} isPrimary - Se a imagem deve ser definida como principal
     * @returns {Promise<Object>} Resultado do upload
     */
    async uploadImage(productId, imageFile, isPrimary = false) {
        try {
            const formData = new FormData();
            formData.append('image', imageFile);
            formData.append('is_primary', isPrimary);

            const response = await fetch(`${this.baseUrl}/api/products/${productId}/images`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Erro ao fazer upload da imagem: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Erro ao fazer upload de imagem para o produto ${productId}:`, error);
            throw error;
        }
    }

    /**
     * Exclui uma imagem de referência
     * @param {number} productId - ID do produto
     * @param {number} imageId - ID da imagem
     * @returns {Promise<Object>} Resultado da exclusão
     */
    async deleteImage(productId, imageId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/products/${productId}/images/${imageId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Erro ao excluir imagem: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Erro ao excluir imagem ${imageId} do produto ${productId}:`, error);
            throw error;
        }
    }

    /**
     * Define uma imagem como principal
     * @param {number} productId - ID do produto
     * @param {number} imageId - ID da imagem
     * @returns {Promise<Object>} Resultado da operação
     */
    async setPrimaryImage(productId, imageId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/products/${productId}/images/${imageId}/set-primary`, {
                method: 'PUT'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Erro ao definir imagem principal: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Erro ao definir imagem ${imageId} como principal para o produto ${productId}:`, error);
            throw error;
        }
    }
}

// Exportar a classe para uso global
window.ApiClient = ApiClient;

