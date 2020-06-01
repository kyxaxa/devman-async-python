import os
from dotenv import load_dotenv
from pathlib import Path  # Python 3.6+ only
import errors


def load_settings_from_file_to_environment(file_name='settings.env'):
    env_path = Path('.') / file_name
    if not os.path.isfile(env_path):
        raise errors.NoFileError(env_path)

    load_dotenv(dotenv_path=env_path)