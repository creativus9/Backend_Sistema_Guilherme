# backend-shopee/storage_operations.py
# Módulo para lidar com operações de upload de arquivos para o Firebase Storage.

from firebase_admin import storage
from firebase_config import firebase_app # CORRIGIDO: Importa a instância do app Firebase inicializada como 'firebase_app'

def upload_profile_picture(file_stream, user_id, file_name):
    """
    Faz o upload de uma foto de perfil para o Firebase Storage.
    Retorna a URL pública do arquivo ou None em caso de erro.
    """
    if not firebase_app:
        print("Firebase Admin SDK não inicializado. Não é possível fazer upload.")
        return None

    try:
        bucket = storage.bucket(app=firebase_app) # Obtém o bucket padrão do seu projeto
        
        # Define o caminho no Storage: profile_pictures/{userId}/{fileName}
        # Isso corresponde às regras de segurança que você configurou.
        blob = bucket.blob(f'profile_pictures/{user_id}/{file_name}')

        # Faz o upload do arquivo
        blob.upload_from_file(file_stream, content_type=file_stream.mimetype)

        # Torna o arquivo publicamente acessível (se suas regras de segurança permitirem)
        # Se suas regras de leitura forem 'if request.auth != null', você não precisa tornar o arquivo público.
        # No entanto, para visualização direta em navegadores sem autenticação complexa, pode ser útil.
        # Se você quer estritamente apenas usuários autenticados, remova a linha abaixo.
        blob.make_public() 

        print(f"Arquivo '{file_name}' uploaded para '{blob.public_url}'")
        return blob.public_url
    except Exception as e:
        print(f"ERRO ao fazer upload da foto de perfil: {e}")
        return None
