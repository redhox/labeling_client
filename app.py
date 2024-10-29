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
app = Flask(__name__)
app.secret_key = os.environ.get('SECTRET_KEY')
SERVER_URL = os.environ.get("SERVER_URL")
# app.config['PREFERRED_URL_SCHEME'] = 'http'
TEMP_FOLDER = 'temp_folder'

if not os.path.exists(TEMP_FOLDER):
    os.makedirs(TEMP_FOLDER)
# uuid pour la machine
load_dotenv()
if os.getenv('UUID_MACHINE') == None:
    with open(".env", "a") as f:
        f.write(f"UUID_MACHINE={uuid.uuid4()}\n")

UUID_MACHINE=os.getenv('UUID_MACHINE')
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


@app.route('/', methods=['GET', 'POST'])
def login():
    user_agent = request.user_agent.string
    user_agent_parsed = parse(user_agent)
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
        except:
            return render_template('login.html') 

        token,last_login = get_token(email, password,ip_address,user_agent_parsed)
        print('token',token)
        if token:
            session['token'] = token  # Store the token in the session
            session['last_login']=last_login
            return redirect(url_for('overview'))
        else:
            
            errorsesion= "wrong"
            print(errorsesion)
            render_template('login.html',errorsesion=errorsesion)
    
    if session.get('token'):
        return redirect(url_for('overview'))
    print('pls')
    errorsesion= "wrong"
    print(errorsesion)
    return render_template('login.html')


@app.route('/dashboard')
@check_authentication
def dashboard(): 
        
 
    last_login = session.get('last_login')
    token = session.get('token') 
    headers = {'Authorization': f'Bearer {token}'}
    user=get_current_user() 
    print("dashboard")
    print("dashboard",user) 
    return render_template('dashboard.html',token=token , user=user,last_login=last_login)
     
@app.route('/user_management')
@check_authentication
def user_management():
    token = session.get('token') 
    headers = {'Authorization': f'Bearer {token}'}
    user=get_current_user()
    
    headers = {'Authorization': f'Bearer {token}'} 
    if user['is_admin'] == True:
        response = requests.post(f'{SERVER_URL}/users/get_all_users', headers=headers)   
        if response.status_code == 200:

            response_data = response.json()
            print("reponce label data",response_data)
    else:
        response = requests.post(f'{SERVER_URL}/users/ids', headers=headers ,json={'user_id':user['id']})   
        if response.status_code == 200:

            response_data = [response.json()]
            print("reponce label data",response_data)

    return render_template('user_management.html',token=token , user=user,users=response_data)


@app.route('/register',methods=['POST'])
@check_authentication
def register():
    token = session.get('token') 
    headers = {'Authorization': f'Bearer {token}'} 
    print('register')
    username = request.form['username']
    password = request.form['password'] 
    email = request.form['email'] 


    data = {
        "username": username,
        "email": email,
        "password": password
    }
    print('ici ça va',data ) 
    print(f'requete secur {SERVER_URL}/users/',token)
    response = requests.post(f'{SERVER_URL}/users/',json=data , headers=headers)
    print('responce de la route secur',response) 
    return user_management() 
 
 

 


  





@app.route('/switch-role/<int:user_id>',methods=['POST'])
@check_authentication
def switch_role(user_id):
    token = session.get('token') 
    headers = {'Authorization': f'Bearer {token}'} 

    response = requests.post(
    f'{SERVER_URL}/users/ids', headers=headers , json={'user_id':user_id})
    response.raise_for_status()
    user_data = response.json()


    if user_data[3] == True:
        new_role = False
    if user_data[3] == False:
        new_role = True
    print('new_role',new_role)
    response = requests.put(
    f'{SERVER_URL}/users/switch_role', headers=headers , json={'user_id':user_id,'role_is_admin':new_role})
    response.raise_for_status()

    return user_management()

@app.route('/delete_user/<int:user_id>',methods=['POST']) 
@check_authentication
def delete_user(user_id):
    token = session.get('token')

    user=get_current_user() 
    headers = {'Authorization': f'Bearer {token}'} 
    response = requests.delete(f'{SERVER_URL}/users/delete', headers=headers , json={'user_id':user_id})
    response.raise_for_status()
    if user['id']==user_id:
        return logout()
    return user_management()
    
 
@app.route('/update')
@check_authentication
def update():
    token = session.get('token')
    if token:
        repo = Repo('.')
        repo.remotes.origin.pull() 
        return login()
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401


