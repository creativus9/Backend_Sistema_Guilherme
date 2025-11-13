# backend-shopee/order_operations.py
# Módulo para operações de alto nível em pedidos (importação, atualização, exclusão).
# ATUALIZADO: import_xlsx_data agora verifica IDs duplicados antes de salvar.
# ATUALIZADO: Corrigida importação circular movendo 'add_import_to_history' para dentro da função.

from firebase_config import db # Importa a instância do Firestore
from importers.xlsx_importer import process_xlsx_file
from order_data_storage import ( # Importa funções do módulo de armazenamento
    ACTIVE_ORDERS_COLLECTION,
    _archive_old_orders_to_firestore,
    add_or_update_pedidos_in_memory,
    remove_pedidos_from_memory,
    update_pedido_field_in_memory,
    _parse_date_str, # Importa a função auxiliar de data
    get_pedidos # ADICIONADO: Necessário para verificar duplicados
)
# REMOVIDO: Importação circular movida para dentro da função
# from import_history_data import add_import_to_history 
from firebase_admin import firestore # Necessário para firestore.SERVER_TIMESTAMP
from datetime import datetime, timedelta 
import traceback 

# Nomes das coleções no Firestore
IMPORT_HISTORY_COLLECTION = 'import_history' # Mantido, embora add_import_to_history o defina

# --- FUNÇÃO import_xlsx_data ATUALIZADA ---
def import_xlsx_data(file_stream, delivery_date_str, ecommerce, conta_ecommerce):
    """
    Processa um arquivo XLSX, verifica IDs duplicados, salva novos pedidos 
    no Firestore e em memória, e registra a importação no histórico.

    Retorna (success, message, ignored_count)
    """
    try:
        # 1. Buscar todos os pedidos existentes para esta data de entrega
        #    Usamos a função de order_data_storage, que busca da memória (cache)
        pedidos_existentes = get_pedidos(delivery_date_str)
        
        # 2. Criar um conjunto (Set) com os IDs base para verificação rápida
        existing_base_ids = set([pedido['id'].split(' (')[0] for pedido in pedidos_existentes])
        print(f"DEBUG (import_xlsx_data): {len(existing_base_ids)} IDs base existentes encontrados para {delivery_date_str}.")

        # 3. Processar o arquivo XLSX para obter a lista de todos os pedidos que ele contém
        all_pedidos_from_file = process_xlsx_file(file_stream, delivery_date_str, ecommerce, conta_ecommerce)

        if not all_pedidos_from_file:
            print("AVISO (import_xlsx_data): process_xlsx_file não retornou pedidos.")
            return False, "Nenhum pedido válido encontrado no arquivo.", 0

        pedidos_para_adicionar = []
        pedidos_ignorados = []

        # 4. Filtrar a lista: separar pedidos novos de pedidos ignorados
        for pedido in all_pedidos_from_file:
            base_id_do_pedido = pedido['id'].split(' (')[0]
            
            if base_id_do_pedido in existing_base_ids:
                pedidos_ignorados.append(base_id_do_pedido)
            else:
                pedidos_para_adicionar.append(pedido)
                existing_base_ids.add(base_id_do_pedido) # Evita duplicatas do próprio arquivo

        ignored_count = len(set(pedidos_ignorados)) # Conta IDs únicos ignorados

        # 5. Salvar os novos pedidos (se houver)
        if not pedidos_para_adicionar:
            print(f"AVISO (import_xlsx_data): Nenhum pedido novo para adicionar. {ignored_count} ignorados.")
            if ignored_count > 0:
                return False, f"Todos os {ignored_count} pedido(s) encontrados no arquivo já existem para esta data. Nenhum pedido foi importado.", ignored_count
            else:
                return False, "Nenhum pedido encontrado no arquivo.", 0
        
        # 6. Adicionar/atualizar pedidos na memória
        add_or_update_pedidos_in_memory(delivery_date_str, pedidos_para_adicionar)
        
        # 7. Salvar em batch no Firestore
        pedidos_ids_adicionados = []
        if db:
            batch = db.batch()
            for pedido in pedidos_para_adicionar:
                pedido_id = pedido.get('id')
                if pedido_id:
                    doc_ref = db.collection(ACTIVE_ORDERS_COLLECTION).document(str(pedido_id))
                    batch.set(doc_ref, pedido, merge=True)
                    pedidos_ids_adicionados.append(pedido_id)
                else:
                    print(f"AVISO (order_operations.py): Pedido sem ID encontrado durante importação: {pedido}")
            
            try:
                batch.commit()
                print(f"DEBUG (order_operations.py): {len(pedidos_ids_adicionados)} pedidos salvos/atualizados no Firestore.")
            except Exception as e:
                print(f"ERRO (order_operations.py): Falha ao salvar lote de pedidos no Firestore: {e}")
                # Continua para salvar o histórico mesmo se o batch falhar?
                # Por enquanto, sim, mas retorna erro.
                return False, f"Erro ao salvar pedidos no Firestore: {e}", ignored_count
        else:
            print("AVISO (order_operations.py): Firestore não conectado. Pedidos ativos não serão salvos.")
            pedidos_ids_adicionados = [p['id'] for p in pedidos_para_adicionar if 'id' in p] # Simula para histórico

        # 8. Salvar no histórico de importação
        try:
            # ADICIONADO: Importação movida para dentro da função para quebrar ciclo
            from import_history_data import add_import_to_history 
            
            add_import_to_history(
                delivery_date_str, 
                ecommerce, 
                conta_ecommerce, 
                len(pedidos_ids_adicionados), 
                pedidos_ids_adicionados
            )
            print(f"DEBUG (order_operations.py): Registro de importação salvo.")
        except Exception as hist_e:
            print(f"ERRO (order_operations.py): Falha ao salvar registro de importação: {hist_e}")
            # Não falha a importação inteira, apenas registra o erro
        
        # 9. Arquivar pedidos antigos (lógica existente)
        current_delivery_date_obj = _parse_date_str(delivery_date_str)
        if current_delivery_date_obj:
            cutoff_date = current_delivery_date_obj - timedelta(days=4) 
            _archive_old_orders_to_firestore(cutoff_date)
        
        # 10. Criar mensagem de sucesso
        success_count = len(pedidos_ids_adicionados)
        message = f"{success_count} pedido(s) importado(s) com sucesso."
        
        if ignored_count > 0:
            message += f" {ignored_count} pedido(s) foram ignorados pois já existiam para esta data."
            
        return True, message, ignored_count

    except Exception as e:
        print(f"ERRO (import_xlsx_data): Falha crítica ao importar dados: {e}")
        traceback.print_exc()
        return False, f"Erro interno ao processar o arquivo: {str(e)}", 0

