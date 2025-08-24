import os
from file_scanner.device_utils import calculate_md5

def scan_directory(root_path: str,limit=5):
    stop_scan = False
    file_list = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        if stop_scan:
            break
        # 确保目录和文件名排序一致
        dirnames.sort()
        filenames.sort()
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_size = os.path.getsize(file_path)
            
            if file_size > 0:
                print(f'file_path:{file_path}, file_size:{file_size}')
                file_list.append(file_path)
            if len(file_list) == limit:
                stop_scan = True
                break
    return file_list

def get_vol_uuid_by_config(volume_path:str)->str:
    '''
-> % /opt/miniconda3/envs/whisper-arm/bin/python /Users/caesar/Documents/IdeaProjects/githubs/routine-utilities/file_s
canner/scan_dir_to_get_uuid.py
vol_path: /Volumes/Untitled 2
file_path:/Volumes/Untitled 2/$360Section/360.B4E4380632D0D3614FC3E4074E70E2BD.q3q, file_size:638976
file_path:/Volumes/Untitled 2/360Rec/20121210/123114.vir, file_size:257096
file_path:/Volumes/Untitled 2/ME/1.jpg, file_size:133831
file_path:/Volumes/Untitled 2/ME/11.jpg, file_size:43161
file_path:/Volumes/Untitled 2/ME/111.jpg, file_size:94299
file_path:/Volumes/Untitled 2/ME/1111.jpg, file_size:98814
file_path:/Volumes/Untitled 2/ME/11111.jpg, file_size:99281
file_path:/Volumes/Untitled 2/ME/111111.jpg, file_size:98837
file_path:/Volumes/Untitled 2/ME/1111111.jpg, file_size:99624
file_path:/Volumes/Untitled 2/ME/11111111.jpg, file_size:40308
index: 1, file: /Volumes/Untitled 2/$360Section/360.B4E4380632D0D3614FC3E4074E70E2BD.q3q, md5: 46f7c4fdc45818ee5fead82611aab5ad
index: 2, file: /Volumes/Untitled 2/360Rec/20121210/123114.vir, md5: 8485910175324f33c1ed0348aedeec1e
index: 3, file: /Volumes/Untitled 2/ME/1.jpg, md5: 99f1f379d79ec0af296d91f9b49e99a0
index: 4, file: /Volumes/Untitled 2/ME/11.jpg, md5: a4383ec9bb77aca794673a60e028ac1d
index: 5, file: /Volumes/Untitled 2/ME/111.jpg, md5: ca7abf3ef427aebc45c5af0f9a0684b2
index: 6, file: /Volumes/Untitled 2/ME/1111.jpg, md5: 1d758443f1d61a8779961ac8dea2b664
index: 7, file: /Volumes/Untitled 2/ME/11111.jpg, md5: d9d4e99ffbced15148f3903f2567dd39
index: 8, file: /Volumes/Untitled 2/ME/111111.jpg, md5: d378e5aec424b6b1052e64f528ff4144
index: 9, file: /Volumes/Untitled 2/ME/1111111.jpg, md5: d51dafd7a2d667055517e69c673cc2fc
index: 10, file: /Volumes/Untitled 2/ME/11111111.jpg, md5: 12f54b26d4f6e29b5efc686001681716
vol_path: /Volumes/Untitled 3
file_path:/Volumes/Untitled 3/NTDETECT.COM, file_size:47564
file_path:/Volumes/Untitled 3/boot.ini, file_size:231
file_path:/Volumes/Untitled 3/bootfont.bin, file_size:322730
file_path:/Volumes/Untitled 3/ntldr, file_size:257728
file_path:/Volumes/Untitled 3/pagefile.sys, file_size:3223322624
file_path:/Volumes/Untitled 3/360SANDBOX/360SandBox.sav, file_size:262144
file_path:/Volumes/Untitled 3/360SANDBOX/360SandBox.sav.LOG, file_size:8192
file_path:/Volumes/Untitled 3/Documents and Settings/Administrator/NTUSER.DAT, file_size:1310720
file_path:/Volumes/Untitled 3/Documents and Settings/Administrator/ntuser.dat.LOG, file_size:274432
file_path:/Volumes/Untitled 3/Documents and Settings/Administrator/ntuser.ini, file_size:178
index: 1, file: /Volumes/Untitled 3/NTDETECT.COM, md5: b2de3452de03674c6cec68b8c8ce7c78
index: 2, file: /Volumes/Untitled 3/boot.ini, md5: c098b8f538881f72f1bceaf73506791f
index: 3, file: /Volumes/Untitled 3/bootfont.bin, md5: 99f68407c9470130eb0f3d7350ec109d
index: 4, file: /Volumes/Untitled 3/ntldr, md5: 879a44be0daa3623381ca34370bc1495
index: 5, file: /Volumes/Untitled 3/pagefile.sys, md5: None
index: 6, file: /Volumes/Untitled 3/360SANDBOX/360SandBox.sav, md5: b506506b271576589fe1e7e7560b29ac
index: 7, file: /Volumes/Untitled 3/360SANDBOX/360SandBox.sav.LOG, md5: 6f311a7bdca13974e1b508985e017add
index: 8, file: /Volumes/Untitled 3/Documents and Settings/Administrator/NTUSER.DAT, md5: 77f1674ccba07332faeef08c0fd4b58a
index: 9, file: /Volumes/Untitled 3/Documents and Settings/Administrator/ntuser.dat.LOG, md5: 659ec187403fdfd616bc18b644a79584
index: 10, file: /Volumes/Untitled 3/Documents and Settings/Administrator/ntuser.ini, md5: cbda6984d2ecc537aef07205ae001013
ignore vol_path: /Volumes/Macintosh HD
vol_path: /Volumes/Untitled 1
file_path:/Volumes/Untitled 1/360杀毒/360sd_5.0.1.5075.exe, file_size:27562312
file_path:/Volumes/Untitled 1/360杀毒/360sd/360AvFlt.dll, file_size:46408
file_path:/Volumes/Untitled 1/360杀毒/360sd/360AvFlt.sys, file_size:65608
file_path:/Volumes/Untitled 1/360杀毒/360sd/360Base.dll, file_size:883016
file_path:/Volumes/Untitled 1/360杀毒/360sd/360Conf.dll, file_size:270152
file_path:/Volumes/Untitled 1/360杀毒/360sd/360FileGuard.dat, file_size:2904
file_path:/Volumes/Untitled 1/360杀毒/360sd/360FileGuard.exe, file_size:1876296
file_path:/Volumes/Untitled 1/360杀毒/360sd/360NetBase.dll, file_size:293704
file_path:/Volumes/Untitled 1/360杀毒/360sd/360P2SP.dll, file_size:738120
file_path:/Volumes/Untitled 1/360杀毒/360sd/360QMachine.exe, file_size:692848
index: 1, file: /Volumes/Untitled 1/360杀毒/360sd_5.0.1.5075.exe, md5: 402c36af1471fc3757975d336b2df5c6
index: 2, file: /Volumes/Untitled 1/360杀毒/360sd/360AvFlt.dll, md5: f9d655feaf8c0b190a252d9fcba2a01d
index: 3, file: /Volumes/Untitled 1/360杀毒/360sd/360AvFlt.sys, md5: d8dee0f3bd03f49ccc30b761e42ee96f
index: 4, file: /Volumes/Untitled 1/360杀毒/360sd/360Base.dll, md5: e43e7e408bfca335cc4240b7c1bbb8ca
index: 5, file: /Volumes/Untitled 1/360杀毒/360sd/360Conf.dll, md5: f92e084de6bf6d4ca79271ebdecdac75
index: 6, file: /Volumes/Untitled 1/360杀毒/360sd/360FileGuard.dat, md5: 8e36ef17daa835665d57437730f4f67e
index: 7, file: /Volumes/Untitled 1/360杀毒/360sd/360FileGuard.exe, md5: 029307d740d4fe9804f3cb8d3346d5f4
index: 8, file: /Volumes/Untitled 1/360杀毒/360sd/360NetBase.dll, md5: 0b0787616c46750f3b14aa0ca93d2868
index: 9, file: /Volumes/Untitled 1/360杀毒/360sd/360P2SP.dll, md5: 176d4527e7fcdecee197fcf65105dc9b
index: 10, file: /Volumes/Untitled 1/360杀毒/360sd/360QMachine.exe, md5: 86e0fad7794e5da588d0717eebcaba9c
vol_path: /Volumes/Untitled
file_path:/Volumes/Untitled/desktop.ini, file_size:131
file_path:/Volumes/Untitled/360Rec/20110922/001EC.vir, file_size:4738120
file_path:/Volumes/Untitled/RECYCLER/S-1-5-21-1614895754-1935655697-1417001333-500/INFO2, file_size:20
file_path:/Volumes/Untitled/RECYCLER/S-1-5-21-1614895754-1935655697-1417001333-500/desktop.ini, file_size:65
file_path:/Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/INFO2, file_size:820
file_path:/Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/desktop.ini, file_size:65
file_path:/Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/De48/BlueStacks_HD_AppPlayerPro_setup_0.7.16.910_REL_KP(1).msi, file_size:113979392
file_path:/Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/De48/BlueStacks_HD_AppPlayerPro_setup_0.7.16.910_REL_KP(www.bluestacks.net.cn).zip, file_size:112540853
file_path:/Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/De48/mokahuanxiang_pipaw.apk, file_size:43727672
file_path:/Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/De48/蓝手指模拟器安装说明.txt, file_size:3170
index: 1, file: /Volumes/Untitled/desktop.ini, md5: 19ca074f88e2fc3731eaeb4b4a69e665
index: 2, file: /Volumes/Untitled/360Rec/20110922/001EC.vir, md5: b432085bd5b6f880c2c051a4096abf8d
index: 3, file: /Volumes/Untitled/RECYCLER/S-1-5-21-1614895754-1935655697-1417001333-500/INFO2, md5: 6b467c588be40ccdf492df4a5f914977
index: 4, file: /Volumes/Untitled/RECYCLER/S-1-5-21-1614895754-1935655697-1417001333-500/desktop.ini, md5: ad0b0b4416f06af436328a3c12dc491b
index: 5, file: /Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/INFO2, md5: e665846f4dbc65ed527c4a7588625800
index: 6, file: /Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/desktop.ini, md5: ad0b0b4416f06af436328a3c12dc491b
index: 7, file: /Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/De48/BlueStacks_HD_AppPlayerPro_setup_0.7.16.910_REL_KP(1).msi, md5: 3fbcbd4f0a2a659a55ad00d79b45d21b
index: 8, file: /Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/De48/BlueStacks_HD_AppPlayerPro_setup_0.7.16.910_REL_KP(www.bluestacks.net.cn).zip, md5: 15f9628a3b7b899d37d97ffd31e9ffe5
index: 9, file: /Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/De48/mokahuanxiang_pipaw.apk, md5: 8d57106e84fec6b436105e309b9136b5
index: 10, file: /Volumes/Untitled/RECYCLER/S-1-5-21-583907252-842925246-1801674531-500/De48/蓝手指模拟器安装说明.txt, md5: 4fe9bbb1b362f76e0b772512f8a71bf6
    '''
    pass

if __name__ == "__main__":
    root = "/Volumes"
    list = os.listdir(root)
    for volume_item in list:
        vol_path = os.path.join(root, volume_item)
        if 'Macintosh' in volume_item:
            print(f'ignore vol_path: {vol_path}')
            continue
        print(f'vol_path: {vol_path}')
        
        files = scan_directory(vol_path,limit=10)
        for idx, f in enumerate(files,start=1):
            print(f'index: {idx}, file: {f}, md5: {calculate_md5(f)}')
