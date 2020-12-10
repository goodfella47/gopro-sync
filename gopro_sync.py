import ffmpeg
from timecode import Timecode
import sys
import os
from collections import namedtuple
import subprocess
from shutil import copy2

path = "synced"

def get_time_difference(timecode1, timecode2):
    framerate = int(timecode1.framerate)
    frame_difference = (timecode1 - timecode2).frames
    return frame_difference / framerate


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


def sync_to_reference(vid, ref):
    vid_timecode, aspect_ratio, vid_name = vid
    ref_timecode, _, ref_name = ref
    new_vide_name = vid_rename(vid_name)  # rename to synced
    time_difference = get_time_difference(vid_timecode, ref_timecode)
    create_black_footage(time_difference, int(vid_timecode.framerate), aspect_ratio)
    add_sound_to_black()
    mp4_to_mpeg2('black_with_sound.mp4', 'intermediate1.ts')
    mp4_to_mpeg2(vid_name, 'intermediate2.ts')
    print(f'{vid_name} synced')
    concat(new_vide_name)
    for file in ['black.mp4', 'intermediate1.ts', 'intermediate2.ts', 'black_with_sound.mp4']:
        remove_file(file)


if __name__ == "__main__":

    vids = []
    vid = namedtuple('vids', ['timecode', 'aspect_ratio', 'name'])
    file_list = [f for f in os.listdir('.') if os.path.isfile(os.path.join('.', f))]
    # iterate over all the files in the folder
    for f in file_list:
        if f.endswith(".MP4") or f.endswith(".mp4"):
            probe = ffmpeg.probe(f)
            codec_type = probe['streams'][0]['codec_type'] == 'video'
            assert codec_type, f'codec mismatch in {f}'
            raw_frame_rate = probe['streams'][0]['r_frame_rate']
            if 'timecode' in probe['streams'][0]['tags']:
                raw_timecode = probe['streams'][0]['tags']['timecode']
            else:
                continue
            width, height = probe['streams'][0]['width'], probe['streams'][0]['height']
            aspect_ratio = f'{width}x{height}'
            timecode = Timecode(str(raw_frame_rate[:-2]), raw_timecode)
            video = vid(timecode, aspect_ratio, f)
            vids.append(video)

    assert vids, 'no video footage found'

    if len(vids) > 1:
        vids.sort()
        reference = vids[0]
        for v in vids[1:]:
            if v.timecode.framerate != reference.timecode.framerate:
                raise IOError(f'{v.name} framerate doesnt match')
        try:
            os.mkdir(path)
        except OSError:
            print("Creation of the directory %s failed" % path)
        else:
            print("Successfully created the directory %s " % path)

        # sync video files
        for v in vids[1:]:
            sync_to_reference(v, reference)

        # copy reference
        copy2(reference.name, path)
        print(f'sync is complete\n the reference file is {reference.name}')

