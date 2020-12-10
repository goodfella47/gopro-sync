import ffmpeg
from timecode import Timecode
import sys
import os
from collections import namedtuple
import subprocess
from shutil import copy2

path = "synced"

def mp4_to_mpeg2(input_name, output_name):
    ffmpeg_command = f'ffmpeg -i {input_name} -c copy -bsf:v h264_mp4toannexb -f mpegts {output_name} -y'.split()
    subprocess.run(ffmpeg_command)


def create_black_footage(time, framerate, aspect_ratio):
    ffmpeg_command = f'ffmpeg -t {time} -f lavfi -i color=c=black:s={aspect_ratio}:r={framerate} -c:v libx264 -tune stillimage -pix_fmt yuv420p black.mp4 -y'.split()
    subprocess.run(ffmpeg_command)  # capture_output=True


def add_sound_to_black():
    ffmpeg_command = f'ffmpeg -i "black.mp4" -f lavfi -i anullsrc=cl=stereo:r=48000 -shortest -y -c:v copy "black_with_sound.mp4"'
    subprocess.run(ffmpeg_command)


def concat(output):
    ffmpeg_command = f'ffmpeg -i concat:intermediate1.ts|intermediate2.ts -c copy -bsf:a aac_adtstoasc {path}\\{output} -y'.split()
    subprocess.run(ffmpeg_command)


def remove_file(file):
    if os.path.exists(file):
        os.remove(file)


def vid_rename(vid_name):
    raw_vid_name, vid_format = vid_name.split('.')
    new_vide_name = raw_vid_name + '_synced.' + vid_format
    return new_vide_name


def create_footage(vid_name, new_vide_name, timecode, exact_time, aspect_ratio):
    create_black_footage(exact_time, int(timecode.framerate), aspect_ratio)
    add_sound_to_black()
    mp4_to_mpeg2('black_with_sound.mp4', 'intermediate1.ts')
    mp4_to_mpeg2(vid_name, 'intermediate2.ts')
    print(f'{vid_name} synced')
    concat(new_vide_name)
    for file in ['black.mp4', 'intermediate1.ts', 'intermediate2.ts', 'black_with_sound.mp4']:
        remove_file(file)


def main(argv):
    assert len(argv) == 3
    _, vid_name, vid_length = argv
    assert vid_name.endswith(".MP4") or vid_name.endswith(".mp4")
    assert os.path.isfile(vid_name)
    new_vide_name = vid_rename(vid_name)
    probe = ffmpeg.probe(vid_name)
    codec_type = probe['streams'][0]['codec_type'] == 'video'
    assert codec_type, f'codec mismatch in {f}'
    raw_frame_rate = probe['streams'][0]['r_frame_rate']
    width, height = probe['streams'][0]['width'], probe['streams'][0]['height']
    aspect_ratio = f'{width}x{height}'
    timecode = Timecode(str(raw_frame_rate[:-2]), vid_length)
    exact_time = timecode.frames / int(timecode.framerate)
    create_footage(vid_name, new_vide_name, timecode, exact_time, aspect_ratio)


if __name__ == "__main__":
    main(sys.argv)
