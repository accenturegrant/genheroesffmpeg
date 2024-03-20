import os
import uuid
import threading
import boto3
import requests
from flask import Flask, request, jsonify
from doffmpeg import do_ffmpeg


app = Flask(__name__)

LOCAL = os.environ.get('local', False)


#background task for video processing and upload
def processVideo(scenes, video_uuid, audio_url):
    images = download_images(scenes, video_uuid)
    audio = download_audio(audio_url, video_uuid)
    output_path = do_ffmpeg(images, audio, video_uuid)  
    print("processing complete")
    if not LOCAL:
        print("uploading video")
        upload_video(video_uuid) 


@app.route('/process', methods=['POST'])
def process():
    data = request.json

    scenes = data.get('scenes', [])
    video_uuid = str(data.get('uuid', uuid.uuid4().hex))
    audio_url = data.get('audio')

    # Check if scenes and audio_url are provided
    if not scenes or not audio_url:
        return jsonify({'error': 'Invalid JSON format. Please provide scenes and audio URL.'}), 400
    try:
        print("starting background thread")
        thread = threading.Thread(target=processVideo, args=(scenes, video_uuid, audio_url))
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
    s3.upload_file(f"./output/{uuid}.mp4", "276036-01-pub", f"{uuid}.mp4")
    
if __name__ == '__main__':
    app.run(port=8000, debug=True)
