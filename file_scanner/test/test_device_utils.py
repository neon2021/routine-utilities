import os
from file_scanner.device_utils import list_mounted_devices
from file_scanner.mount_path_utils import MountPathUtil

mount_points = list_mounted_devices()
for m in mount_points:
    print(f'mount_point: {m}\n')

print(f'\n{"-"*80}\n')
mountPathUtil = MountPathUtil.from_mount_points(mount_points)

root_dir = mount_points[1].mount_path
real_path_list = mountPathUtil.get_n_real_path(root_dir,n=10)
print(f'real_path_list: {real_path_list}')

print(f'\n{"-"*80}\n')
logical_path = mountPathUtil.real_path_2_logical(real_path_list[0])
print(f'logical_path: {logical_path}')

print(f'\n{"-"*80}\n')
uuid, relative_path = logical_path
real_path = mountPathUtil.logical_path_2_real(uuid,relative_path)
print(f'real_path: {real_path}')