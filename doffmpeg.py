import os
import subprocess
import ffmpeg
import platform

# Configuration
DEFAULT_FRAME_RATE = 24
DEFAULT_RESOLUTION = 1920
DEFAULT_DURATION = 60

DIALOG_START_DELAY = 1
DIALOG_START_DELAY_MILIS = DIALOG_START_DELAY * 1000
DIALOG_END_PAD = 4
TRANSITION_DIV = 1

SOUNDTRACK = "./music/AdobeSummit2024_Music.mp3"
WWW_ROOT = "./output" if platform.system() == 'Darwin' else "/var/www/html"

def do_ffmpeg(images, audio_file, uuid, color="colorful", duration=DEFAULT_DURATION, frame_rate=DEFAULT_FRAME_RATE, video_resolution=DEFAULT_RESOLUTION, soundtrack=SOUNDTRACK):
    stream_path = os.path.realpath( os.path.join(WWW_ROOT, 'streams', uuid) )
    dl_path = os.path.realpath('./output')
    if os.path.isdir(stream_path):
        print('DUPLICATE CALL!!!!!')
        return
    os.makedirs(stream_path, exist_ok=True)
    os.makedirs(dl_path, exist_ok=True)
    #get video duration
    dialog_duration = ffmpeg.probe(audio_file)['format']['duration']
    total_duration = float(dialog_duration) + DIALOG_START_DELAY + DIALOG_END_PAD
    #build the ffmpeg command
    ffmpeg_command = make_ffmpeg_command(images, audio_file, uuid, stream_path, dl_path, color, total_duration, frame_rate, video_resolution, soundtrack)

    # execute FFmpeg commands
    print("creating video stream")
    print(' '.join(ffmpeg_command))
    subprocess.run(' '.join(ffmpeg_command), shell=True)
    return os.path.join(dl_path, f'{uuid}.mp4')

def make_ffmpeg_command(images, audio_file, uuid, stream_path, dl_path, color, duration, frame_rate, video_resolution, soundtrack):
    image_ct = len(images)
    image_dur_sec = float(duration) / image_ct * 2
    offset_duration = float(image_dur_sec) / 2

    trans_div = 1.75 if color == "bw" else TRANSITION_DIV
    trans_dur_sec = float(offset_duration) / trans_div

    #audio inputs
    ffmpeg_inputs = [ "-i {} -i {}".format(audio_file, soundtrack) ]

    #image inputs
    for img in images:
        ffmpeg_inputs+= [(
            "-loop 1 -framerate {:.5f} -t {:.5f} -i {}"
           .format(frame_rate, image_dur_sec, img)
        )]

    #filters
    ffmpeg_filters = ['"']

    #mix audio
    ffmpeg_filters += [(
        "[0:a][0:a]amerge=inputs=2,"
        "adelay={0:d}|{0:d},"
        "apad=pad_dur={1:.5f}[dialog];"
        "[dialog][1:a]amerge=inputs=2[amaster];"
        "[amaster]areverse,afade=d={1:.5f},areverse[aedit];"
        .format(int(DIALOG_START_DELAY_MILIS), DIALOG_END_PAD)
    )]

    #format images (slight performance win)
    for c in range(0, image_ct):
        ffmpeg_filters += [(
            "[{:d}]scale={:d}:-2,format=yuvj420p[hd{:d}];"
            .format(c + 2, int(video_resolution), c)
        )]

    #crossfades
    for c in range(0, image_ct - 1):
         ffmpeg_filters += [(
            "[{}][hd{}]"
            "xfade=transition=fade:duration={:.5f}:offset={:5f}[f{:d}];"
            .format(
                f"hd{c}" if c == 0 else f"f{c}",
                c + 1,
                trans_dur_sec,
                offset_duration * (c + 1),
                c + 1
            )
        )]

    ffmpeg_filters += [(
        "[f{0:d}]fade=in:st=0:d={1:.5f},fade=out:st={2:.5f}:d={1:.5f}[vedit]"
        .format(image_ct - 1, trans_dur_sec, offset_duration * ( image_ct - 1 ))
    )]

    ffmpeg_filters += ['"']

    #ffmpeg args
    ffmpeg_encode_args = [
        "-loglevel", "quiet",
        "-acodec", "ac3",
        "-vcodec", "libx264",
        "-pix_fmt", "yuvj420p",
        "-r", str(frame_rate),
        "-preset","ultrafast",
        "-tune", "zerolatency",
        "-flags", "+global_header"
    ]

    ffmpeg_hls_args = (
        f'"[f=hls:hls_time=2:hls_list_size={duration}:'
        'hls_flags=independent_segments:hls_segment_type=fmp4:hls_list_size=0:'
        f'hls_segment_filename={stream_path}/data%02d.ts]'
        f"{stream_path}/stream.m3u8"
    )

    ffmpeg_mp4_args = f'[movflags=+faststart]{dl_path}/{uuid}.mp4"'

    ffmpeg_tee_args = '|'.join([ffmpeg_hls_args, ffmpeg_mp4_args])

    # put it all together
    ffmpeg_command = [
        "ffmpeg",
        ' '.join(ffmpeg_inputs),
        "-filter_complex",
        ''.join(ffmpeg_filters),
        '-map', '[vedit]',
        '-map', '[aedit]',
        ' '.join(ffmpeg_encode_args),
        '-f', 'tee',
        ffmpeg_tee_args
    ]
    return ffmpeg_command
