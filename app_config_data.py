# backend-shopee/app_config_data.py
# Módulo para gerenciamento de configurações da aplicação (situação, XLSX e Mapeamentos).

from firebase_config import db # Importa a instância do Firestore
from firebase_admin import firestore # Necessário para firestore.SERVER_TIMESTAMP

CONFIGURATIONS_COLLECTION = 'configuracoes' 

# --- Armazenamento de Opções de Situação em Memória ---
_in_memory_situacao_options = [] 

# --- Armazenamento de Configurações XLSX em Memória ---
_in_memory_xlsx_config = {
    'ecommerces': [],
    'accounts': []
}

# --- Armazenamento de Mapeamentos em Memória ---
_in_memory_cores_map = {}
_in_memory_formato_map = {}
_in_memory_furos_map = {}
_in_memory_variacoes_map = {}

# --- Funções de Gerenciamento de Configurações (Situação, XLSX e Mapeamentos) ---

def _load_situacao_options_from_firestore():
    """
    Carrega as opções de situação do Firestore para a memória.
    Se não existirem, salva as opções padrão no Firestore.
    """
    global _in_memory_situacao_options
    if not db:
        print("Firestore não conectado. Não é possível carregar opções de situação.")
        return

    try:
        doc_ref = db.collection(CONFIGURATIONS_COLLECTION).document('situacao_options')
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            options_raw = data.get('options', [])
            formatted_options = []
            for option in options_raw:
                if isinstance(option, str):
                    formatted_options.append({'name': option, 'color': '#000000'}) 
                elif isinstance(option, dict) and 'name' in option:
                    formatted_options.append({'name': option['name'], 'color': option.get('color', '#000000')})
            _in_memory_situacao_options = formatted_options
            print(f"DEBUG (app_config_data.py): Opções de situação carregadas do Firestore: {_in_memory_situacao_options}")
        else:
            print("AVISO (app_config_data.py): Documento 'situacao_options' não encontrado. Usando padrão e salvando.")
            _in_memory_situacao_options = [
                {'name': 'Fazer arquivo', 'color': '#FF0000'}, 
                {'name': 'Arquivo Padronizado', 'color': '#FFA500'},
                {'name': 'Aguardando Pagamento', 'color': '#FFFF00'},
                {'name': 'Em Separação', 'color': '#008000'},
                {'name': 'Enviado', 'color': '#0000FF'},
                {'name': 'Entregue', 'color': '#800080'},
                {'name': 'Cancelado', 'color': '#808080'},
                {'name': 'Retrabalho', 'color': '#FFC0CB'}
            ]
            update_situacao_options(_in_memory_situacao_options) 
    except Exception as e:
        print(f"ERRO: Falha ao carregar opções de situação do Firestore: {e}")
        _in_memory_situacao_options = [ 
            {'name': 'Fazer arquivo', 'color': '#FF0000'},
            {'name': 'Arquivo Padronizado', 'color': '#FFA500'},
            {'name': 'Aguardando Pagamento', 'color': '#FFFF00'},
            {'name': 'Em Separação', 'color': '#008000'},
            {'name': 'Enviado', 'color': '#0000FF'},
            {'name': 'Entregue', 'color': '#800080'},
            {'name': 'Cancelado', 'color': '#808080'},
            {'name': 'Retrabalho', 'color': '#FFC0CB'}
        ]

def get_situacao_options():
    """
    Retorna as opções de situação configuradas (da memória, que é populada pelo Firestore).
    """
    return list(_in_memory_situacao_options)

def update_situacao_options(new_options):
    """
    Atualiza as opções de situação em memória e no Firestore.
    """
    global _in_memory_situacao_options
    formatted_new_options = []
    for opt in new_options:
        if isinstance(opt, dict) and 'name' in opt and 'color' in opt:
            formatted_new_options.append({'name': opt['name'], 'color': opt['color']})
        elif isinstance(opt, str): 
            formatted_new_options.append({'name': opt, 'color': '#000000'}) 
    
    _in_memory_situacao_options = formatted_new_options
    print(f"DEBUG (app_config_data.py): Opções de situação atualizadas em memória para: {_in_memory_situacao_options}")

    if db:
        try:
            doc_ref = db.collection(CONFIGURATIONS_COLLECTION).document('situacao_options')
            doc_ref.set({'options': _in_memory_situacao_options}, merge=True)
            print(f"DEBUG (app_config_data.py): Opções de situação salvas no Firestore.")
            return True
        except Exception as e:
            print(f"ERRO (app_config_data.py): Falha ao salvar opções de situação no Firestore: {e}")
            return False
    else:
        print("AVISO (app_config_data.py): Firestore não conectado. Opções de situação não serão salvas no Firestore.")
        return False 

