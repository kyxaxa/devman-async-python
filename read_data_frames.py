import os
import errors
import logging

logger = logging.getLogger('read_data_frames')


def read_all_text_frames():
    """Read all prepared text frames of the game"""
    file_paths = [
        r'data/text_frames/demo_frame_1.txt',
        r'data/text_frames/demo_frame_2.txt',
        r'data/text_frames/rocket_frame_1.txt',
        r'data/text_frames/rocket_frame_2.txt',
    ]

    frames = {}
    for file_path in file_paths:
        if not os.path.isfile(file_path):
            logger.ERROR(f'NO FILE {file_path}')
            raise errors.NoFileError(file_path)

        file_name = os.path.basename(file_path)
        with open(file_path, 'r', encoding='utf8') as f:
            content = f.read()
            frames[file_name] = content
    return frames


def load_spaceship_frames(all_text_frames: dict = None) -> List[str]:
    """Loading spaceship text frames"""
    if all_text_frames is None:
        all_text_frames = read_all_text_frames()
    frame1 = all_text_frames['rocket_frame_1.txt']
    frame2 = all_text_frames['rocket_frame_2.txt']

    spaceship_frames = [
        frame1,
        frame1,
        frame2,
        frame2,
    ]
    return spaceship_frames

