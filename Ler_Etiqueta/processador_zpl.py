# backend-shopee/Ler_Etiqueta/processador_zpl.py
# ATUALIZADO: Corrigido o Regex para não capturar o CRC no final dos dados Base64.

import re
import zlib
import base64
import io # Usado para manipulação de imagem em memória
from PIL import Image, ImageOps

def converter_zpl_para_imagem_base64(bloco_zpl: str):
    """
    Recebe um bloco de texto ZPL, extrai os dados da imagem (~DGR),
    converte em uma imagem PIL e retorna como uma string PNG Base64.
    """
    if '~DGR' not in bloco_zpl:
        print("Erro: Bloco ZPL não contém ~DGR.")
        return None

    # Expressão regular ATUALIZADA:
    # Captura (.+?) de forma não-gulosa e para ANTES do CRC (:AAAA)
    match = re.search(r'~DGR:DEMO\.GRF,(\d+),(\d+),:Z64:(.+?):[0-9A-F]{4}', bloco_zpl, re.DOTALL)
    
    if match:
        total_bytes_str, bytes_por_linha_str, dados_comprimidos_b64 = match.groups()
        
        # Limpa apenas quebras de linha e espaços. O CRC já foi excluído pela regex.
        dados_comprimidos_b64 = ''.join(dados_comprimidos_b64.split())

        try:
            total_bytes = int(total_bytes_str)
            bytes_por_linha = int(bytes_por_linha_str)
            
            # Etapa 1: Decodificar de Base64
            # O erro "Incorrect padding" acontecia aqui.
            dados_comprimidos = base64.b64decode(dados_comprimidos_b64)
            
            # Etapa 2: Descomprimir os dados (zlib)
            dados_brutos = zlib.decompress(dados_comprimidos)
            
            # Etapa 3: Calcular as dimensões da imagem
            largura = bytes_por_linha * 8
            altura = total_bytes // bytes_por_linha
            
            # Etapa 4: Criar o objeto de imagem a partir dos dados brutos (Modo '1' = monocromático)
            img = Image.frombytes('1', (largura, altura), dados_brutos)
            
            # Etapa 5: Inverter para visualização (preto no branco)
            img_visual = ImageOps.invert(img.convert('L')).convert('1')

            # Etapa 6: Salvar a imagem em memória como PNG e codificar em Base64
            buffered = io.BytesIO()
            img_visual.save(buffered, format="PNG")
            img_str_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return f"data:image/png;base64,{img_str_base64}"
            
        except Exception as e:
            # Imprime o erro específico no console do backend
            print(f"Erro ao processar ZPL para imagem: {e}")
            return None
    
    print("Erro: Regex não encontrou correspondência no bloco ZPL.")
    return None