def _load_xlsx_config_from_firestore():
    """
    Carrega as configurações XLSX (e-commerces e contas) do Firestore para a memória.
    Se não existirem, salva as opções padrão no Firestore.
    """
    global _in_memory_xlsx_config
    if not db:
        print("Firestore não conectado. Não é possível carregar configurações XLSX.")
        return

    try:
        doc_ref = db.collection(CONFIGURATIONS_COLLECTION).document('xlsx_config')
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            _in_memory_xlsx_config['ecommerces'] = data.get('ecommerces', [])
            _in_memory_xlsx_config['accounts'] = data.get('accounts', [])
            print(f"DEBUG (app_config_data.py): Configurações XLSX carregadas do Firestore: {_in_memory_xlsx_config}")
        else:
            print("AVISO (app_config_data.py): Documento 'xlsx_config' não encontrado. Usando padrão e salvando.")
            _in_memory_xlsx_config = {
                'ecommerces': ['Shopee', 'Mercado Livre', 'Tiny', 'Outro'],
                'accounts': ['Conta Padrão', 'Conta Secundária']
            }
            update_xlsx_config(_in_memory_xlsx_config) 
    except Exception as e:
        print(f"ERRO: Falha ao carregar configurações XLSX do Firestore: {e}")
        _in_memory_xlsx_config = { 
            'ecommerces': ['Shopee', 'Mercado Livre', 'Tiny', 'Outro'],
            'accounts': ['Conta Padrão', 'Conta Secundária']
        }

def get_xlsx_config():
    """
    Retorna as configurações XLSX (e-commerces e contas) da memória.
    """
    return _in_memory_xlsx_config

def update_xlsx_config(new_config):
    """
    Atualiza as configurações XLSX em memória e no Firestore.
    """
    global _in_memory_xlsx_config
    _in_memory_xlsx_config = {
        'ecommerces': list(new_config.get('ecommerces', [])),
        'accounts': list(new_config.get('accounts', []))
    }
    print(f"DEBUG (app_config_data.py): Configurações XLSX atualizadas em memória para: {_in_memory_xlsx_config}")

    if db:
        try:
            doc_ref = db.collection(CONFIGURATIONS_COLLECTION).document('xlsx_config')
            doc_ref.set(_in_memory_xlsx_config, merge=True)
            print(f"DEBUG (app_config_data.py): Configurações XLSX salvas no Firestore.")
            return True
        except Exception as e:
            print(f"ERRO (app_config_data.py): Falha ao salvar configurações XLSX no Firestore: {e}")
            return False
    else:
        print("AVISO (app_config_data.py): Firestore não conectado. Configurações XLSX não serão salvas no Firestore.")
        return False

def _load_mapping_from_firestore(map_name, default_map, global_var):
    """
    Função auxiliar para carregar um mapa de mapeamento específico do Firestore.
    """
    if not db:
        print(f"Firestore não conectado. Não é possível carregar o mapa '{map_name}'.")
        return

    try:
        doc_ref = db.collection(CONFIGURATIONS_COLLECTION).document(map_name)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            global_var.clear()
            global_var.update(data.get('map', {}))
            print(f"DEBUG (app_config_data.py): Mapa '{map_name}' carregado do Firestore: {global_var}")
        else:
            print(f"AVISO (app_config_data.py): Documento '{map_name}' não encontrado. Usando padrão e salvando.")
            global_var.clear()
            global_var.update(default_map)
            _update_mapping_in_firestore(map_name, global_var)
    except Exception as e:
        print(f"ERRO: Falha ao carregar o mapa '{map_name}' do Firestore: {e}")
        global_var.clear()
        global_var.update(default_map)

def _update_mapping_in_firestore(map_name, map_data):
    """
    Função auxiliar para atualizar um mapa de mapeamento específico no Firestore.
    """
    if not db:
        print(f"Firestore não conectado. Não é possível salvar o mapa '{map_name}'.")
        return False
    try:
        doc_ref = db.collection(CONFIGURATIONS_COLLECTION).document(map_name)
        doc_ref.set({'map': map_data}, merge=True)
        print(f"DEBUG (app_config_data.py): Mapa '{map_name}' salvo no Firestore.")
        return True
    except Exception as e:
        print(f"ERRO (app_config_data.py): Falha ao salvar o mapa '{map_name}' no Firestore: {e}")
        return False

