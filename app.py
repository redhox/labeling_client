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
    url = 'http://192.168.173.12:8002/users/token'
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
        response = requests.post(
            f'{SERVER_URL}/users/protected_route', headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            return user_data
    return login()
def check_authentication(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if the current route is the "predict_route"
        if request.endpoint == 'predict_route':
            # Extract the token from the request's form
            token = request.form['token']
        else:
            # Check for the token in the session
            token = session.get('token')
        if token:
            # Verify the token using the get_token function
            headers = {'Authorization': f'JWT {token}'}
            response = requests.get(f'{SERVER_URL}/users/protected_route', headers=headers)
            if response.status_code == 200:
                # Do not print the result here
                pass
            else:
                print(
                    f"Failed to access protected resource. Status code: {response.status_code}")
            return func(*args, **kwargs)
        else:
            print("Authentication failed")
            return login(),401
    return wrapper

def compter_elements_dans_dossier(dossier):
    return len([f for f in sorted(os.listdir(dossier)) if os.path.isfile(os.path.join(dossier, f))])


def dir_in_dir(path):
    dir_list=[]
    for racine, sous_dossiers, fichiers in sorted(os.walk(path)):
        for sous_dossier in sous_dossiers:
            print(os.path.join(racine, sous_dossier))
            image_number = compter_elements_dans_dossier(f'{racine}/{sous_dossier}')
            dir_list.append([sous_dossier,image_number])
    return dir_list


def images_in_dir(path):
    # Spécifiez le chemin du dossier à scanner
    image_list=[]
    for racine, soudoss, fichiers in sorted(os.walk(path)):
        for fichier in fichiers:
            if fichier != "integrity.check" or "metadata.json":
                image_list.append([fichier])
    return image_list


@app.route('/', methods=['GET', 'POST'])
def login():
    print("bonjour")
    if request.method == 'POST':
        print("post")
        email = request.form['email']
        password = request.form['password']
        print('de rretour dans app ',email)
        token = get_token(email, password)
        print('j ais le tocken',token)
        if token:
            session['token'] = token  # Store the token in the session
            return redirect(url_for('dashboard'))
        else:
            return jsonify({'message':'auth fail'})
    
    print("get")
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
    return render_template('dashboard.html',token=token , user=user)
    


@app.route('/labelling/<pathname>/<dirname>/<filename>', methods=['GET'])
@check_authentication
def labelling(pathname,dirname,filename):
    token = session.get('token')
    if token: 

        filepath=[pathname,dirname,filename]
        print(f'/{filepath[0]}/{filepath[1]}/{filepath[2]}')
        # filepath = '/image_dir/image/boys.jpg'
        with open(f'/{filepath[0]}/{filepath[1]}/{filepath[2]}', "rb") as img_file:
            files = {'file': img_file}
        
            data={'path': f'{filepath[1]}/{filepath[2]}'}
            
            response = requests.post(
                f"{SERVER_URL}/images/image_save",
                data={"path": f'{UUID_MACHINE}/{filepath[1]}/{filepath[2]}'},
                files=files
                )
        

        # response = requests.post(f"{SERVER_URL}/images/image_save",json={'path':f'{filepath[1]}/{filepath[2]}'},files=files)

        # filepath = {"filepath": filepath}
        # filename_2 = data_image['result']['name']
        ##labelisation time
        
        # if data_image['result']['labels'] == False:
        #     response_annotation = requests.post(
        #         f'{SERVER_URL}/load_images', json=filepath, headers=headers)
        #     data = response_annotation.json()
        #     print(data)
        # else:
        #     data = data_image['result']['regions']
        #     data = {'images': {
        #             f"{filename_2}{data_image['result']['size']}": {
        #                 'file_attributes': {},
        #                 'filename': data_image['result']['name'],
        #                 'regions': data,
        #                 'size': data_image['result']['size']
        #             }
        #             }}


        # filename = [image_info['filename']
        #             for image_info in data['images'].values()]
        # filesize = [image_info['size']
        #             for image_info in data['images'].values()]
        # filename = filename[0]
        # filesize = filesize[0]
        # print(filesize)
        # print(f"Image:{filename}")
        # print(f"Image:{filename_2}")
        # filename = filename_2
        # response_image = requests.post(
        #     f'{SERVER_URL}/image_from_server', json=filepath, headers=headers)

        # with open(f"./image/{filename}", 'wb') as f:
        #     f.write(response_image.content)
        image = filename
        liste_images=images_in_dir(f'/{filepath[0]}/{filepath[1]}')
        return render_template('labelling.html',  filepath=filepath,liste_images=liste_images, filesize=440 )
        return render_template('labelling.html', image=image, filename=filename, data=data, id_image=id_image, filesize=filesize)
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
            print(data)
            response = requests.post(f'{SERVER_URL}/images/post_resultat', json=data, headers=headers)
            return jsonify({"message": " File uploaded successfully"}), 200 

@app.route('/get_image/<pathname>/<dirname>/<filename>' ,methods=['GET'])
def get_image(pathname,dirname,filename):
    print("getimage")
    image_path = f'/{pathname}/{dirname}/{filename}'
    with Image.open(image_path) as img:
        image_format = img.format.lower()
        return send_file(image_path, mimetype=f'.{image_format}')


@app.route('/overview')
@check_authentication
def overview():
    user=get_current_user()
    images = dir_in_dir('./dossier_images')
    
    return render_template('overview.html', images=images, username=user)

@app.route('/overview/<dirname>')
@check_authentication
def overview_dir(dirname):
    user=get_current_user()
    images = images_in_dir(f'/image_dir/{dirname}')
    path=f'image_dir'
    return render_template('overview_img.html', images=images,path=path,dirname=dirname, username=user)

# @app.route('/admin/user_management')
# @check_authentication
# def user_management():
#     token = session.get('token')

#     if token:
#         headers = {'Authorization': f'JWT {token}'}
#         user_id = requests.post(f'{SERVER_URL}/user_name', headers=headers)
#         username = user_id.json()['username']
#         role = user_id.json()['role']
#         try:
#             # Remplacez l'URL par l'URL r�elle de votre API pour r�cup�rer les utilisateurs
#             response = requests.post(f'{SERVER_URL}/all_user', headers=headers)
#             response.raise_for_status()  # G�re les erreurs HTTP
#             users = response.json()  # Convertit la r�ponse JSON en Python dict
#             print('users=',users)
#             return render_template('user_management.html', users=users, username=username, role=role)
#         except requests.exceptions.RequestException as e:
#             print(f"Error fetching users: {e}")
#             return []
#     else:
#         print("Authentication failed")
#         return jsonify({'message': 'Authentication failed'}), 401


# @app.route('/admin/register', methods=['GET', 'POST'])
# @check_authentication
# def register():
#     if request.method == 'POST':
#         # Rest of your registration code remains unchanged
#         admin_token = session.get('token')
#         if admin_token:
#             # Cr�ez un nouvel utilisateur avec les donn�es minimales
#             username = request.form['username']
#             password = request.form['password']
#             role = request.form['role']

#             headers = {'Authorization': f'JWT {admin_token}'}
#             data = {
#                 'username': username,
#                 'password': password,
#                 'role': role
#             }

#             try:
#                 response = requests.post(
#                     f'{SERVER_URL}/create_user', headers=headers, json=data)
#                 response.raise_for_status()

#                 if response.status_code == 201:
#                     flash('User created successfully', 'success')
#                     return redirect(url_for('user_management'))
#                 else:
#                     error_message = response.json().get('message')
#                     flash(
#                         f"User creation failed. Status code: {response.status_code}, Message: {error_message}", 'error')

#             except requests.exceptions.RequestException as e:
#                 flash(f"Error during user creation: {e}", 'error')

#         else:
#             flash("Admin authentication failed", 'error')
#             return redirect(url_for('user_management'))

#     return redirect(url_for('user_management'))


# @app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
# @check_authentication
# def delete_user(user_id):
#     token = session.get('token')
#     if token:
#         try:
#             headers = {'Authorization': f'JWT {token}'}
#             data = {'id':user_id}
#             response = requests.post(f'{SERVER_URL}/delete_user',json=data , headers=headers)
#             response.raise_for_status()
#             return user_management(), 200
#         except requests.exceptions.RequestException as e:
#             print(f"Error deleting user: {e}")
#             return jsonify({'message': f'Erreur lors de la suppression de l\'utilisateur'}), 500
#     else:
#         return jsonify({'message': f'L\'authentification a �chou�'}), 401


# @app.route('/admin/switch_role/<int:user_id>', methods=['POST'])
# @check_authentication
# def switch_role(user_id):
#     token = session.get('token')
#     if token:
#         try:
#             headers = {'Authorization': f'JWT {token}'}
#             data = {'id':user_id}
#             response = requests.post(f'{SERVER_URL}/user',json=data , headers=headers)
#             response.raise_for_status()
#             user_data = response.json().get('user')
#             current_role = user_data.get('role')
#             new_role = 'admin' if current_role == 'utilisateur' else 'utilisateur'
#             data = {'id':user_id,'role': new_role}
#             response = requests.post(f'{SERVER_URL}/change_role', json=data, headers=headers)
#             response.raise_for_status()
#             return user_management(), 200
#         except requests.exceptions.RequestException as e:
#             print(f"Error switching role: {e}")
#             print(f"Response content: {response.content}")
#     else:
#         return jsonify({'message': 'L\'authentification a �chou�'}), 401


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
