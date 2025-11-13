# backend-shopee/user_auth.py
# Módulo para gerenciamento de usuários (criação e verificação).

import hashlib
from firebase_admin import firestore # Necessário para firestore.SERVER_TIMESTAMP
from firebase_config import db # Importa a instância do Firestore

USERS_COLLECTION = 'users'

def _hash_password(password):
    """Gera um hash simples para a senha (para fins de exemplo)."""
    # Em uma aplicação real, use um algoritmo de hash mais seguro como bcrypt.
    return hashlib.sha256(password.encode()).hexdigest()

def _initialize_admin_user():
    """
    Verifica se os usuários administradores padrão existem e os cria se não existirem.
    """
    if not db:
        print("Firestore não conectado. Não é possível inicializar usuários admin.")
        return

    # Lista de usuários administradores desejados
    admin_users_to_ensure = [
        {"username": "guilhermeprofissionaladm@gmail.com", "password": "guilhermeimperador1", "name": "Guilherme"}, # NOVO: Adicionado nome
        {"username": "fernandopollastrini@gmail.com", "password": "polastrinipolasfernando1", "name": "Fernando"} # NOVO: Adicionado nome
    ]

    try:
        # Primeiro, remove o usuário "Guilherme" se ele existir
        # ATENÇÃO: Se o email for o identificador, "Guilherme" não será o document ID.
        # Precisamos usar o email como document ID para consistência.
        # Por enquanto, vou manter a remoção pelo nome "Guilherme" se for um ID de documento.
        # Se o sistema usa email como ID, esta parte pode precisar de ajuste.
        guilherme_user_ref = db.collection(USERS_COLLECTION).document("Guilherme")
        guilherme_user_doc = guilherme_user_ref.get()
        if guilherme_user_doc.exists:
            guilherme_user_ref.delete()
            print("Usuário 'Guilherme' removido do Firestore.")

        # Em seguida, adiciona ou verifica os novos usuários administradores
        for admin_user_data in admin_users_to_ensure:
            username = admin_user_data["username"]
            password_hash = _hash_password(admin_user_data["password"])
            name = admin_user_data["name"] # NOVO: Obtém o nome

            user_ref = db.collection(USERS_COLLECTION).document(username) # Usa email como ID do documento
            user_doc = user_ref.get()

            if not user_doc.exists:
                user_ref.set({
                    'username': username,
                    'password_hash': password_hash,
                    'role': 'admin', # Adiciona um campo de role (papel)
                    'name': name, # NOVO: Salva o nome
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                print(f"Usuário administrador '{username}' criado no Firestore.")
            else:
                print(f"Usuário administrador '{username}' já existe no Firestore.")
                # Opcional: Atualizar a senha, role ou nome se necessário
                # user_ref.update({'password_hash': password_hash, 'role': 'admin', 'name': name})
                # print(f"Usuário administrador '{username}' atualizado no Firestore.")

    except Exception as e:
        print(f"ERRO: Falha ao inicializar usuários administradores: {e}")

def create_user(username, password, name):
    """
    Cria um novo usuário no Firestore.
    Retorna True em caso de sucesso, False se o usuário já existe ou em caso de erro.
    """
    if not db:
        print("Firestore não conectado. Não é possível criar usuário.")
        return False, "Firestore não conectado."

    try:
        user_ref = db.collection(USERS_COLLECTION).document(username) # Usa email como ID do documento
        user_doc = user_ref.get()

        if user_doc.exists:
            return False, "Nome de usuário já existe." # Se o email já existe
        
        password_hash = _hash_password(password)
        user_ref.set({
            'username': username,
            'password_hash': password_hash,
            'role': 'user', # Papel padrão para novos usuários
            'name': name, # NOVO: Salva o nome
            'created_at': firestore.SERVER_TIMESTAMP
        })
        print(f"Usuário '{username}' criado com sucesso no Firestore.")
        return True, "Usuário criado com sucesso!"
    except Exception as e:
        print(f"ERRO: Falha ao criar usuário '{username}': {e}")
        return False, f"Erro ao criar usuário: {str(e)}"

def verify_user(username, password):
    """
    Verifica as credenciais de um usuário no Firestore.
    Retorna o papel do usuário (role) se as credenciais forem válidas, None caso contrário.
    """
    if not db:
        print("Firestore não conectado. Não é possível verificar usuário.")
        return None

    try:
        user_ref = db.collection(USERS_COLLECTION).document(username) # Usa email como ID do documento
        user_doc = user_ref.get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            stored_password_hash = user_data.get('password_hash')
            provided_password_hash = _hash_password(password)

            if stored_password_hash == provided_password_hash:
                print(f"Usuário '{username}' autenticado com sucesso.")
                return user_data.get('role', 'user') # Retorna o papel do usuário
            else:
                print(f"Tentativa de login falhou para '{username}': senha incorreta.")
                return None
        else:
            print(f"Tentativa de login falhou para '{username}': usuário não encontrado.")
            return None
    except Exception as e:
        print(f"ERRO: Falha ao verificar usuário '{username}': {e}")
        return None

# Inicializa o usuário administrador na inicialização do módulo
if db:
    _initialize_admin_user()
