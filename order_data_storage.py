# backend-shopee/order_data_storage.py
# Módulo para gerenciar o armazenamento em memória dos pedidos, carga inicial e arquivamento.

from datetime import datetime, timedelta
import traceback
from firebase_admin import firestore
from firebase_config import db # Importa a instância do Firestore

# Nomes das coleções no Firestore
ACTIVE_ORDERS_COLLECTION = 'pedidos_ativos'
ARCHIVED_ORDERS_COLLECTION = 'pedidos_arquivados' # Nova coleção para pedidos arquivados

# --- Armazenamento de Pedidos em Memória ---
_in_memory_pedidos_by_date = {}

# --- Funções de Ajuda Internas ---
def _parse_date_str(date_str):
    """Converte string 'DD/MM/YYYY' para objeto datetime.date."""
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        return None

def _format_date_to_str(date_obj):
    """Converte objeto datetime.date para string 'DD/MM/YYYY'."""
    return date_obj.strftime('%d/%m/%Y')

# --- Funções de Gerenciamento de Pedidos em Memória e Firestore ---

def _load_active_orders_from_firestore():
    """
    Carrega pedidos ativos do Firestore para o armazenamento em memória na inicialização.
    """
    global _in_memory_pedidos_by_date
    _in_memory_pedidos_by_date = {} 

    if not db:
        print("Firestore não conectado. Não é possível carregar pedidos ativos.")
        return

    print("Carregando pedidos ativos do Firestore para a memória...")
    try:
        docs = db.collection(ACTIVE_ORDERS_COLLECTION).stream()

        for doc in docs:
            pedido = doc.to_dict()
            pedido['id'] = doc.id 
            data_entrega = pedido.get('dataEntrega')
            if data_entrega:
                if data_entrega not in _in_memory_pedidos_by_date:
                    _in_memory_pedidos_by_date[data_entrega] = []
                _in_memory_pedidos_by_date[data_entrega].append(pedido)
        print(f"DEBUG (order_data_storage.py): {sum(len(v) for v in _in_memory_pedidos_by_date.values())} pedidos ativos carregados do Firestore.")
    except Exception as e:
        print(f"ERRO (order_data_storage.py): Falha ao carregar pedidos ativos do Firestore: {e}")

def _archive_old_orders_to_firestore(cutoff_date):
    """
    Move pedidos mais antigos que a data de corte do armazenamento em memória para o Firestore.
    """
    if not db:
        print("Firestore não conectado. Não é possível arquivar pedidos.")
        return

    dates_to_archive = []
    # Cria uma cópia das chaves para evitar problemas de modificação durante a iteração
    for date_str in list(_in_memory_pedidos_by_date.keys()):
        pedidos_list = _in_memory_pedidos_by_date[date_str]
        date_obj = _parse_date_str(date_str)
        if date_obj and date_obj < cutoff_date:
            print(f"Arquivando pedidos da data {date_str} para a coleção de arquivados...")
            batch = db.batch()
            for pedido in pedidos_list:
                try:
                    pedido_id = pedido.get('id')
                    if pedido_id:
                        # Remove do 'pedidos_ativos' e adiciona ao 'pedidos_arquivados'
                        active_doc_ref = db.collection(ACTIVE_ORDERS_COLLECTION).document(str(pedido_id))
                        archived_doc_ref = db.collection(ARCHIVED_ORDERS_COLLECTION).document(str(pedido_id))
                        batch.delete(active_doc_ref)
                        batch.set(archived_doc_ref, pedido, merge=True) 
                    else:
                        print(f"AVISO (order_data_storage.py): Pedido sem ID encontrado na data {date_str}. Não arquivado: {pedido}")
                except Exception as e:
                    print(f"ERRO (order_data_storage.py): Falha ao adicionar pedido {pedido.get('id', 'N/A')} ao lote de arquivamento: {e}")
            
            try:
                batch.commit()
                print(f"DEBUG (order_data_storage.py): Lote de pedidos da data {date_str} arquivado com sucesso.")
                dates_to_archive.append(date_str)
            except Exception as e:
                print(f"ERRO (order_data_storage.py): Falha ao commitar lote de arquivamento para {date_str}: {e}")
    
    for date_str in dates_to_archive:
        del _in_memory_pedidos_by_date[date_str]
        print(f"DEBUG (order_data_storage.py): Pedidos da data {date_str} removidos da memória.")

