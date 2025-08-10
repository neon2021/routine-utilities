#!/sh/bin
uuid="$1"
echo "uuid: ",$uuid
dev_mount_point=$(blkid | grep "$1" | cut -d':' -f 1)
echo "dev_mount_point:", $dev_mount_point
mount $dev_mount_point