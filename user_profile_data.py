# backend-shopee/user_profile_data.py
# Módulo para operações de perfil de usuário (buscar e atualizar).

from firebase_admin import firestore
from firebase_config import db # Importa a instância do Firestore

USERS_COLLECTION = 'users'

def get_user_profile(email):
    """
    Busca o perfil completo de um usuário no Firestore pelo seu email.
    Retorna um dicionário com os dados do perfil se encontrado, ou None caso contrário.
    """
    if not db:
        print("Firestore não conectado. Não é possível buscar perfil do usuário.")
        return None

    try:
        user_ref = db.collection(USERS_COLLECTION).document(email)
        user_doc = user_ref.get()

        if user_doc.exists:
            return user_doc.to_dict()
        else:
            print(f"Perfil do usuário não encontrado para o email: {email}")
            return None
    except Exception as e:
        print(f"ERRO: Falha ao buscar perfil do usuário '{email}': {e}")
        return None

def update_user_profile(email, name, nickname, dob, profile_picture_url):
    """
    Atualiza os dados de perfil de um usuário no Firestore.
    """
    if not db:
        print("Firestore não conectado. Não é possível atualizar perfil do usuário.")
        return False, "Firestore não conectado."

    try:
        user_ref = db.collection(USERS_COLLECTION).document(email)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return False, "Usuário não encontrado para atualização de perfil."

        update_data = {
            'name': name,
            'nickname': nickname,
            'dob': dob,
            'profilePictureUrl': profile_picture_url,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        user_ref.update(update_data)
        print(f"Perfil do usuário '{email}' atualizado com sucesso no Firestore.")
        return True, "Perfil atualizado com sucesso!"
    except Exception as e:
        print(f"ERRO: Falha ao atualizar perfil do usuário '{email}': {e}")
        return False, f"Erro ao atualizar perfil: {str(e)}"
