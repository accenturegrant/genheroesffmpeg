#!/usr/bin/env python3

import os
import subprocess
import ffmpeg
from ffmpeg._run import Error

# Configuration
DEFAULT_FRAME_RATE = 24
DEFAULT_RESOLUTION = '1920'
DEFAULT_DURATION = 60

def do_ffmpeg(images, audio_file, uuid, duration=DEFAULT_DURATION, frame_rate=DEFAULT_FRAME_RATE, video_resolution=DEFAULT_RESOLUTION):
    #get video duration
    duration = ffmpeg.probe(audio_file)['format']['duration']
    #build the ffmpeg command
    ffmpeg_command = make_ffmpeg_command(images, audio_file, uuid, duration, frame_rate, video_resolution)

    # execute FFmpeg command
    subprocess.run(' '.join(ffmpeg_command), shell=True)
    return os.path.join('output/', '{}.mp4'.format(uuid))

def make_ffmpeg_command(images, audio_file, uuid, duration, frame_rate, video_resolution):
    image_ct = len(images)
    #scene_dur_sec = float(duration)/len(images)
    #image_dur_sec = scene_dur_sec / image_ct * 2
    image_dur_sec = float(duration) / image_ct * 2
    trans_dur_sec = image_dur_sec / 2

    #initial command with audio
    ffmpeg_command = ['./ffmpeg -i {}'.format(audio_file)]


    #add images
    for img in images:
        ffmpeg_command += ['-loop 1 -t {:.5f} -i {}'.format(image_dur_sec, img)]

    #add crossfade params
    xfade_commands = ['\'']
    for c in range(1, image_ct):
        if c != image_ct - 1:
             xfade_commands.append('[{}][{}]xfade=transition=fade:duration={:.5f}:offset={:5f}[f{}];'.format(
                    c if c == 1 else f"f{c}", c + 1, trans_dur_sec, trans_dur_sec * (c), c+1
                ))
        else:
            xfade_commands.append('[{}][{}]xfade=transition=fade:duration={:5f}:offset={:5f}'.format(
                c if c == 1 else f"f{c}", c + 1, trans_dur_sec, trans_dur_sec * (c)
            ))

    # put it all together
    ffmpeg_command += [
        '-filter_complex',
        ''.join([
            ''.join(xfade_commands),
            ''.join([
                ',scale={}:-2,setsar=1:1,format=yuvj420p[v]\''.format(video_resolution)
            ])
        ]),
        '-map','[v]',
        '-map', '0:a',
        '-c:a', 'aac',
        '-r', str(frame_rate),
        '-preset','ultrafast',
        '-tune', 'zerolatency',
        '-movflags', '+faststart',
        '-f', 'hls',
        '-hls_time', '2',
        '-hls_list_size', str(duration),
        '-hls_flags', 'independent_segments',
        '-hls_segment_type', 'fmp4',
        '-hls_segment_filename', '/var/www/html/stream_%v/data%02d.ts',
        '-var_stream_map', '"v:0,a:0"', f"/var/www/html/stream_%v/{uuid}.m3u8",
        '-y', os.path.join('output/', '{}.mp4'.format(uuid))
    ]
    print(' '.join(ffmpeg_command))
    ffmpeg_command2 = "./ffmpeg -i /var/www/html/stream_%v/{}.m3u8 -bsf:a aac_adtstoasc -vcodec h264 -crf 28 /output/{}.mp4".format(uuid, uuid)
    return ffmpeg_command
