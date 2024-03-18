from flask import Flask, request, jsonify
import subprocess
import boto3
from botocore.exceptions import ClientError
import concurrent.futures
import uuid
import requests
from doffmpeg import do_ffmpeg
import os

app = Flask(__name__)

# Configure Boto3 S3 Client
#s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY, region_name=S3_REGION_NAME)

@app.route('/process', methods=['POST'])
def process():
    data = request.json

    scenes = data.get('scenes', [])
    video_uuid = str(data.get('uuid', uuid.uuid4().hex))
    audio_url = data.get('audio')

    # Check if scenes and audio_url are provided
    if not scenes or not audio_url:
        return jsonify({'error': 'Invalid JSON format. Please provide scenes and audio URL.'}), 400

    images = download_images(scenes, video_uuid)
    audio = download_audio(audio_url, video_uuid)

    output_path = do_ffmpeg(images, audio, video_uuid)

    # Upload video to S3
    #try:
    #    s3.upload_file('output_video.mp4', S3_BUCKET_NAME, 'output_video.mp4')
    #except ClientError as e:
    #    return jsonify({'error': str(e)}), 500

    upload_video(video_uuid)
    return jsonify({'message': 'Video processed and uploaded to S3 successfully!', 'url': output_path}), 200

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
    s3.upload_file(f"./output/{uuid}.mp4", "276036-01-pub", f"{uuid}.mp4")
    
if __name__ == '__main__':
    app.run(port=8000, debug=True)