def get_pedidos(delivery_date_str=None):
    """
    Busca pedidos do armazenamento em memória para a data de entrega especificada.
    Se delivery_date_str for None, retorna todos os pedidos em memória.
    """
    if delivery_date_str:
        print(f"DEBUG (order_data_storage.py): Buscando pedidos em memória para a data: {delivery_date_str}")
        return _in_memory_pedidos_by_date.get(delivery_date_str, [])
    else:
        all_pedidos = []
        for date_list in _in_memory_pedidos_by_date.values():
            all_pedidos.extend(date_list)
        print(f"DEBUG (order_data_storage.py): Buscando todos os pedidos em memória. Total: {len(all_pedidos)}")
        return all_pedidos

def add_or_update_pedidos_in_memory(delivery_date_str, processed_pedidos):
    """
    Adiciona ou atualiza uma lista de pedidos no armazenamento em memória.
    """
    if delivery_date_str not in _in_memory_pedidos_by_date:
        _in_memory_pedidos_by_date[delivery_date_str] = []
    
    for new_pedido in processed_pedidos:
        found = False
        for i, existing_pedido in enumerate(_in_memory_pedidos_by_date[delivery_date_str]):
            if existing_pedido.get('id') == new_pedido.get('id'):
                _in_memory_pedidos_by_date[delivery_date_str][i] = new_pedido 
                found = True
                break
        if not found:
            _in_memory_pedidos_by_date[delivery_date_str].append(new_pedido) 
    print(f"DEBUG (order_data_storage.py): {len(processed_pedidos)} pedidos processados e atualizados/adicionados em memória para a data {delivery_date_str}.")

def remove_pedidos_from_memory(pedido_ids, data_entrega_str=None):
    """
    Remove pedidos específicos do armazenamento em memória.
    Se data_entrega_str for fornecido, remove apenas daquela data.
    Caso contrário, busca e remove de todas as datas.
    Retorna a contagem de pedidos removidos da memória.
    """
    removed_count = 0
    ids_to_remove_set = set(pedido_ids)

    if data_entrega_str:
        if data_entrega_str in _in_memory_pedidos_by_date:
            initial_len = len(_in_memory_pedidos_by_date[data_entrega_str])
            _in_memory_pedidos_by_date[data_entrega_str] = [
                p for p in _in_memory_pedidos_by_date[data_entrega_str]
                if p['id'] not in ids_to_remove_set
            ]
            removed_count = initial_len - len(_in_memory_pedidos_by_date[data_entrega_str])
            if not _in_memory_pedidos_by_date[data_entrega_str]:
                del _in_memory_pedidos_by_date[data_entrega_str]
                print(f"DEBUG (order_data_storage.py): Lista de pedidos para {data_entrega_str} removida da memória (vazia).")
            print(f"DEBUG (order_data_storage.py): {removed_count} pedidos removidos da memória para a data {data_entrega_str}.")
    else:
        # Remove de todas as datas
        for date_str in list(_in_memory_pedidos_by_date.keys()):
            initial_len = len(_in_memory_pedidos_by_date[date_str])
            _in_memory_pedidos_by_date[date_str] = [
                p for p in _in_memory_pedidos_by_date[date_str]
                if p['id'] not in ids_to_remove_set
            ]
            removed_count += (initial_len - len(_in_memory_pedidos_by_date[date_str]))
            if not _in_memory_pedidos_by_date[date_str]:
                del _in_memory_pedidos_by_date[date_str]
                print(f"DEBUG (order_data_storage.py): Lista de pedidos para {date_str} removida da memória (vazia).")
        print(f"DEBUG (order_data_storage.py): {removed_count} pedidos removidos da memória (todas as datas).")
    
    return removed_count


