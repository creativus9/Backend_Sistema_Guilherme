# backend-shopee/importers/xlsx_importer.py
# Módulo dedicado à importação e processamento de pedidos a partir de arquivos XLSX.
# NOVO: O valor DXF agora é armazenado como 'skuPlanoCorte' e 'planoCorte' é inicializado.
# ATUALIZADO: Lógica para incluir a cor no skuPlanoCorte.

import openpyxl
import re
from datetime import datetime

# --- Mapeamentos (do Google Apps Script) ---
rendimentoPlacas = {
    "2020": 50, "3015": 50, "4020": 25, "1515": 55, "3030": 24,
    "3010": 70, "5151": 10, "3013": 50, "4010": 50, "4015": 35,
    "2508": 105, "3510": 60, "1414": 90
}

coresMap = {
    "DOU": "Dourado", "PRA": "Prata", "ROS": "Rose", "CRU": "Cru",
    "BRA": "Branco", "TRA": "Transparente"
}

formatoMap = {
    "REDO": "Redondo", "AVIA": "Aviãozinho", "CORA": "Coração",
    "PLAC": "Plaquinha", "MOLD": "Moldurinha", "NUVM": "Nuvenzinha",
    "NUVE": "Nuvem", "PLAO": "Plaquinha Oval", "PLAR": "Plaquinha com bolinha redonda no começo",
    "URSI": "Ursinho", "PING": "Pingente", "BORB": "Borboleta",
    "BO3D": "Borboleta 3D", "PROT": "Passante retangular oval no topo",
    "FLOP": "Flor Passante", "APCA": "Aplique Casamento", "MIPA": "Mini Palito"
}

furosMap = {
    "1FS": "1 furo Superior", "1FH": "1 Furo Lateral", "2FH": "2 Furos Lateral",
    "2FV": "2 Furos Vertical", "4FL": "4 Furos, 2 na horizontal e 2 na vertical",
    "4FC": "4 Furos nos cantos", "0SF": "SEM FURO", "2PV": "DOIS FUROS PASSANTES VERTICAL",
    "1PC": "UM PASSANTE NO CENTRO"
}

variacoesMap = {
    "0001F": "Escrita/Logo", "0002F": "Ramo coração data", "0003F": "Três Corações data",
    "0004F": "Coração Barra data", "0005F": "Coração Barra", "0006F": "Três corações",
    "0007F": "&", "0008F": "& e data", "0009F": "Cheguei", "0010F": "Escrita+Estrelas",
    "0011F": "Chá do", "0012F": "Escrita+Corações", "1001P": "Gratidão",
    "1002P": "Você é especial", "1003P": "Feito a mão + novelo",
    "1004P": "Feito a mão com coração vazado no meio", "1005P": "Feito com amor + novelo",
    "1006P": "Caderneta de Saúde", "1007P": "Feliz dia das Mães", "1008P": "Ramo de flor 1",
    "1009P": "Feito com amor", "1010P": "Feliz Páscoa", "1011P": "Gratidão modelo 2",
    "1012P": "Fé", "1013P": "Coração", "0000P": "Sem gravação", "0000F": "Sem gravação"
}

def extrair_skus(texto):
    """
    Extrai SKUs de um texto, similar à função extrairSkus do Apps Script.
    Ajusta a quantidade no SKU com base na quantidade principal.
    """
    regex = r"Quantity:\s*(\d+);[^;]*SKU Reference No\.\:\s*([A-Za-z0-9\-]*)"
    skus_parsed = []
    
    for match in re.finditer(regex, texto):
        quantity_main = int(match.group(1))
        sku_original = match.group(2).strip()

        partes = sku_original.split("-")
        if len(partes) >= 7 and partes[5].isdigit(): # Verifica se a parte da quantidade é um dígito
            qtd_sku_in_part = int(partes[5])
            nova_qtd = qtd_sku_in_part * quantity_main
            partes[5] = str(nova_qtd).zfill(3) # Pad with leading zeros to 3 digits
            sku_corrigido = "-".join(partes)
            skus_parsed.append(sku_corrigido)
        else:
            # CORREÇÃO: Cria um SKU de placeholder que ainda contém a quantidade para processamento.
            quantidade_formatada = str(quantity_main).zfill(3)
            placeholder_sku = f"XXXX-XXXX-XXX-XX-XXX-{quantidade_formatada}-XXXXX"
            skus_parsed.append(placeholder_sku)
    return skus_parsed

