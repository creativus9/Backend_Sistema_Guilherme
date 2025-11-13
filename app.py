# backend-shopee/app.py
# Este é o arquivo principal que inicializa a aplicação Flask.
# ATUALIZADO: Importa e inicializa os novos módulos de dados.

from flask import Flask, jsonify
from flask_cors import CORS # Importa CORS para permitir comunicação entre React e Flask

# Importa as funções de registro de rotas
from routes import register_routes 

# Importa os novos módulos de dados para garantir que as inicializações ocorram
# A ordem de importação é importante para garantir que 'db' esteja disponível
# antes que outros módulos tentem usá-lo para carregar dados.
import firebase_config
import user_auth
import order_data_storage 
import order_operations 
import import_history_data
import app_config_data

def create_app():
    """
    Cria e configura a instância da aplicação Flask.
    """
    app = Flask(__name__) # Inicializa a aplicação Flask
    CORS(app) # Habilita o CORS para todas as rotas, permitindo que o frontend React acesse o backend

    # Registra as rotas definidas no módulo routes.py
    register_routes(app)

    # Rota de teste simples para verificar se o backend está funcionando
    @app.route('/')
    def hello_world():
        return jsonify(message="Bem-vindo ao Backend de Gestão de Pedidos Shopee!")

    return app

if __name__ == '__main__':
    # Quando este script é executado diretamente, ele inicia o servidor Flask.
    # Para rodar em modo de desenvolvimento, com recarregamento automático
    # e informações de debug.
    app = create_app()
    # Adicionamos host='0.0.0.0' para permitir acesso de outros computadores na rede local.
    app.run(debug=True, host='0.0.0.0', port=5000) # O backend rodará na porta 5000 por padrão
