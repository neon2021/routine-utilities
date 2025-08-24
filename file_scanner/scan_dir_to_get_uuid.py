import os
from file_scanner.device_utils import calculate_md5

def scan_directory(root_path: str,limit=5):
    stop_scan = False
    file_list = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        depth = dirpath[len(root):].count(os.sep)
        if depth <= 2:
            print(dirpath, filenames)
        else:
            dirnames[:] = []  # 停止深入
            stop_scan = True
        if stop_scan:
            break
        # 确保目录和文件名排序一致
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            is_existed = os.path.exists(file_path)
            print(f'file_path: {file_path} exists: {is_existed}')
            if not is_existed:
                continue
            file_size = os.path.getsize(file_path)
            
            if file_size > 0:
                print(f'file_path:{file_path}, file_size:{file_size}')
                file_list.append(file_path)
            if len(file_list) == limit:
                stop_scan = True
                break
    return file_list

def get_vol_uuid_by_config(volume_path:str)->str:
    pass

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="args to create uuid for disks or directories")
    parser.add_argument('--root',type=str,default="/Volumes")
    
    args = parser.parse_args()
    
    root = args.root
    list = os.listdir(root)
    print(f'list: {list}')
    dir_map_2_md5_list = {}
    for volume_item in list:
        vol_path = os.path.join(root, volume_item)
        if 'Macintosh' in volume_item:
            print(f'ignore vol_path: {vol_path}')
            continue
        print(f'vol_path: {vol_path}')
        
        files = scan_directory(vol_path,limit=5)
        file_with_md5 = dict(map(lambda file_path: (file_path.removeprefix(vol_path).removeprefix(os.sep), calculate_md5(file_path)), files))
        dir_map_2_md5_list[vol_path] = file_with_md5

    print(f'dir_map_2_md5_list: {dir_map_2_md5_list}')