@app.context_processor
def inject_global_variables():
    data={"need_update": need_update()}
    return dict(global_variable=data)

@app.route('/labelling/<pathname>/<dirname>/<filename>/<string:model>', methods=['GET'])
@check_authentication 
def labelling(pathname,dirname,filename,model):
    token = session.get('token')
    user=get_current_user()
    if token:

        filepath=[pathname,dirname,filename]
        with open(f'/{filepath[0]}/{filepath[1]}/{filepath[2]}', "rb") as img_file:
            files = {'file': img_file}
        
            data={'path': f'{filepath[1]}/{filepath[2]}'} 
            headers = {'Authorization': f'Bearer {token}'}
            #verification 
            response = requests.post(
                f"{SERVER_URL}/images/image_search", 
                data={"path": f'{UUID_MACHINE}/{filepath[1]}/{filepath[2]}'},  headers=headers
                )
            label_confirm='' 

            if response.status_code == 200:
                data = response.json()
                # print('ici',response_json )  
                # data = response_json['content'] 



                print('data status 200=',data)
                try:
                    regions = data['regions'] 
                    liste_objet=[]
                    for region in regions:
                        liste_objet.append(region['region_attributes']['objet'])   
                except:
                    regions=[] 
                    liste_objet=[]
                 
                label_confirm='verified by human'

            else:
                # envoi de limage 
                response = requests.post( 
                    f"{SERVER_URL}/images/image_save",
                    data={"path": f'{UUID_MACHINE}/{filepath[1]}/{filepath[2]}',"model":model},
                    files=files, headers=headers
                    )
                response_data = response.json()
                regions = json.dumps(response_data)
                # Load the JSON data 
                data_dict = json.loads(regions)
                
                # Extract the information 
                print('data from model=',data_dict)
                try:
                    regions = data_dict['regions'] 
                except:
                    regions=[]
                print('region=', regions )
                try:
                    liste_objet_data = data_dict['liste_objet'] 
                    liste_objet=[]
                    for element in liste_objet_data:
                        liste_objet.append(liste_objet_data[element])
                except:
                    liste_objet=[]
                print('listeobjet',liste_objet)

            # regions=response_data
                
        # creation de la liste thumbnail
        liste_images=images_in_dir(f'/{filepath[0]}/{filepath[1]}') 
        indice_element = liste_images.index(filename)
        avant = liste_images[max(indice_element - 3, 0):indice_element]
        apres = liste_images[indice_element + 1:min(indice_element + 4, len(liste_images))]
        liste_images = avant + [filename] + apres
        try :
            nextimage=apres[0]
        except:
            nextimage=False

        index_in_list=[indice_element,len(liste_images)]
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(f"{SERVER_URL}/models/actif_model", headers=headers)
        response_data = response.json()
        data = json.loads(response_data) 
        # print('listemodel= ',data)
        lists_model=data


        return render_template('labelling.html',nextimage=nextimage,index_in_list=index_in_list, regions=regions, filepath=filepath,liste_images=liste_images, filesize=440 ,model=model ,liste_models=lists_model,liste_objet=liste_objet,label_confirm=label_confirm,user=user)
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401

@app.route('/resultat', methods=['POST'])
def resultat():
    print("resultat")
    token = session.get('token')
 
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        file = request.files['file']

        if file:
            
            filename = request.form.get('filename') 
            filedir = request.form.get('filedir') 


            content = file.read()
            file.close()
            data = json.loads(content)
            for key in data.keys():
                first_key = key  
            path=f"{UUID_MACHINE}/{filedir}/{filename}"
            regions=data[first_key]["regions"]
            data = {'filename':filename,"filedir":filedir,"path":path,'regions': regions,"uuid_machine":UUID_MACHINE}
            print("resultat",data)
            response = requests.put(f'{SERVER_URL}/images/post_resultat', json=data, headers=headers)
            return jsonify({"message": " File uploaded successfully"}), 200 
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401
@app.route('/get_image/<pathname>/<dirname>/<filename>' ,methods=['GET'])
@check_authentication
def get_image(pathname,dirname,filename):
    print("getimage")
    token = session.get('token')
    if token:
        image_path = f'/{pathname}/{dirname}/{filename}'
        with Image.open(image_path) as img:
            return send_file(image_path)

    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401
