#!/sh/bin
uuid="$1"
echo "uuid: ",$uuid
line=$(blkid | grep "$1")
echo "dev_mount_point:", $line

# 输入是 blkid 的一行输出，例如：
# /dev/nvme0n1p2: UUID="456215e7-..." BLOCK_SIZE="4096" TYPE="ext4" PARTUUID="fa32472c-..."
# /dev/sdc1: LABEL="OldSeagate4" UUID="6239-..." BLOCK_SIZE="512" TYPE="exfat" PARTUUID="1a0e6c29-..."

# 提取 mount_path
mount_path=$(echo "$line" | cut -d":" -f1)

# 提取 TYPE
format=$(echo "$line" | sed -n 's/.*TYPE="\([^"]*\)".*/\1/p')

# 提取 PARTUUID
partuuid=$(echo "$line" | sed -n 's/.*PARTUUID="\([^"]*\)".*/\1/p')

# 提取 UUID
uuid=$(echo "$line" | sed -n 's/.* UUID="\([^"]*\)".*/\1/p')

echo "mount_path:$mount_path,format:$format,partuuid:$partuuid,uuid:$uuid"

# 如果 PARTUUID 为空则用 UUID
if [ -z "$partuuid" ]; then
    mount_dir="$uuid"
else
    mount_dir="$partuuid"
fi

# 输出挂载命令
echo "sudo mount -t $format $mount_path /mnt/$mount_dir"
mkdir /mnt/$mount_dir
mount -t $format $mount_path /mnt/$mount_dir