# Funções GET para os mapeamentos
def get_cores_map():
    return dict(_in_memory_cores_map)

def get_formato_map():
    return dict(_in_memory_formato_map)

def get_furos_map():
    return dict(_in_memory_furos_map)

def get_variacoes_map():
    return dict(_in_memory_variacoes_map)

# Funções UPDATE para os mapeamentos
def update_cores_map(new_map):
    global _in_memory_cores_map
    _in_memory_cores_map.clear()
    _in_memory_cores_map.update(new_map)
    return _update_mapping_in_firestore('cores_map', _in_memory_cores_map)

def update_formato_map(new_map):
    global _in_memory_formato_map
    _in_memory_formato_map.clear()
    _in_memory_formato_map.update(new_map)
    return _update_mapping_in_firestore('formato_map', _in_memory_formato_map)

def update_furos_map(new_map):
    global _in_memory_furos_map
    _in_memory_furos_map.clear()
    _in_memory_furos_map.update(new_map)
    return _update_mapping_in_firestore('furos_map', _in_memory_furos_map)

def update_variacoes_map(new_map):
    global _in_memory_variacoes_map
    _in_memory_variacoes_map.clear()
    _in_memory_variacoes_map.update(new_map)
    return _update_mapping_in_firestore('variacoes_map', _in_memory_variacoes_map)

# Mapeamentos padrão (para inicialização se não existirem no Firestore)
DEFAULT_CORES_MAP = {
    "DOU": "Dourado", "PRA": "Prata", "ROS": "Rose", "CRU": "Cru",
    "BRA": "Branco", "TRA": "Transparente"
}

DEFAULT_FORMATO_MAP = {
    "REDO": "Redondo", "AVIA": "Aviãozinho", "CORA": "Coração",
    "PLAC": "Plaquinha", "MOLD": "Moldurinha", "NUVM": "Nuvenzinha",
    "NUVE": "Nuvem", "PLAO": "Plaquinha Oval", "PLAR": "Plaquinha com bolinha redonda no começo",
    "URSI": "Ursinho", "PING": "Pingente", "BORB": "Borboleta",
    "BO3D": "Borboleta 3D", "PROT": "Passante retangular oval no topo",
    "FLOP": "Flor Passante", "APCA": "Aplique Casamento", "MIPA": "Mini Palito"
}

DEFAULT_FUROS_MAP = {
    "1FS": "1 furo Superior", "1FH": "1 Furo Lateral", "2FH": "2 Furos Lateral",
    "2FV": "2 Furos Vertical", "4FL": "4 Furos, 2 na horizontal e 2 na vertical",
    "4FC": "4 Furos nos cantos", "0SF": "SEM FURO", "2PV": "DOIS FUROS PASSANTES VERTICAL",
    "1PC": "UM PASSANTE NO CENTRO"
}

DEFAULT_VARIACOES_MAP = {
    "0001F": "Escrita/Logo", "0002F": "Ramo coração data", "0003F": "Três Corações data",
    "0004F": "Coração Barra data", "0005F": "Coração Barra", "0006F": "Três corações",
    "0007F": "&", "0008F": "& e data", "0009F": "Cheguei", "0010F": "Escrita+Estrelas",
    "0011F": "Chá do", "0012F": "Escrita+Corações", "1001P": "Gratidão",
    "1002P": "Você é especial", "1003P": "Você é especial", "1004P": "Feito a mão com coração vazado no meio",
    "1005P": "Feito com amor + novelo", "1006P": "Caderneta de Saúde", "1007P": "Feliz dia das Mães",
    "1008P": "Ramo de flor 1", "1009P": "Feito com amor", "1010P": "Feliz Páscoa",
    "1011P": "Gratidão modelo 2", "1012P": "Fé", "1013P": "Coração", "0000P": "Sem gravação", "0000F": "Sem gravação"
}


# Inicializa as configurações em memória ao carregar o módulo
if db:
    _load_situacao_options_from_firestore()
    _load_xlsx_config_from_firestore()
    _load_mapping_from_firestore('cores_map', DEFAULT_CORES_MAP, _in_memory_cores_map)
    _load_mapping_from_firestore('formato_map', DEFAULT_FORMATO_MAP, _in_memory_formato_map)
    _load_mapping_from_firestore('furos_map', DEFAULT_FUROS_MAP, _in_memory_furos_map)
    _load_mapping_from_firestore('variacoes_map', DEFAULT_VARIACOES_MAP, _in_memory_variacoes_map)
