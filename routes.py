# backend-shopee/routes.py
# ATUALIZADO: Rota /import-xlsx agora retorna uma mensagem detalhada 
# e contagem de sucesso/ignorados.

from flask import request, jsonify
from flask_cors import CORS 

# ... (outros imports existentes) ...
from order_data_storage import get_pedidos 
from order_operations import ( 
    import_xlsx_data, 
    update_pedido_field, 
    delete_single_pedido, 
    delete_multiple_pedidos,
)
from import_history_data import ( 
    get_import_history,
    delete_orders_by_import_id
)
from app_config_data import ( 
    get_situacao_options,
    update_situacao_options,
    get_xlsx_config,
    update_xlsx_config,
    get_cores_map, 
    update_cores_map, 
    get_formato_map, 
    update_formato_map, 
    get_furos_map, 
    update_furos_map, 
    get_variacoes_map, 
    update_variacoes_map 
)
from user_auth import ( 
    create_user,
    verify_user,
)
from user_profile_data import get_user_profile, update_user_profile 
from storage_operations import upload_profile_picture 
from Ler_Etiqueta.processador_zpl import converter_zpl_para_imagem_base64

# --- ATUALIZADO: Importa a nova função de conversão de imagem ---
from Ler_Etiqueta.gerador_zpl_lista import gerar_zpl_de_imagem_base64

