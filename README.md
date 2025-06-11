# Sistema de Inspeção Visual para PCIs de LED - Versão Melhorada

## Visão Geral

Esta é uma versão melhorada do Sistema de Inspeção Visual para PCIs de LED, que agora suporta o gerenciamento de múltiplos produtos. O sistema permite cadastrar diferentes modelos de PCIs, armazenar imagens de referência para cada produto, realizar inspeções comparativas e manter um histórico completo de todas as análises realizadas.

## Novas Funcionalidades

- **Cadastro de Múltiplos Produtos**: Cadastre e gerencie diferentes modelos de PCIs de LED
- **Gerenciamento de Imagens de Referência**: Cada produto pode ter múltiplas imagens de referência
- **Filtro e Busca de Produtos**: Encontre facilmente produtos por nome, código ou descrição
- **Ordenação Personalizada**: Ordene produtos por diferentes critérios
- **Histórico de Inspeções por Produto**: Visualize o histórico completo de inspeções para cada produto
- **Interface Moderna e Responsiva**: Design intuitivo e adaptável a diferentes dispositivos
- **Banco de Dados SQLite**: Armazenamento persistente de produtos e inspeções

## Requisitos do Sistema

- Python 3.6 ou superior
- Flask
- OpenCV
- SQLAlchemy
- Outras dependências listadas em `requirements.txt`

## Instalação

1. Extraia os arquivos do projeto em uma pasta de sua preferência
2. Crie um ambiente virtual (recomendado):
   ```
   python -m venv venv
   ```
3. Ative o ambiente virtual:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

## Executando o Sistema

1. Ative o ambiente virtual (se não estiver ativado)
2. Execute o aplicativo:
   ```
   python src/main.py
   ```
3. Acesse o sistema no navegador:
   ```
   http://localhost:5000
   ```

## Estrutura do Projeto

- `src/`: Código-fonte principal
  - `models/`: Modelos de dados
  - `routes/`: Rotas e controladores
  - `static/`: Arquivos estáticos (CSS, JS, imagens)
  - `templates/`: Templates Jinja2 para as páginas
  - `main.py`: Ponto de entrada da aplicação

## Guia de Uso

### Gerenciamento de Produtos

1. **Cadastrar Novo Produto**:
   - Acesse a página inicial e clique em "Novo Produto"
   - Preencha os dados do produto e faça upload de uma imagem de referência
   - Clique em "Salvar Produto"

2. **Editar Produto**:
   - Na lista de produtos, clique no ícone de edição
   - Atualize as informações e/ou adicione novas imagens de referência
   - Clique em "Salvar Alterações"

3. **Gerenciar Imagens de Referência**:
   - Na página de detalhes do produto, você pode adicionar, remover ou definir a imagem principal
   - A imagem principal será usada como referência nas inspeções

### Inspeção de PCIs

1. **Realizar Nova Inspeção**:
   - Clique em "Nova Inspeção" no menu principal
   - Selecione o produto a ser inspecionado
   - Faça upload da imagem da PCI a ser analisada
   - O sistema comparará automaticamente com a imagem de referência e mostrará o resultado

2. **Visualizar Histórico de Inspeções**:
   - Acesse "Histórico" no menu principal
   - Use os filtros para encontrar inspeções específicas por produto, status ou data
   - Clique em "Detalhes" para ver informações completas de uma inspeção

## Personalização

O sistema foi projetado para ser facilmente adaptável às suas necessidades específicas:

- **Algoritmo de Detecção**: O algoritmo de comparação pode ser ajustado em `src/routes/inspection.py`
- **Parâmetros de Sensibilidade**: Ajuste o valor de `min_defect_area` para alterar a sensibilidade da detecção
- **Interface Visual**: Personalize o design modificando os arquivos em `src/static/` e `src/templates/`

## Solução de Problemas

- **Erro ao iniciar**: Verifique se todas as dependências foram instaladas corretamente
- **Erro de banco de dados**: O arquivo de banco de dados SQLite será criado automaticamente na primeira execução
- **Problemas com imagens**: Certifique-se de que as pastas `uploads` e `results` dentro de `static/images/` têm permissões de escrita

## Próximas Melhorias Planejadas

- Exportação de relatórios em PDF
- Dashboard com estatísticas de inspeção
- Suporte a múltiplos usuários com diferentes níveis de acesso
- Integração com sistemas de controle de qualidade

## Suporte

Para dúvidas ou suporte adicional, entre em contato com a equipe de desenvolvimento.
