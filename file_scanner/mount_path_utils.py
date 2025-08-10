import os
from file_scanner.device_utils import list_mounted_devices
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

from global_config.logger_config import logger

logger.name = os.path.basename('MountPathUtil')

@dataclass
class MountPathUtil:
    mount_points: List[Any] = field(default_factory=list)
    
    def __post_init__(self):
        """
        __post_init__ of dataclass will run after the automatically generated __init__
        here could supplement extra validation logic
        """
        if not isinstance(self.mount_points, list):
            raise TypeError("mount_points must be a list")

    @classmethod
    def from_mount_points(cls, mount_points: List[Any]) -> "MountPathUtil":
        """
        构造方法1：外部传入 mount_points。
        """
        return cls(mount_points=mount_points)

    @classmethod
    def from_system(cls) -> "MountPathUtil":
        """
        构造方法2：内部自动调用 list_mounted_devices() 初始化。
        """
        mounts = list_mounted_devices()
        return cls(mount_points=mounts)

    def get_n_real_path(self, root_dir:str, n:int=1):
        n_real_path_list=[]

        idx = 0
        stop_loop=False
        for root, _, files in os.walk(root_dir):
            if stop_loop:
                break
            for name in files:
                if idx == n or stop_loop:
                    stop_loop = True
                    break
                
                real_path = os.path.join(root, name)
                # print(f'real_path: {real_path}')
                n_real_path_list.append(real_path)
                
                idx += 1
        
        return n_real_path_list

    # real_path_2_logical
    def real_path_2_logical(self, real_path:str)->Tuple[str,str]:
        '''
        returns {disk uuid}, {relative_path}
        '''
        mount_path_list = [m for m in self.mount_points if real_path.startswith(m.mount_path)]
        if mount_path_list:
            most_match_mount = max(mount_path_list, key=lambda o: len(o.mount_path))
            relative_path = real_path.removeprefix(most_match_mount.mount_path)
            relative_path = relative_path.removeprefix(os.path.sep)
            return most_match_mount.partition_uuid if most_match_mount.partition_uuid else most_match_mount.uuid, relative_path
        
        return None

    def logical_path_2_real(self, uuid:str, relative_path:str)->str:
        if uuid is None or relative_path is None:
            logger.error(f'logical_path_2_real, uuid:{uuid} or relative_path:{relative_path} is illegal')
            return None
        mount_path_list = [m for m in self.mount_points if m.partition_uuid == uuid or m.uuid == uuid]
        print(f'mount_path_list: {mount_path_list}')
        if mount_path_list:
            most_match_mount = mount_path_list[0]
            real_path = os.path.join(most_match_mount.mount_path, relative_path)
            return real_path
        
        return None