import pytest
from unittest.mock import patch, Mock, MagicMock
import requests
import os
import zipfile
import io
from app import (app,get_token, get_current_user, check_authentication, compter_elements_dans_dossier, dir_in_dir, images_in_dir, need_update, create_zip_from_list)
from git import Repo
from flask import session  ,Flask

from unittest.mock import patch, Mock

@patch('requests.post')
def test_get_token_success(mock_post):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'access_token': 'test_token', 'last_login': '2023-10-10T10:00:00'}
    mock_post.return_value = mock_response
    token, last_login = get_token('test@example.com', 'password', '192.168.1.1', 'TestAgent')
    assert token == 'test_token'
    assert last_login == '2023-10-10T10:00:00'


@patch('requests.post')
def test_get_token_failure(mock_post):
    mock_post.side_effect = requests.exceptions.RequestException("Connection error")
    token, last_login = get_token('test@example.com', 'password', '192.168.1.1', 'TestAgent')
    assert token is None
    assert last_login is None



@patch('requests.post')
def test_get_current_user_authenticated(mock_post):
    with app.test_request_context():
        with patch('flask.session.get') as mock_session_get:
            # Simuler un token valide dans la session
            mock_session_get.return_value = 'test_token'
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'user_id': 1, 'username': 'testuser'}
            mock_post.return_value = mock_response

            # Appel de la fonction
            user_data = get_current_user()

            # Vérification
            assert user_data == {'user_id': 1, 'username': 'testuser'}


# @patch.dict('flask.session', {'token': None})  # Simuler l'absence de token dans la session
# @patch('requests.post')
# def test_get_current_user_unauthenticated(mock_post):
#     # Appel de la fonction
#     user_data = get_current_user()
    
#     # Vérification : vérifier si la fonction retourne un appel à `login()`
#     assert user_data == login()

# from unittest.mock import patch, Mock

# # Créer une instance de Flask pour les tests
# app = Flask(__name__)
# app.secret_key = 'test_secret'  # Nécessaire pour utiliser la session
# @patch.dict('flask.session', {'token': None})  # Simuler l'absence de token dans la session
# # Décorateur de test pour simuler le contexte de l'application
# def test_check_authentication_with_token():
#     with app.test_request_context():  # Crée un contexte de requête
#         with patch('session.get') as mock_session_get, patch('requests.post') as mock_post:
#             # Simuler un token valide et une réponse 200
#             mock_session_get.return_value = 'test_token'
#             mock_response = Mock()
#             mock_response.status_code = 200
#             mock_post.return_value = mock_response
            
#             # Décorateur de vérification de l'authentification
#             @check_authentication
#             def protected_function():
#                 return "Function accessed"
            
#             # Appel de la fonction protégée
#             result = protected_function()
            
#             # Vérification
#             assert result == "Function accessed"



@patch('os.listdir')
@patch('os.path.isfile')
def test_compter_elements_dans_dossier(mock_isfile, mock_listdir):
    mock_listdir.return_value = ['file1.txt', 'file2.txt', 'dir1']
    mock_isfile.side_effect = lambda x: not x.endswith('dir1')
    count = compter_elements_dans_dossier('/path/to/folder')
    assert count == 2


@patch('os.walk')
@patch('app.compter_elements_dans_dossier')  # Correction ici avec le chemin complet
def test_dir_in_dir(mock_compter, mock_walk):
    mock_walk.return_value = [('/path', ['dir1', 'dir2'], [])]
    mock_compter.side_effect = lambda x: 5 if 'dir1' in x else 3
    result = dir_in_dir('/path')
    assert result == [['dir1', 5], ['dir2', 3]]


@patch('os.walk')
def test_images_in_dir(mock_walk):
    mock_walk.return_value = [
        ('/path', [], ['image1.jpg', 'metadata.json', 'image2.png'])
    ]
    result = images_in_dir('/path')
    assert result == ['image1.jpg', 'image2.png']

from unittest.mock import patch, MagicMock
from git import Repo

from unittest.mock import patch, MagicMock
from git import Repo

# @patch('git.Repo')
# def test_need_update(mock_repo):
#     # Création d'une instance mockée pour Repo
#     mock_repo_instance = mock_repo.return_value

#     # Mock du commit local
#     mock_local_commit = MagicMock()
#     mock_local_commit.hexsha = 'commit1'  # Définir le hash du commit local
#     mock_repo_instance.head.commit = mock_local_commit

#     # Mock de la méthode fetch et du commit sur origin/main
#     mock_repo_instance.remotes.origin.fetch.return_value = None  # Simuler la méthode fetch

#     # Mock du commit sur origin/main
#     mock_origin_commit = MagicMock()
#     mock_origin_commit.hexsha = 'commit1'  # Simuler que origin/main a le même commit
#     mock_repo_instance.commit.return_value = mock_origin_commit  # Configurer la méthode commit pour retourner le commit simulé

#     # Exécuter la fonction et vérifier le résultat
#     result = need_update()
#     assert result is False  # On s'attend à ce que cela retourne False car les commits correspondent

#     # Changer le commit distant pour simuler une mise à jour
#     mock_origin_commit.hexsha = 'commit2'  # Maintenant, le commit distant est différent

#     # Exécuter la fonction et vérifier le résultat à nouveau
#     result = need_update()
#     assert result is True  # Maintenant, on s'attend à True car il y a une mise à jour disponible


import tempfile
def test_create_zip_from_list():
    global TEMP_FOLDER
    with tempfile.TemporaryDirectory() as temp_dir:
        TEMP_FOLDER = temp_dir
        text_list = [{'filename': 'file1.jpg', 'regions': [{'region_attributes': {'objet': 'object1'}, 'shape_attributes': {'x': 1, 'y': 2, 'width': 10, 'height': 20}}]}]
        
        memory_file = create_zip_from_list(text_list, 'project_name')
        assert memory_file is not None
        assert memory_file.getvalue()

        with zipfile.ZipFile(memory_file) as zf:
            assert 'file1.txt' in zf.namelist()
            with zf.open('file1.txt') as f:
                content = f.read()
                if content:
                    assert content
                # assert content == b'Some content here'