@app.route('/get_image_thumbnail/<pathname>/<dirname>/<filename>' ,methods=['GET'])
@check_authentication
def get_image_thumbnail(pathname,dirname,filename):
    token = session.get('token')
    if token:
        print("getimage")
        image_path = f'/{pathname}/{dirname}/{filename}'
        with Image.open(image_path) as img:
            new_size = (170, 170)  # Exemple : 100px de large et 100px de haut
            img.thumbnail(new_size)
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG")
            return send_file(io.BytesIO(buffered.getvalue()), mimetype='image/jpeg')
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401
@app.route('/overview')
@check_authentication
def overview():
    token = session.get('token')
    if token:
        user=get_current_user()
        images = dir_in_dir('./dossier_images')
        return render_template('overview.html', images=images, user=user)
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401

@app.route('/overview/<dirname>')
@check_authentication
def overview_dir(dirname):
    token = session.get('token')
    if token:
        user=get_current_user()
        images = images_in_dir(f'/image_dir/{dirname}')
        path=f'image_dir'
        model='model_non_actif'
        print("overvei dirname")
        print({"uuid": UUID_MACHINE,"projet_name":dirname,"download":False})
        
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post( 
            f"{SERVER_URL}/images/labels",
            json={"uuid": UUID_MACHINE,"projet_name":dirname,"download":False}, headers=headers)
        response_data = response.json()
        print("reponce label data",response_data)
        data_label = json.loads(response_data)

        return render_template('overview_img.html', images=images,path=path,dirname=dirname, user=user,model=model,data_label=data_label)
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401


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



@app.route('/download_label/<projet_name>')
@check_authentication
def download_label(projet_name):
    token = session.get('token')
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        # S'assurer que le dossier existe
        if not os.path.exists(f'{TEMP_FOLDER}/{projet_name}'):
            os.makedirs(f'{TEMP_FOLDER}/{projet_name}')
        
        
        response = requests.post( 
            f"{SERVER_URL}/images/labels",
            json={"uuid": UUID_MACHINE,"projet_name":projet_name,"download":True}, headers=headers)
        response_data = response.json()
        data = json.loads(response_data)
        print('data:',data)
    # Créer un fichier zip depuis la liste de textes
        memory_file = create_zip_from_list(data,projet_name)
        # if os.path.exists(f'{TEMP_FOLDER}/{projet_name}'):
        #     os.remove(f'{TEMP_FOLDER}/{projet_name}')
        # Envoyer le fichier zip pour le téléchargement
        if memory_file:
            return send_file(memory_file, download_name=f'{projet_name}.zip', as_attachment=True)
        else:
            return "Erreur lors de la création du fichier zip.", 500
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401

@app.route('/model_list')
@check_authentication
def model_list():
    token = session.get('token')
    if token:
        user=get_current_user()
        if user['is_admin'] != True:
            return dashboard() 

        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(f'{SERVER_URL}/models/lists_models', headers=headers)
        response_data = response.json()
        list_model_all = json.loads(response_data)
        print('model data',list_model_all)

        response = requests.post(f'{SERVER_URL}/models/actif_model', headers=headers)
        response_data = response.json()
        list_model_actif = json.loads(response_data)
        # list_model_actif = json.dumps(response_data)

        return render_template('model_dashboard.html', list_model_actif=list_model_actif,list_model_all=list_model_all,user=user)
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401
@app.route('/add_model_list/<string:id_model>', methods=['GET'])
@check_authentication
def add_model_list(id_model):
    print('id model',id_model)
    token = session.get('token')
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.put(f'{SERVER_URL}/models/add_model_id', json={'id':id_model}, headers=headers)
        response_data = response.json()
        return json.dumps({"message": "Bonjour"})
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401

@app.route('/del_model_list/<string:id_model>', methods=['GET'])
@check_authentication
def del_model_list(id_model):
    print('id model',id_model)
    token = session.get('token')
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.delete(f'{SERVER_URL}/models/del_model_id', json={'id':id_model}, headers=headers)
        response_data = response.json()
        print('response_data del model',response_data)
        return json.dumps({"message": "Bonjour"})
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401
@app.route('/liste_actif_model') 
@check_authentication
def liste_actif_model():
    token = session.get('token')
    if token:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(f'{SERVER_URL}/models/actif_model', headers=headers)
        response_data = response.json()
        list_model_actif = json.loads(response_data)
        print('liste model',list_model_actif)
        return list_model_actif 
    else:
        print("Authentication failed")
        return jsonify({'message': 'Authentication failed'}), 401



@app.route('/logout')
def logout():
    session.clear()
    return render_template('login.html',errorsesion="timeout")



if __name__ == '__main__':
    app.run(debug=True)