def process_xlsx_file(file_stream, delivery_date_str, ecommerce, conta_ecommerce): # Adicionado ecommerce, conta_ecommerce
    """
    Processa um arquivo XLSX usando o módulo xlsx_importer,
    extrai dados de pedidos e os formata em um dicionário.
    """
    if not file_stream:
        print("Nenhum arquivo XLSX fornecido para processamento.")
        return []

    try:
        workbook = openpyxl.load_workbook(file_stream)
        sheet = workbook.active 
        print(f"DEBUG (xlsx_importer): Planilha XLSX ativa: '{sheet.title}'")

        sku_map = {}
        id_counter = {}

        # Itera pelas linhas a partir da linha 2 (índice 1) conforme solicitado
        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            values = [cell.value if cell.value is not None else '' for cell in row]

            # Coluna B (índice 1) para ID, Coluna C (índice 2) para Texto com SKUs
            if len(values) < 3: 
                print(f"AVISO (xlsx_importer): Linha {row_idx} do XLSX incompleta (menos de 3 colunas): {values}. Pulando.")
                continue

            order_id_raw = str(values[1]).strip() # Coluna B do XLSX
            sku_text_raw = str(values[2]).strip() # Coluna C do XLSX

            if not order_id_raw and not sku_text_raw: # Pula linhas completamente vazias nas colunas B e C
                continue

            if order_id_raw and not sku_text_raw:
                sku_text_raw = "Quantity: 1; SKU Reference No.: XXXX-XXXX-XXX-XX-XXX-XXX-XXXXX"
                print(f"DEBUG (xlsx_importer): Linha {row_idx}: Coluna C vazia para ID '{order_id_raw}', usando SKU padrão.")

            parsed_skus = extrair_skus(sku_text_raw)

            for sku in parsed_skus:
                partes = sku.split("-")
                if len(partes) >= 7:
                    grupo1 = partes[0]
                    grupo2 = partes[1]
                    grupo3 = partes[2]
                    grupo5 = partes[4]
                    grupo7 = partes[6]
                    quantidade = int(partes[5])

                    base_sku_prefix = "-".join(partes[0:5]) + "-"
                    chave = f"{order_id_raw}|{base_sku_prefix}|{grupo7}"

                    sku_map[chave] = sku_map.get(chave, 0) + quantidade
                else:
                    print(f"AVISO (xlsx_importer): SKU '{sku}' na linha {row_idx} não tem formato esperado (menos de 7 partes).")
        
        if not sku_map:
            print("Nenhum SKU válido encontrado para processar no arquivo XLSX.")
            return []

        final_pedidos_list = []
        for chave, quantidade_total in sku_map.items():
            order_id, base_sku_prefix, grupo7 = chave.split("|")
            partes_base = base_sku_prefix.split("-")
            
            grupo1 = partes_base[0]
            grupo2 = partes_base[1]
            grupo3 = partes_base[2]
            # grupo4 é o material, partes_base[3]
            grupo5 = partes_base[4] # Cor

            quantidade_formatada = str(quantidade_total).zfill(3)
            
            placas = rendimentoPlacas.get(grupo2, "N/A")
            if placas != "N/A":
                placas = (quantidade_total + placas - 1) // placas
            
            cor = coresMap.get(grupo5, "Desconhecido")
            formato = formatoMap.get(grupo1, "Desconhecido")
            furo = furosMap.get(grupo3, "Desconhecido")
            
            tamanho_x = int(grupo2[0:2]) / 10 if grupo2[0:2].isdigit() else "N/A"
            tamanho_y = int(grupo2[2:]) / 10 if grupo2[2:].isdigit() else "N/A"
            tamanho_formatado = f"{tamanho_x}x{tamanho_y} Cm" if tamanho_x != "N/A" and tamanho_y != "N/A" else "Desconhecido"

            variacao = variacoesMap.get(grupo7, "Desconhecido")

            sku_final = base_sku_prefix + quantidade_formatada + "-" + grupo7
            
            # CORREÇÃO: Lógica atualizada para a situação do pedido
            if base_sku_prefix == "XXXX-XXXX-XXX-XX-XXX-":
                is_padronizado = "SKU Inválido"
            elif sku_final.endswith("P"):
                is_padronizado = "Arquivo Padronizado"
            elif sku_final.endswith("F"):
                is_padronizado = "Fazer arquivo"
            else:
                is_padronizado = "" # Fallback para outros casos
            
            id_counter[order_id] = id_counter.get(order_id, 0) + 1
            id_com_numero = f"{order_id} ({id_counter[order_id]})" if id_counter[order_id] > 1 else order_id

            # ATUALIZADO: Lógica para gerar o skuPlanoCorte_dxf
            sku_plano_corte_dxf = "N/A"
            if (sku_final.endswith("F") or sku_final.endswith("P")) and len(partes_base) >= 5:
                # partes_base contém [FORMATO, TAMANHO, FURO, MATERIAL, COR, '']
                # Verifica se a 5ª parte (índice 4) é uma chave de cor conhecida
                if partes_base[4].upper() in coresMap:
                    dxf_parts = partes_base[0:5] # Inclui a parte da cor
                else:
                    dxf_parts = partes_base[0:4] # Exclui a cor se não for reconhecida
                sku_plano_corte_dxf = "-".join(dxf_parts) + ".dxf"
            elif (sku_final.endswith("F") or sku_final.endswith("P")) and len(partes_base) >= 4:
                # Se não houver 5ª parte ou não for uma cor, usa apenas até o material
                dxf_parts = partes_base[0:4]
                sku_plano_corte_dxf = "-".join(dxf_parts) + ".dxf"
            else:
                # Fallback para formatos de SKU inesperados
                sku_plano_corte_dxf = sku_final + ".dxf" # Retorna o SKU completo com .dxf


            pedido = {
                'id': id_com_numero,
                'situacao': is_padronizado,
                'material': cor,
                'qntPlacas': placas,
                'formato': formato,
                'tamanho': tamanho_formatado,
                'furo': furo,
                'planoCorte': '', # NOVO: Inicializa planoCorte como vazio, será preenchido no frontend
                'skuPlanoCorte': sku_plano_corte_dxf, # NOVO: Novo campo para o SKU do plano de corte (DXF)
                'tipoArte': variacao,
                'sku': sku_final,
                'motivoRetrabalho': '',
                'dataEntrega': delivery_date_str,
                'ecommerce': ecommerce, # Adicionado
                'contaEcommerce': conta_ecommerce # Adicionado
            }
            final_pedidos_list.append(pedido)
        
        print(f"DEBUG (xlsx_importer): {len(final_pedidos_list)} pedidos processados do XLSX.")
        return final_pedidos_list

    except Exception as e:
        print(f"ERRO (xlsx_importer): Falha ao processar dados do XLSX: {e}")
        import traceback
        traceback.print_exc()
        return []

