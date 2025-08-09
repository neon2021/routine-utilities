import os
import yaml
from box import Box

with open(os.path.expanduser('~/Documents/global-config.yaml'),"r",encoding="utf-8") as f:
    yaml_config = yaml.safe_load(f)
    print(f'yaml_config: {yaml_config}')
    
    for k, v in yaml_config.items():
        if isinstance(v, str):
            yaml_config[k] = os.path.expanduser(v)
    
    print(yaml_config.get('global_dir'))
    
    yaml_config_boxed = Box(yaml_config)
    print(f'yaml_config_boxed: {yaml_config_boxed}')
    

if __name__=='__main__':
    print(f'key: "transcribe.db_conn", value:{yaml_config_boxed.transcribe.db_conn}')