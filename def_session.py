import os
import json
from pathlib import Path
from werkzeug.utils import secure_filename 
from dotenv import load_dotenv
import uuid
from bson import json_util
import io
from git import Repo
import zipfile
from user_agents import parse
from functools import wraps
from flask import g, request, redirect, url_for, flash

# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
import smtplib
#from flask_mail import Mail, Message
import json
from flask import flash, session
from PIL import Image
from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, session, url_for, send_file, jsonify
import requests
import os
import json
from pathlib import Path
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import uuid
from bson import json_util
from PIL import Image
import io
from git import Repo
import os
import zipfile
from user_agents import parse



UUID_MACHINE=os.getenv('UUID_MACHINE')
SERVER_URL = os.environ.get("SERVER_URL")



def get_token(email, password,ip_address,user_agent_parsed):
    url = f'{SERVER_URL}/users/token'
    data = {'email': email, 'password': password,"uuid_machine":UUID_MACHINE,"ip_address":ip_address,"user_agent": f"{user_agent_parsed}"}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX/5XX
        print('reponce au token',response.json())
        print('Raw response:', response.text) 
        return response.json().get('access_token') ,response.json().get('last_login')
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None ,None


def get_current_user(): 
    token = session.get('token')
    print('token',token) 
    if token: 
        headers = {
            'Authorization': f'Bearer {token}',
        }
        print('headers',headers,f'url {SERVER_URL}/users/protected_route')
        response = requests.post(f'{SERVER_URL}/users/protected_route', headers=headers)  

        # headers = {'Authorization': f'Bearer {token}'} 
        # response = requests.get(f'{SERVER_URL}/users/protected_route', headers=headers)  
 
        if response.status_code == 200:
            user_data = response.json()
            return user_data
        if response.status_code == 401:
                print("Authentication failed")
                return logout(),401
    return login()

def check_authentication(func):
    @wraps(func) 
    def wrapper(*args, **kwargs):
        # Check if the current route is the "predict_route"
        if request.endpoint == 'predict_route':
            # Extract the token from the request's form
            token = request.form['token']
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.post(f'{SERVER_URL}/users/protected_route', headers=headers)
            if response.status_code == 200:
                # Do not print the result here
                pass
            if response.status_code == 401:
                print("Authentication failed")
                return logout(),401
        else:
            # Check for the token in the session
            token = session.get('token')
            if token:
                # Verify the token using the get_token function
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.post(f'{SERVER_URL}/users/protected_route', headers=headers)
                if response.status_code == 200:
                    # Do not print the result here
                    pass
                else:
                    print(f"Failed to access protected resource. Status code: {response.status_code}")
                    
                return func(*args, **kwargs)
            else:
                print("Authentication failed")
                return logout(),401
        
    return wrapper

def compter_elements_dans_dossier(dossier):
    return len([f for f in sorted(os.listdir(dossier)) if os.path.isfile(os.path.join(dossier, f))])

def dir_in_dir(path):
    dir_list=[]
    for racine, sous_dossiers, fichiers in sorted(os.walk(path)):
        for sous_dossier in sous_dossiers:
            print("dir_in_dir",os.path.join(racine, sous_dossier))
            image_number = compter_elements_dans_dossier(f'{racine}/{sous_dossier}')
            dir_list.append([sous_dossier,image_number])
    return dir_list


def images_in_dir(path):
    # Spécifiez le chemin du dossier à scanner
    image_list=[]
    for racine, soudoss, fichiers in sorted(os.walk(path)):
        for fichier in fichiers:
            if fichier != "integrity.check" or "metadata.json":
                image_list.append(fichier)
    return image_list

def need_update():
    repo = Repo('.')
    current_commit = repo.head.commit
    repo.remotes.origin.fetch()
    origin_main_commit = repo.commit('origin/main')
    if current_commit == origin_main_commit:
        return False
    else:
        return True
def create_zip_from_list(text_list,projet_name):
    # Utiliser un fichier en mémoire pour stocker le zip
    memory_file = io.BytesIO()
    
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for element in text_list:
            # Créer le nom du fichier, par exemple "file_1.txt"
            filename = '.'.join(element['filename'].split('.')[:-1])
            filename = f"{filename}.txt"
            
            # Chemin complet du fichier
            file_path = f'{TEMP_FOLDER}/{projet_name}/{filename}'
            # Créer un fichier txt pour chaque ligne
            with open(file_path, 'a') as f:
                f.write('#objet x y width height \n')
            for region in element['regions']:

                result_string = f"{region['region_attributes']['objet'],region['shape_attributes']['x'],region['shape_attributes']['y'],region['shape_attributes']['width'],region['shape_attributes']['height']}"
                with open(file_path, 'a') as f:
                    f.write(f'{result_string}\n')
            
            # Ajouter chaque fichier dans le zip
            zf.write(file_path, filename)
            os.remove(f'{file_path}')

            

    # Revenir au début du fichier en mémoire
    memory_file.seek(0)
    return memory_file

