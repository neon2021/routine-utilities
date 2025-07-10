import os
import yaml

with open(os.path.expanduser('~/Documents/global-config.yaml'),"r",encoding="utf-8") as f:
    yaml_config = yaml.safe_load(f)
    print(f'yaml_config: {yaml_config}')
    
    for k, v in yaml_config.items():
        if isinstance(v, str):
            yaml_config[k] = os.path.expanduser(v)
    
    print(yaml_config.get('global_dir'))