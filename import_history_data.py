# backend-shopee/import_history_data.py
# Módulo para gerenciamento do histórico de importações.
# ATUALIZADO: Corrigida importação circular movendo 'delete_multiple_pedidos' para dentro da função.
# ADICIONADO: Nova função 'add_import_to_history'.

from datetime import datetime
import traceback
from firebase_admin import firestore # Necessário para firestore.Query.DESCENDING
from firebase_config import db # Importa a instância do Firestore

# REMOVIDO: Importação circular movida para dentro da função
# from order_operations import delete_multiple_pedidos 

IMPORT_HISTORY_COLLECTION = 'import_history'

def add_import_to_history(data_entrega, ecommerce, conta_ecommerce, quantidade_pedidos, pedidos_ids):
    """
    Adiciona um novo registro ao histórico de importações no Firestore.
    """
    if not db:
        print("AVISO (import_history_data.py): Firestore não conectado. Histórico de importação não será salvo.")
        # Levanta um erro para que o chamador (order_operations) saiba que falhou
        raise ConnectionError("Firestore não conectado. Não é possível salvar o histórico.")

    try:
        import_timestamp = datetime.now() # Usa o timestamp do servidor
        history_record = {
            'timestamp': import_timestamp,
            'quantidade_pedidos': quantidade_pedidos,
            'data_entrega': data_entrega,
            'ecommerce': ecommerce,
            'conta_ecommerce': conta_ecommerce,
            'pedidos_ids': pedidos_ids
        }
        db.collection(IMPORT_HISTORY_COLLECTION).add(history_record)
        print(f"DEBUG (import_history_data.py): Registro de importação salvo no Firestore: {import_timestamp}")
    except Exception as e:
        print(f"ERRO (import_history_data.py): Falha ao salvar registro de importação no Firestore: {e}")
        traceback.print_exc()
        # Propaga o erro para que o chamador saiba que falhou
        raise e

def get_import_history():
    """
    Busca o histórico de importações do Firestore.
    """
    if not db:
        print("Firestore não conectado. Não é possível buscar histórico de importações.")
        return []
    try:
        history_docs = db.collection(IMPORT_HISTORY_COLLECTION).order_by('timestamp', direction=firestore.Query.DESCENDING).get()
        history_list = []
        for doc in history_docs:
            data = doc.to_dict()
            data['id'] = doc.id
            # Verifica se 'timestamp' existe e é um objeto datetime
            if 'timestamp' in data and hasattr(data['timestamp'], 'strftime'):
                data['timestamp_formatted'] = data['timestamp'].strftime('%d/%m/%Y %H:%M:%S')
            else:
                data['timestamp_formatted'] = 'N/A'
            history_list.append(data)
        print(f"DEBUG (import_history_data.py): {len(history_list)} registros de importação encontrados.")
        return history_list
    except Exception as e:
        print(f"ERRO (import_history_data.py): Falha ao buscar histórico de importações do Firestore: {e}")
        return []

def delete_orders_by_import_id(import_doc_id):
    """
    Deleta um lote de pedidos com base em um registro de importação do histórico.
    Remove os pedidos da memória e também do Firestore (pedidos ativos e registro histórico).
    """
    if not db:
        print("Firestore não conectado. Não é possível deletar pedidos por ID de importação.")
        return False
    try:
        # ADICIONADO: Importação movida para dentro da função para quebrar ciclo
        from order_operations import delete_multiple_pedidos 

        import_ref = db.collection(IMPORT_HISTORY_COLLECTION).document(import_doc_id)
        import_doc = import_ref.get() # Pega o documento

        if not import_doc.exists:
            print(f"AVISO (import_history_data.py): Registro de importação com ID '{import_doc_id}' não encontrado.")
            return False
        
        import_data = import_doc.to_dict()
        pedidos_to_delete_ids = import_data.get('pedidos_ids', [])
        
        if pedidos_to_delete_ids:
            # Chama a função de order_operations para deletar os pedidos ativos
            deleted_count = delete_multiple_pedidos(pedidos_to_delete_ids)
            print(f"DEBUG (import_history_data.py): {deleted_count} pedidos associados à importação '{import_doc_id}' foram solicitados para exclusão.")

        # Deleta o registro do histórico
        import_ref.delete()
        print(f"DEBUG (import_history_data.py): Registro de importação '{import_doc_id}' removido com sucesso.")
        return True
    except Exception as e:
        print(f"ERRO (import_history_data.py): Falha ao deletar importação por ID '{import_doc_id}': {e}")
        traceback.print_exc()
        return False
