# backend-shopee/Ler_Etiqueta/gerador_zpl_lista.py
# ATUALIZADO: Este arquivo não desenha mais a lista.
# Ele AGORA apenas recebe uma imagem Base64 de alta resolução (gerada pelo frontend)
# e a converte para o formato ZPL ~DGR.

import zlib
import base64
from PIL import Image, ImageOps
import io
import re

# --- Constantes de ZPL ---
# Nome do gráfico na memória da impressora
NOME_GRF = "DEMO.GRF"
# Dimensões da etiqueta (para o comando de impressão)
DPI = 203
LABEL_WIDTH_INCHES = 4
LABEL_HEIGHT_INCHES = 6
LABEL_WIDTH_DOTS = int(LABEL_WIDTH_INCHES * DPI)
LABEL_HEIGHT_DOTS = int(LABEL_HEIGHT_INCHES * DPI)


# --- Funções de Conversão para ZPL ~DGR (Mantidas) ---

def _crc16_ccitt_0000(data_bytes: bytes) -> int:
    """Calcula o CRC-16-CCITT (poly 0x1021, init 0x0000) sobre os bytes."""
    crc = 0x0000
    poly = 0x1021
    for b in data_bytes:
        crc ^= (b << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

def _imagem_para_grf_z64(imagem: Image.Image, nome_grafico: str) -> str:
    """Converte imagem PIL monocromática ('1') para a string ZPL ~DGR:Z64."""
    if imagem.mode != '1':
        print(f"AVISO: Imagem recebida para _imagem_para_grf_z64 não estava no modo '1'. Tentando converter...")
        # A imagem já deve vir em '1' (1=preto, 0=branco)
        imagem = imagem.convert('1')

    largura_bytes = (imagem.width + 7) // 8
    total_bytes = imagem.height * largura_bytes
    
    # .tobytes() no modo '1' gera os dados binários corretos (1=preto, 0=branco)
    dados_raw = imagem.tobytes()

    # Comprime e codifica em Base64
    dados_z = zlib.compress(dados_raw)
    dados_b64 = base64.b64encode(dados_z).decode('ascii')
    dados_b64 = ''.join(dados_b64.split()) # Remove quebras de linha/espaços

    # Calcula o CRC sobre os BYTES da string Base64
    crc = _crc16_ccitt_0000(dados_b64.encode('ascii'))
    crc_hex = f"{crc:04X}"

    # Monta a string ~DGR
    return f"~DGR:{nome_grafico},{total_bytes},{largura_bytes},:Z64:{dados_b64}:{crc_hex}"

# --- Nova Função Principal ---

def gerar_zpl_de_imagem_base64(imagem_base64_string: str) -> str:
    """
    Recebe uma imagem (PNG Base64) do frontend, converte para monocromático
    e gera o ZPL final.
    """
    try:
        # 1. Limpar e Decodificar a string Base64
        # Remove o prefixo "data:image/png;base64,"
        dados_imagem = re.sub('^data:image/.+;base64,', '', imagem_base64_string)
        img_bytes = base64.b64decode(dados_imagem)
        img_pil = Image.open(io.BytesIO(img_bytes))

        # 2. Lidar com transparência (se for PNG) e garantir RGB
        if img_pil.mode == 'RGBA':
            fundo_branco = Image.new('RGB', img_pil.size, (255, 255, 255))
            fundo_branco.paste(img_pil, mask=img_pil.split()[3]) # Cola usando o canal alfa como máscara
            img_rgb = fundo_branco
        else:
            img_rgb = img_pil.convert('RGB')

        # 3. Converter para L (escala de cinza)
        # No modo L: 0 é preto, 255 é branco
        img_l = img_rgb.convert('L')

        # 4. Inverter a imagem L
        # Agora: 255 é preto, 0 é branco
        img_l_invertida = ImageOps.invert(img_l)

        # 5. Converter para '1' (monocromático)
        # No modo '1' do PIL, pixels > 128 (no caso, 255=preto) viram 1.
        # Isso resulta em 1=preto, 0=branco, que é o formato binário esperado.
        img_bw = img_l_invertida.convert('1')
        
        # 6. Gerar o ZPL ~DGR
        zpl_dgr_string = _imagem_para_grf_z64(img_bw, NOME_GRF)

        # 7. Adicionar comandos de impressão
        zpl_print_cmd = f"^XA^MMT^PW{LABEL_WIDTH_DOTS}^LL{LABEL_HEIGHT_DOTS}^LS0^FO0,0^XGR:{NOME_GRF},1,1^FS^PQ1,0,1,Y^XZ"
        
        print("Imagem Base64 convertida para ZPL com sucesso.")
        return zpl_dgr_string + "\n" + zpl_print_cmd

    except Exception as e:
        print(f"ERRO CRÍTICO ao converter imagem Base64 para ZPL: {e}")
        # Retorna um ZPL de erro visível na impressão
        return f"^XA^FO50,50^A0N,30,30^FDErro ao gerar imagem ZPL: {e}^FS^XZ"