# --- FUNÇÕES RESTANTES (Sem modificação) ---

def update_pedido_field(pedido_id, data_entrega_str, field_name, new_value):
    """
    Atualiza um campo de um pedido no Firestore e depois atualiza o cache em memória para consistência.
    """
    if not db:
        print("AVISO (order_operations.py): Firestore não conectado. Campo não será atualizado.")
        return False

    try:
        # 1. Atualiza no Firestore (fonte da verdade)
        doc_ref = db.collection(ACTIVE_ORDERS_COLLECTION).document(str(pedido_id))
        if not doc_ref.get().exists:
            print(f"AVISO (order_operations.py): Pedido '{pedido_id}' não encontrado no Firestore para atualização.")
            return False
            
        doc_ref.update({field_name: new_value})
        print(f"DEBUG (order_operations.py): Campo '{field_name}' do pedido '{pedido_id}' atualizado no Firestore.")

        # 2. Atualiza em memória para manter a consistência
        success_memory = update_pedido_field_in_memory(pedido_id, data_entrega_str, field_name, new_value)
        if success_memory:
            print(f"DEBUG (order_operations.py): Cache em memória para pedido '{pedido_id}' atualizado.")
        else:
            print(f"AVISO (order_operations.py): Pedido '{pedido_id}' com data '{data_entrega_str}' não encontrado no cache em memória para atualização (pode ser normal se adicionado por webhook).")

        return True
    except Exception as e:
        print(f"ERRO (order_operations.py): Falha ao atualizar campo '{field_name}' do pedido '{pedido_id}' no Firestore: {e}")
        return False

def delete_single_pedido(pedido_id, data_entrega_str):
    """
    Deleta um único pedido diretamente no Firestore e depois remove do cache em memória para manter a consistência.
    O parâmetro data_entrega_str é mantido por compatibilidade com a rota.
    """
    if not db:
        print("AVISO (order_operations.py): Firestore não conectado. Pedido não será deletado.")
        return False
        
    try:
        doc_ref = db.collection(ACTIVE_ORDERS_COLLECTION).document(str(pedido_id))
        
        # Firestore é a fonte da verdade. Verifica se o pedido existe lá.
        if not doc_ref.get().exists:
            print(f"AVISO (order_operations.py): Pedido '{pedido_id}' não encontrado no Firestore. Nenhuma ação realizada.")
            # Se não existe no Firestore, pode ser que ainda esteja na memória desatualizada. Tenta limpar.
            remove_pedidos_from_memory([pedido_id], data_entrega_str)
            return False 

        # Deleta do Firestore
        doc_ref.delete()
        print(f"DEBUG (order_operations.py): Pedido '{pedido_id}' excluído do Firestore.")
        
        # Remove da memória para manter a consistência
        remove_pedidos_from_memory([pedido_id], data_entrega_str)
        print(f"DEBUG (order_operations.py): Pedido '{pedido_id}' removido do cache em memória.")

        return True
    except Exception as e:
        print(f"ERRO (order_operations.py): Falha ao deletar pedido '{pedido_id}' do Firestore: {e}")
        traceback.print_exc()
        return False


def delete_multiple_pedidos(pedido_ids):
    """
    Deleta múltiplos pedidos diretamente no Firestore usando um lote e depois remove do cache em memória.
    Retorna a contagem de pedidos que foram solicitados para exclusão.
    """
    if not pedido_ids:
        return 0

    if not db:
        print("AVISO (order_operations.py): Firestore não conectado. Pedidos não serão deletados.")
        return 0

    # 1. Deleta do Firestore
    batch = db.batch()
    for pedido_id in pedido_ids:
        doc_ref = db.collection(ACTIVE_ORDERS_COLLECTION).document(str(pedido_id))
        batch.delete(doc_ref)
    
    try:
        batch.commit()
        print(f"DEBUG (order_operations.py): Lote de exclusão para {len(pedido_ids)} pedidos enviado ao Firestore.")
    except Exception as e:
        print(f"ERRO (order_operations.py): Falha ao deletar lote de pedidos do Firestore: {e}")
        traceback.print_exc()
        return 0 # Retorna 0 se o commit falhar

    # 2. Remove da memória para manter a consistência
    # O segundo argumento (data_entrega_str) é None, o que faz a função procurar em todas as datas.
    removed_count_memory = remove_pedidos_from_memory(pedido_ids)
    print(f"DEBUG (order_operations.py): {removed_count_memory} pedidos removidos do cache em memória.")

    return len(pedido_ids) # Retorna a contagem de operações de exclusão bem-sucedidas no Firestore.

