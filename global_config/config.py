import os
import yaml
from box import Box

from global_config.logger_config import logger

with open(os.path.expanduser('~/Documents/global-config.yaml'),"r",encoding="utf-8") as f:
    yaml_config = yaml.safe_load(f)
    logger.info(f'yaml_config: {yaml_config}')
    
    for k, v in yaml_config.items():
        if isinstance(v, str):
            yaml_config[k] = os.path.expanduser(v)
    
    logger.info(yaml_config.get('global_dir'))
    
    yaml_config_boxed = Box(yaml_config)
    logger.info(f'yaml_config_boxed: {yaml_config_boxed}')
    
base_dir = os.path.dirname(os.getcwd())

def cur_dir(path:str)->str:
    return os.path.join(base_dir,path)

def cur_dir(f:str, path:str)->str:
    base_dir = os.path.dirname(f)
    return os.path.join(base_dir,path)


if __name__=='__main__':
    logger.info(f'key: "transcribe.db_conn", value:{yaml_config_boxed.transcribe.db_conn}')