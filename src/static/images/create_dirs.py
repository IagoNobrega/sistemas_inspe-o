import os

# Criar diretório para imagens de loading
os.makedirs('/home/ubuntu/led_inspection_system/src/static/images', exist_ok=True)

# Criar arquivo GIF de loading vazio (será substituído)
with open('/home/ubuntu/led_inspection_system/src/static/images/loading.gif', 'w') as f:
    f.write('')
