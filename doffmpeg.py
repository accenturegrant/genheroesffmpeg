import os
import subprocess
import ffmpeg

# Configuration
DEFAULT_FRAME_RATE = 24
DEFAULT_RESOLUTION = '1920'
DEFAULT_DURATION = 60   

DIALOG_START_DELAY = 1
DIALOG_START_DELAY_MILIS = DIALOG_START_DELAY * 1000
DIALOG_END_PAD = 4
TRANSITION_DIV = 1

soundtrack = "./music/AdobeSummit2024_Music.mp3"

def do_ffmpeg(images, audio_file, uuid, color="color", duration=DEFAULT_DURATION, frame_rate=DEFAULT_FRAME_RATE, video_resolution=DEFAULT_RESOLUTION):
    #get video duration
    duration = ffmpeg.probe(audio_file)['format']['duration']
    total_duration = float(duration) + DIALOG_START_DELAY + DIALOG_END_PAD
    #build the ffmpeg command
    ffmpeg_commands = make_ffmpeg_commands(images, audio_file, uuid, duration, total_duration, frame_rate, video_resolution)

    # execute FFmpeg commands
    print("merging audio tracks")
    subprocess.run(ffmpeg_commands[0], shell=True)
    print("creating video stream")
    subprocess.run(' '.join(ffmpeg_commands[1]), shell=True)
    print("converting to mp4")
    subprocess.run(ffmpeg_commands[2], shell=True)
    return os.path.join('output/', '{}.mp4'.format(uuid))

def make_ffmpeg_commands(images, audio_file, uuid, duration, total_duration, frame_rate, video_resolution, color="color"):
    image_ct = len(images)
    image_dur_sec = float(duration) / image_ct * 2
    offset_duration = image_dur_sec / 2

    trans_div = 1.75 if color == "bw" else TRANSITION_DIV
    trans_dur_sec = offset_duration/trans_div

    merge_audio_command = "ffmpeg -i {} -i {} -filter_complex \"[0:a][0:a]amerge=inputs=2,adelay={}|{:.5f},apad=pad_dur={:.5f}[dialog];[dialog][1:a]amerge=inputs=2[master];[master]areverse,afade=d={:.5f},areverse[edit]\" -map \"[edit]\"  -t {:.5f} -ac 2 ./tmp/{}/audio/final.aac".format(audio_file, soundtrack, DIALOG_START_DELAY_MILIS, DIALOG_START_DELAY_MILIS, DIALOG_END_PAD, DIALOG_END_PAD, total_duration, uuid)

    #initial command with audio
    ffmpeg_command = ['ffmpeg -i ./tmp/{}/audio/final.aac'.format(uuid)]


    #add images
    for img in images:
        ffmpeg_command += ['-loop 1 -t {:.5f} -i {}'.format(image_dur_sec, img)]

    #add crossfade params
    xfade_commands = ['\'']
    for c in range(1, image_ct):
        if c != image_ct - 1:
             xfade_commands.append('[{}][{}]xfade=transition=fade:duration={:.5f}:offset={:5f}[f{}];'.format(
                    c if c == 1 else f"f{c}", c + 1, trans_dur_sec, offset_duration * (c), c+1
                ))
        else:
            xfade_commands.append('[{}][{}]xfade=transition=fade:duration={:5f}:offset={:5f}'.format(
                c if c == 1 else f"f{c}", c + 1, trans_dur_sec, offset_duration * (c)
            ))

    # put it all together
    ffmpeg_command += [
        '-filter_complex',
        ''.join([
            ''.join(xfade_commands),
            ''.join([
                '[body];[body]fade=in:st=0:d={},fade=out:st={}:d={},scale={}:-2,setsar=1:1,format=yuvj420p[v]\''.format(trans_dur_sec, trans_dur_sec * image_ct, trans_dur_sec, video_resolution)
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
        '-hls_segment_filename', f"/var/www/html/stream_%v/{uuid}/data%02d.ts",
        '-var_stream_map', '"v:0,a:0"', f"/var/www/html/stream_%v/{uuid}/{uuid}.m3u8"
    ]
    ffmpeg_command2 = f"ffmpeg -y -i /var/www/html/stream_0/{uuid}/{uuid}.m3u8 -bsf:a aac_adtstoasc -vcodec h264 -crf 28 ./output/{uuid}.mp4"
    return (merge_audio_command,ffmpeg_command, ffmpeg_command2)