def register_routes(app):
    """
    Registra todas as rotas da API na aplicação Flask.
    """
    CORS(app) 

    # --- Rota para visualizar etiqueta ZPL (existente) ---
    @app.route('/visualizar-etiqueta', methods=['POST'])
    def visualizar_etiqueta_route():
        data = request.json
        zpl_data = data.get('zpl_data')

        if not zpl_data:
            return jsonify(message="Nenhum dado ZPL fornecido."), 400

        try:
            imagem_base64 = converter_zpl_para_imagem_base64(zpl_data)
            if imagem_base64:
                return jsonify(imageUrl=imagem_base64), 200
            else:
                return jsonify(message="Falha ao converter ZPL. O formato pode ser inválido ou não conter imagem."), 400
        except Exception as e:
            app.logger.error(f"Erro na rota /visualizar-etiqueta: {e}")
            return jsonify(message=f"Erro interno ao processar ZPL: {str(e)}"), 500

    # --- ROTA ATUALIZADA: Agora recebe uma imagem Base64 (WYSIWYG) ---
    @app.route('/gerar-zpl-lista', methods=['POST'])
    def gerar_zpl_lista_route():
        data = request.json
        # 1. Espera a imagem Base64 gerada pelo frontend
        imagem_base64 = data.get('imagem_base64')

        if not imagem_base64:
            return jsonify(message="Nenhuma imagem_base64 fornecida."), 400

        try:
            # 2. Chama a nova função de conversão
            zpl_string = gerar_zpl_de_imagem_base64(imagem_base64)
            
            if not zpl_string:
                 return jsonify(message="Falha ao gerar ZPL para a lista."), 500
            
            # 3. Retorna o ZPL como TEXTO PURO (o frontend espera response.text())
            if "^FDErro" in zpl_string:
                # Se a função de ZPL retornou um erro, envie-o como erro 500
                app.logger.error(f"Erro retornado por gerar_zpl_de_imagem_base64: {zpl_string}")
                return zpl_string, 500, {'Content-Type': 'text/plain; charset=utf-8'}
            else:
                # Sucesso, envia o ZPL
                return zpl_string, 200, {'Content-Type': 'text/plain; charset=utf-8'}

        except Exception as e:
            app.logger.error(f"Erro na rota /gerar-zpl-lista: {e}")
            return jsonify(message=f"Erro interno ao gerar ZPL da lista: {str(e)}"), 500


    # --- Rotas Existentes ---
    # ... (todas as outras rotas /pedidos, /import-history, etc. permanecem aqui) ...

    @app.route('/pedidos', methods=['GET'])
    def get_pedidos_route():
        data_entrega = request.args.get('data_entrega')
        pedidos = get_pedidos(data_entrega)
        return jsonify(pedidos)

    # --- ROTA /import-xlsx ATUALIZADA ---
    @app.route('/import-xlsx', methods=['POST'])
    def import_xlsx_route():
        if 'file' not in request.files:
            return jsonify(message="Nenhum arquivo enviado."), 400
        file = request.files['file']
        data_entrega = request.form.get('dataEntrega')
        ecommerce = request.form.get('ecommerce')
        conta_ecommerce = request.form.get('contaEcommerce')

        if not data_entrega or not ecommerce or not conta_ecommerce:
            return jsonify(message="Data de entrega, E-commerce e Conta do E-commerce são obrigatórios."), 400

        try:
            # ATUALIZADO: A função agora retorna (success, message, ignored_count)
            success, message, ignored_count = import_xlsx_data(file, data_entrega, ecommerce, conta_ecommerce)
            
            if success:
                # Retorna a mensagem detalhada e a contagem de ignorados
                return jsonify(
                    message=message, 
                    ignored_count=ignored_count
                ), 200
            else:
                # Retorna a mensagem de erro detalhada (ex: "Todos já existem")
                return jsonify(
                    message=message, 
                    ignored_count=ignored_count
                ), 400
        except Exception as e:
            app.logger.error(f"Erro ao importar XLSX: {e}")
            return jsonify(
                message=f"Erro interno ao processar o arquivo: {str(e)}",
                ignored_count=0
            ), 500
    # --- Fim da Rota /import-xlsx ATUALIZADA ---

    @app.route('/import-history', methods=['GET'])
    def get_import_history_route():
        history = get_import_history()
        # Formatação do timestamp deve ser tratada aqui ou no módulo de dados
        formatted_history = []
        for item in history:
            item_copy = item.copy()
            if 'timestamp' in item_copy and hasattr(item_copy['timestamp'], 'strftime'):
                 # Convert Firestore Timestamp to Python datetime if necessary before strftime
                 dt_object = item_copy['timestamp']
                 # Ensure it's a datetime object before formatting
                 if hasattr(dt_object, 'strftime'):
                     item_copy['timestamp_formatted'] = dt_object.strftime('%d/%m/%Y %H:%M:%S')
                 else:
                     item_copy['timestamp_formatted'] = str(dt_object) # Fallback to string representation
            elif 'timestamp_formatted' not in item_copy: 
                 item_copy['timestamp_formatted'] = 'N/A' 
            formatted_history.append(item_copy)
        return jsonify(formatted_history)


    @app.route('/import-history/<import_doc_id>', methods=['DELETE'])
    def delete_import_history_route(import_doc_id):
        try:
            success = delete_orders_by_import_id(import_doc_id)
            if success:
                return jsonify(message=f"Importação '{import_doc_id}' e pedidos associados excluídos com sucesso.")
            else:
                return jsonify(message=f"Falha ao excluir importação '{import_doc_id}' ou não encontrada."), 404
        except Exception as e:
            app.logger.error(f"Erro ao deletar importação: {e}")
            return jsonify(message=f"Erro interno ao excluir a importação: {str(e)}"), 500

    @app.route('/situacao-options', methods=['GET'])
    def get_situacao_options_route():
        options = get_situacao_options()
        return jsonify(options)

    @app.route('/situacao-options', methods=['PUT'])
    def update_situacao_options_route():
        new_options = request.json
        if not isinstance(new_options, list):
            return jsonify(message="Formato inválido. Esperado uma lista de opções."), 400
        
        success = update_situacao_options(new_options)
        if success:
            return jsonify(message="Opções de situação atualizadas com sucesso!")
        else:
            return jsonify(message="Falha ao atualizar opções de situação."), 500

    @app.route('/xlsx-config', methods=['GET'])
    def get_xlsx_config_route():
        config = get_xlsx_config()
        return jsonify(config)

    @app.route('/xlsx-config', methods=['PUT'])
    def update_xlsx_config_route():
        new_config = request.json
        if not isinstance(new_config, dict):
            return jsonify(message="Formato inválido. Esperado um objeto de configuração."), 400
        
        success = update_xlsx_config(new_config)
        if success:
            return jsonify(message="Configurações XLSX atualizadas com sucesso!")
        else:
            return jsonify(message="Falha ao atualizar configurações XLSX."), 500

    # Rotas para Mappings (Cores, Formato, Furos, Variacoes)
    @app.route('/mapping/cores', methods=['GET'])
    def get_cores_map_route():
        return jsonify(get_cores_map())

    @app.route('/mapping/cores', methods=['PUT'])
    def update_cores_map_route():
        new_map = request.json
        if not isinstance(new_map, dict): return jsonify(message="Formato inválido."), 400
        if update_cores_map(new_map): return jsonify(message="Mapeamento de Cores atualizado!")
        return jsonify(message="Falha ao atualizar mapeamento."), 500
    
    @app.route('/mapping/formato', methods=['GET'])
    def get_formato_map_route():
        return jsonify(get_formato_map())

    @app.route('/mapping/formato', methods=['PUT'])
    def update_formato_map_route():
        new_map = request.json
        if not isinstance(new_map, dict): return jsonify(message="Formato inválido."), 400
        if update_formato_map(new_map): return jsonify(message="Mapeamento de Formato atualizado!")
        return jsonify(message="Falha ao atualizar mapeamento."), 500

    @app.route('/mapping/furos', methods=['GET'])
    def get_furos_map_route():
        return jsonify(get_furos_map())

    @app.route('/mapping/furos', methods=['PUT'])
    def update_furos_map_route():
        new_map = request.json
        if not isinstance(new_map, dict): return jsonify(message="Formato inválido."), 400
        if update_furos_map(new_map): return jsonify(message="Mapeamento de Furos atualizado!")
        return jsonify(message="Falha ao atualizar mapeamento."), 500

    @app.route('/mapping/variacoes', methods=['GET'])
    def get_variacoes_map_route():
        return jsonify(get_variacoes_map())

    @app.route('/mapping/variacoes', methods=['PUT'])
    def update_variacoes_map_route():
        new_map = request.json
        if not isinstance(new_map, dict): return jsonify(message="Formato inválido."), 400
        if update_variacoes_map(new_map): return jsonify(message="Mapeamento de Variações atualizado!")
        return jsonify(message="Falha ao atualizar mapeamento."), 500


    @app.route('/pedidos/<string:pedido_id>/<string:field_name>', methods=['PATCH'])
    def update_pedido_field_route(pedido_id, field_name):
        data = request.json
        new_value = data.get('value')
        data_entrega = data.get('data_entrega') 

        if new_value is None: return jsonify(message=f"Valor para '{field_name}' não fornecido."), 400
        if not data_entrega: return jsonify(message="Data de entrega é obrigatória."), 400

        try:
            if update_pedido_field(pedido_id, data_entrega, field_name, new_value):
                return jsonify(message=f"Campo '{field_name}' atualizado.")
            else:
                return jsonify(message=f"Pedido '{pedido_id}' não encontrado ou falha."), 404
        except Exception as e:
            app.logger.error(f"Erro ao atualizar campo '{field_name}': {e}")
            return jsonify(message=f"Erro interno: {str(e)}"), 500

    @app.route('/pedidos/<string:pedido_id>', methods=['DELETE'])
    def delete_single_pedido_route(pedido_id):
        data = request.json
        data_entrega = data.get('data_entrega')

        if not data_entrega: return jsonify(message="Data de entrega é obrigatória."), 400

        try:
            if delete_single_pedido(pedido_id, data_entrega):
                return jsonify(message=f"Pedido '{pedido_id}' excluído.")
            else:
                return jsonify(message=f"Pedido '{pedido_id}' não encontrado ou falha."), 404
        except Exception as e:
            app.logger.error(f"Erro ao excluir pedido '{pedido_id}': {e}")
            return jsonify(message=f"Erro interno: {str(e)}"), 500

    @app.route('/pedidos/delete-multiple', methods=['DELETE'])
    def delete_multiple_pedidos_route():
        # ATENÇÃO: Esta rota precisa ser adaptada para receber 'data_entrega' para cada pedido ou
        # assumir uma única data se aplicável, pois delete_multiple_pedidos pode precisar dela.
        # A implementação atual de delete_multiple_pedidos pode não funcionar corretamente sem data_entrega.
        data = request.json
        pedido_ids = data.get('pedido_ids', [])
        # data_entrega = data.get('data_entrega') # Precisa decidir como passar a data aqui

        if not pedido_ids: return jsonify(message="Nenhum ID fornecido."), 400
        # if not data_entrega: return jsonify(message="Data de entrega é obrigatória."), 400

        try:
            # Precisa ajustar delete_multiple_pedidos para aceitar data_entrega
            # success_count = delete_multiple_pedidos(pedido_ids, data_entrega) 
            # Placeholder:
            return jsonify(message="Rota /delete-multiple precisa ser ajustada no backend para data_entrega."), 501
            # if success_count > 0:
            #     return jsonify(message=f"{success_count} pedido(s) excluído(s).")
            # else:
            #     return jsonify(message="Nenhum pedido encontrado ou falha."), 404
        except Exception as e:
            app.logger.error(f"Erro ao excluir múltiplos pedidos: {e}")
            return jsonify(message=f"Erro interno: {str(e)}"), 500


    # Rotas de Autenticação e Perfil
    @app.route('/register', methods=['POST'])
    def register_user_route():
        data = request.json
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')

        if not all([email, password, name]): return jsonify(message="E-mail, senha e nome são obrigatórios."), 400
        
        success, message = create_user(email, password, name)
        status_code = 201 if success else 409
        return jsonify(message=message), status_code

    @app.route('/login', methods=['POST'])
    def login_user_route():
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not all([email, password]): return jsonify(message="E-mail e senha são obrigatórios."), 400
        
        user_info = verify_user(email, password) # verify_user agora retorna um dict ou None
        if user_info:
            # Retorna email, role e name
            return jsonify(message="Login bem-sucedido!", **user_info), 200
        else:
            return jsonify(message="E-mail ou senha inválidos."), 401


    @app.route('/get_user_profile', methods=['POST'])
    def get_user_profile_route():
        data = request.json
        email = data.get('email')

        if not email: return jsonify(message="E-mail é obrigatório."), 400
        
        user_profile = get_user_profile(email)
        if user_profile:
            return jsonify(user_profile), 200
        else:
            # Retorna um perfil padrão se não encontrado, em vez de 404
             default_profile = {
                "name": email.split('@')[0], # Usa a parte local do email como nome padrão
                "nickname": "",
                "dob": "",
                "profilePictureUrl": "",
                "role": "user" # Assume role 'user' se não especificado
            }
             return jsonify(default_profile), 200
            # return jsonify(message="Perfil do usuário não encontrado."), 404

    @app.route('/update_profile', methods=['POST'])
    def update_profile_route():
        data = request.json
        email = data.get('email')
        # Pega os outros campos, permitindo que sejam None se não enviados
        name = data.get('name') 
        nickname = data.get('nickname')
        dob = data.get('dob')
        profile_picture_url = data.get('profilePictureUrl')

        if not email: return jsonify(message="E-mail é obrigatório."), 400

        success, message = update_user_profile(email, name, nickname, dob, profile_picture_url)
        if success:
            return jsonify(message=message), 200
        else:
            # Retorna 404 se o usuário não foi encontrado para atualização
             if "não encontrado" in message:
                 return jsonify(message=message), 404
             else:
                 return jsonify(message=message), 500


    @app.route('/upload_profile_picture', methods=['POST'])
    def upload_profile_picture_route():
        if 'profile_picture' not in request.files: return jsonify(message="Nenhum arquivo de imagem."), 400
        
        file = request.files['profile_picture']
        user_id = request.form.get('userId') 

        if not user_id: return jsonify(message="ID do usuário obrigatório."), 400
        if file.filename == '': return jsonify(message="Nenhum arquivo selecionado."), 400

        try:
            public_url = upload_profile_picture(file, user_id) # Passa só user_id agora
            if public_url:
                return jsonify(message="Upload bem-sucedido!", imageUrl=public_url), 200
            else:
                return jsonify(message="Falha no upload."), 500
        except Exception as e:
            app.logger.error(f"Erro no upload da foto de perfil: {e}")
            return jsonify(message=f"Erro interno: {str(e)}"), 500

