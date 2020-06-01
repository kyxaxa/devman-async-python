from dotenv import load_dotenv
from pathlib import Path  # Python 3.6+ only
import errors

def load_settings(file_name='.env'):
    env_path = Path('.') / file_name
    if not os.path.isfile(env_path):
        raise errors.NoFileError(env_path)

    load_dotenv(dotenv_path=env_path)