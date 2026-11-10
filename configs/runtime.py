"""YAML defaults with local environment overrides."""
from functools import lru_cache
from pathlib import Path
import os
import yaml
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parents[1]
@lru_cache(maxsize=1)
def settings():
    load_dotenv(ROOT / '.env', override=False)
    return yaml.safe_load((ROOT / 'configs/settings.yaml').read_text(encoding='utf-8'))
def option(section, key, default=None, env=None):
    value = settings().get(section, {}).get(key, default)
    return os.getenv(env, value) if env else value
def data_path(key, default):
    path = Path(option('paths', key, default, key.upper()))
    return path if path.is_absolute() else ROOT / path
