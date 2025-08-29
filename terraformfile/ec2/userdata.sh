#!/bin/bash

cp -p /etc/fstab /etc/fstab.bak
mkdir /data
echo "/dev/xvdi /data xfs defaults,nofail 0 2" >> /etc/fstab
mkfs -t xfs /dev/xvdi
xfs_groefs /dev/xvdb
mount /data