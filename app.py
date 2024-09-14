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
app = Flask(__name__)
app.secret_key = os.environ.get('SECTRET_KEY')
SERVER_URL = os.environ.get("SERVER_URL")
# app.config['PREFERRED_URL_SCHEME'] = 'http'
 
# uuid pour la machine
load_dotenv()
if os.getenv('UUID_MACHINE') == None:
    with open(".env", "a") as f:
        f.write(f"UUID_MACHINE={uuid.uuid4()}\n")

UUID_MACHINE=os.getenv('UUID_MACHINE')
def get_token(email, password):
    url = f'{SERVER_URL}/users/token'
    data = {'email': email, 'password': password}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX/5XX
        return response.json().get('access_token')
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None


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
            headers = {'Authorization': f'JWT {token}'}
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
                headers = {'Authorization': f'JWT {token}'}
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
        return True



@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        token = get_token(email, password)
        if token:
            session['token'] = token  # Store the token in the session
            return redirect(url_for('dashboard'))
        else:
            return jsonify({'message':'auth fail'})
    
    if session.get('token'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')
    

@app.route('/dashboard')
@check_authentication
def dashboard():
    token = session.get('token') 
    headers = {'Authorization': f'JWT {token}'}
    user=get_current_user()
    print("dashboard")
    print("dashboard",user)
    return render_template('dashboard.html',token=token , user=user)
     

@app.route('/update')
@check_authentication
def update():
    repo = Repo('.')
    repo.remotes.origin.pull()
    return login()
     


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
            
            #verification 
            response = requests.post(
                f"{SERVER_URL}/images/image_search", 
                data={"path": f'{UUID_MACHINE}/{filepath[1]}/{filepath[2]}'}, 
                )
            label_confirm=''

            if response.status_code == 200:
                response_data = response.json()
                data = json.loads(response_data)
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
                    files=files
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
        response = requests.post(f"{SERVER_URL}/models/actif_model")
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
        headers = {'Authorization': f'JWT {token}'}
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
            response = requests.post(f'{SERVER_URL}/images/post_resultat', json=data, headers=headers)
            return jsonify({"message": " File uploaded successfully"}), 200 

@app.route('/get_image/<pathname>/<dirname>/<filename>' ,methods=['GET'])
def get_image(pathname,dirname,filename):
    print("getimage")
    image_path = f'/{pathname}/{dirname}/{filename}'
    with Image.open(image_path) as img:
        return send_file(image_path)

    
@app.route('/get_image_thumbnail/<pathname>/<dirname>/<filename>' ,methods=['GET'])
def get_image_thumbnail(pathname,dirname,filename):
    print("getimage")
    image_path = f'/{pathname}/{dirname}/{filename}'
    with Image.open(image_path) as img:
        new_size = (170, 170)  # Exemple : 100px de large et 100px de haut
        img.thumbnail(new_size)
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        return send_file(io.BytesIO(buffered.getvalue()), mimetype='image/jpeg')
    
@app.route('/overview')
@check_authentication
def overview():
    user=get_current_user()
    images = dir_in_dir('./dossier_images')
    
    return render_template('overview.html', images=images, user=user)

@app.route('/overview/<dirname>')
@check_authentication
def overview_dir(dirname):
    user=get_current_user()
    images = images_in_dir(f'/image_dir/{dirname}')
    path=f'image_dir'
    model='model_non_actif'
    return render_template('overview_img.html', images=images,path=path,dirname=dirname, user=user,model=model)




@app.route('/model_list')
@check_authentication
def model_list():
    user=get_current_user()
    if user['is_admin'] != True:
        return dashboard() 
    response = requests.post(f'{SERVER_URL}/models/lists_models')
    response_data = response.json()
    list_model_all = json.loads(response_data)
    print('model data',list_model_all)

    response = requests.post(f'{SERVER_URL}/models/actif_model')
    response_data = response.json()
    list_model_actif = json.loads(response_data)
    # list_model_actif = json.dumps(response_data)

    return render_template('model_dashboard.html', list_model_actif=list_model_actif,list_model_all=list_model_all,user=user)

@app.route('/add_model_list/<string:id_model>', methods=['GET'])
@check_authentication
def add_model_list(id_model):
    print('id model',id_model)
    response = requests.post(f'{SERVER_URL}/models/add_model_id', json={'id':id_model})
    response_data = response.json()
    return json.dumps({"message": "Bonjour"})

@app.route('/del_model_list/<string:id_model>', methods=['GET'])
@check_authentication
def del_model_list(id_model):
    print('id model',id_model)
    response = requests.post(f'{SERVER_URL}/models/del_model_id', json={'id':id_model})
    response_data = response.json()
    print('response_data del model',response_data)
    return json.dumps({"message": "Bonjour"})

@app.route('/liste_actif_model') 
@check_authentication
def liste_actif_model():
    response = requests.post(f'{SERVER_URL}/models/actif_model')
    response_data = response.json()
    list_model_actif = json.loads(response_data)
    print('liste model',list_model_actif)
    return list_model_actif 




@app.route('/logout') 
def logout():
    session.clear()
    return render_template('login.html')


if __name__ == '__main__':
    app.run(debug=True)
