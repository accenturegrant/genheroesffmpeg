import os
import pathlib
import uuid
import logging
import threading
import boto3
import shutil
from botocore.exceptions import ClientError
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from doffmpeg import do_ffmpeg


app = Flask(__name__)
CORS(app, origins=["*"])

LOCAL = os.environ.get('local', False)
S3_BUCKET = "276036-01-pub"
PRE_SIGNED_URL_EXPIRY = 3600
SECRET = "gA2jj/dYrpI6ZXiGjFmZ9MSX1lZ544a8"

#background task for video processing and upload
def processVideo(scenes, video_uuid, audio_url, color="color"):
    images = download_images(scenes, video_uuid)
    audio = download_audio(audio_url, video_uuid)
    do_ffmpeg(images, audio, video_uuid, color)  
    print("processing complete")
   
    if not LOCAL:
        print("uploading video")
        upload_video(video_uuid)
    else:
        print("not uploading video")
    print("cleaning up...")
    shutil.rmtree("./tmp/{}".format(video_uuid), ignore_errors=True)
    pathlib.Path("./output/{}.mp4".format(video_uuid)).unlink()


@app.route('/upload', methods=['GET'])
def get_upload_url():
    data = request.args
    object_name = data.get('object_name', uuid.uuid4().hex)
    secret = data.get('secret', '')

    if not verify_secret(secret):
        return jsonify({'message': "DENIED"}), 403

    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_post(
            S3_BUCKET,
            object_name,
            None,
            None,
            PRE_SIGNED_URL_EXPIRY
        )
    except ClientError as e:
        logging.error(e)
        return jsonify({'message': str(e)}), 500
    return jsonify({'message': "success!", "signed-url": response}), 200

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    secret = data.get('secret', '')
    if not verify_secret(secret):
        return jsonify({'message': "DENIED"}), 403
    
    scenes = data.get('scenes', [])
    video_uuid = str(data.get('uuid', uuid.uuid4().hex))
    audio_url = data.get('audio')
    color = data.get('color', 'color')
    

    # Check if scenes and audio_url are provided
    if not scenes or not audio_url:
        return jsonify({'error': 'Invalid JSON format. Please provide scenes and audio URL.'}), 400
    try:
        print("starting background thread")
        thread = threading.Thread(target=processVideo, args=(scenes, video_uuid, audio_url), kwargs={"color": color})
        thread.start()
        return jsonify({'message': 'Video processing.', 'uuid': video_uuid}), 200
    except Exception as error:
        return jsonify({'message': str(error)}), 500
    

def download_images(scenes, uuid):
    directory = os.path.join("tmp",uuid,"images")
    os.makedirs(directory, exist_ok=True)
    images = []
    for scene_index, scene in enumerate(scenes):
        for image_index, img in enumerate(scene.get('images', [])):
            filename = 'tmp/{}/images/scene{}_{}.jpg'.format(uuid, scene_index, image_index)
            res = requests.get(img)
            with open(filename, 'wb') as file:
                file.write(res.content)
            images.append(filename)
    return images
            

def download_audio(audio_url, uuid):
    directory = os.path.join("tmp",uuid,"audio")
    os.makedirs(directory, exist_ok=True)
    filename = 'tmp/{}/audio/{}.m4a'.format(uuid, uuid)
    res = requests.get(audio_url) 
    with open(filename, 'wb') as file:
        file.write(res.content)
    return filename

def upload_video(uuid):
    s3 = boto3.client('s3')
    s3.upload_file(f"./output/{uuid}.mp4", S3_BUCKET, f"{uuid}.mp4")

def verify_secret(secret):
    #this could be better
    return secret == SECRET
    
if __name__ == '__main__':
    app.run(port=8000, debug=True)