def update_pedido_field_in_memory(pedido_id, data_entrega_str, field_name, new_value):
    """
    Atualiza um campo específico de um pedido no armazenamento em memória.
    """
    if data_entrega_str not in _in_memory_pedidos_by_date:
        print(f"AVISO (order_data_storage.py): Data de entrega '{data_entrega_str}' não encontrada na memória para atualização do pedido '{pedido_id}'.")
        return False

    found = False
    for i, pedido in enumerate(_in_memory_pedidos_by_date[data_entrega_str]):
        if pedido.get('id') == pedido_id:
            _in_memory_pedidos_by_date[data_entrega_str][i][field_name] = new_value
            found = True
            print(f"DEBUG (order_data_storage.py): Campo '{field_name}' do pedido '{pedido_id}' atualizado para '{new_value}' em memória.")
            break
    return found

# --- Funções para Firestore (mantidas para webhooks e arquivamento) ---
# Estas funções operam na coleção 'pedidos' (geral), não 'pedidos_ativos'.
# Podem ser movidas para um módulo separado de "external_integrations" se houver mais webhooks
# ou se forem consideradas operações menos "core" para o gerenciamento diário de pedidos.

def add_pedido_firestore_general(pedido_data):
    """
    Adiciona um novo pedido ao Firestore na coleção 'pedidos' (para webhooks/futuro).
    """
    if db:
        try:
            doc_ref = db.collection('pedidos').add(pedido_data)
            print(f"Pedido adicionado ao Firestore (coleção 'pedidos') com ID: {doc_ref[1].id}")
            return pedido_data
        except Exception as e:
            print(f"Erro ao adicionar pedido ao Firestore (coleção 'pedidos'): {e}")
            return None
    else:
        print("Firestore não conectado. Não é possível adicionar pedidos na coleção 'pedidos'.")
        return None

def save_shopee_order_firestore_general(shopee_order_id, pedido_data):
    """
    Salva ou atualiza um pedido no Firestore na coleção 'pedidos' (para webhooks/futuro).
    """
    if db:
        try:
            doc_ref = db.collection('pedidos').document(str(shopee_order_id))
            doc_ref.set(pedido_data, merge=True)
            print(f"Pedido Shopee {shopee_order_id} salvo/atualizado no Firestore (coleção 'pedidos').")
            return True
        except Exception as e:
            print(f"Erro ao salvar/atualizar pedido Shopee {shopee_order_id} no Firestore (coleção 'pedidos'): {e}")
            return False
    else:
        print("Firestore não conectado. Não é possível salvar/atualizar pedidos na coleção 'pedidos'.")
        return False

def update_pedido_firestore_general(pedido_id, new_data):
    """
    Atualiza um pedido existente no Firestore na coleção 'pedidos' (para futuro).
    """
    if db:
        try:
            doc_ref = db.collection('pedidos').document(pedido_id)
            doc_ref.update(new_data)
            print(f"Pedido {pedido_id} atualizado com sucesso no Firestore (coleção 'pedidos').")
            return True
        except Exception as e:
            print(f"Erro ao atualizar pedido {pedido_id} no Firestore (coleção 'pedidos'): {e}")
            return False
    else:
        print("Firestore não conectado. Não é possível atualizar pedidos na coleção 'pedidos'.")
        return False

def delete_pedido_firestore_general(pedido_id):
    """
    Deleta um pedido do Firestore na coleção 'pedidos' (para futuro).
    """
    if db:
        try:
            db.collection('pedidos').document(pedido_id).delete()
            print(f"Pedido {pedido_id} deletado do Firestore (coleção 'pedidos') com sucesso.")
            return True
        except Exception as e:
            print(f"Erro ao deletar pedido {pedido_id} do Firestore (coleção 'pedidos'): {e}")
            return False
    else:
        print("Firestore não conectado. Não é possível deletar pedidos na coleção 'pedidos'.")
        return False

# Inicializa pedidos ativos em memória ao carregar o módulo
if db:
    _load_active_orders_from_firestore()
