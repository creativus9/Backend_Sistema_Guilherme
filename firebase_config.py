# backend-shopee/firebase_config.py
# Módulo responsável pela inicialização do Firebase Admin SDK.
# ATUALIZADO: Este arquivo foi modificado para rodar SOMENTE no Railway,
# lendo as credenciais das Variáveis de Ambiente, e não de um arquivo.

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
import json # Necessário para "ler" o JSON da variável de ambiente

# --- Configuração do Firebase ---
# O caminho do arquivo 'firebase-adminsdk.json' FOI REMOVIDO.
FIRESTORE_DATABASE_ID = 'shopee-pedidos-creativusfabrica'
FIREBASE_STORAGE_BUCKET = 'shopee-pedidos-backend.firebasestorage.app'

# Instância do Firestore e do aplicativo Firebase
db = None
firebase_app = None
cred_firebase = None # Iniciamos a credencial como None

try:
    # 1. Tenta carregar as credenciais da Variável de Ambiente do Railway.
    #    O nome da variável no Railway DEVE SER 'FIREBASE_ADMIN_SDK_JSON'.
    firebase_sdk_json_str = os.environ.get('FIREBASE_ADMIN_SDK_JSON')

    if not firebase_sdk_json_str:
        # Se a variável não for encontrada no Railway, o app não pode funcionar.
        print("ERRO FATAL: Variável de Ambiente 'FIREBASE_ADMIN_SDK_JSON' não encontrada!")
        print("Certifique-se de que ela foi criada no painel do Railway.")
        raise ValueError("FIREBASE_ADMIN_SDK_JSON não está configurada.")

    # 2. Converte a string JSON (vinda da variável) em um dicionário Python.
    try:
        cred_dict = json.loads(firebase_sdk_json_str)
        cred_firebase = credentials.Certificate(cred_dict)
    except json.JSONDecodeError:
        print("ERRO FATAL: Falha ao decodificar FIREBASE_ADMIN_SDK_JSON.")
        print("O JSON na variável do Railway provavelmente está mal formatado ou incompleto.")
        raise # Re-levanta o erro para parar a execução do app

    # 3. Inicializa o aplicativo Firebase (se a credencial foi carregada)
    if cred_firebase and not firebase_admin._apps:
        firebase_app = firebase_admin.initialize_app(cred_firebase, {
            'storageBucket': FIREBASE_STORAGE_BUCKET
        })
        print("Conexão com Firebase Admin SDK (via Variável de Ambiente) estabelecida com sucesso!")
    else:
        # Se já inicializado (ex: recarga do servidor), obtém a instância existente
        firebase_app = firebase_admin.get_app()
        print("Firebase Admin SDK já inicializado (recarregamento a quente).")

    # 4. Garante que 'firebase_app' não seja None antes de tentar usar
    if firebase_app:
        db = firestore.client(database_id=FIRESTORE_DATABASE_ID, app=firebase_app)
        print(f"Conexão com Firestore '{FIRESTORE_DATABASE_ID}' estabelecida com sucesso!")
    else:
        print("ERRO: firebase_app não foi inicializado corretamente.")
        raise ValueError("Falha ao obter instância do firebase_app.")

except Exception as e:
    print(f"Erro fatal ao inicializar Firebase: {e}")
    db = None
    firebase_app = None

# O 'db' é importado por outros módulos (como order_data_storage.py)
# Se 'db' for None, os outros módulos irão falhar (o que é esperado se a conexão falhar).