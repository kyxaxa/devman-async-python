import os
import errors
import logging

logger = logging.getLogger('read_data_frames')


def read_all_text_frames():
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
