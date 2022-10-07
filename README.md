# Simple VMware VM backup

I was looking for a simple solution to backup my home lab VMs, something which runs on Linux, lightweight and to the point.
After few research and deployments of various solutions, I ended up finding this: https://blog.erben.sk/2014/05/30/vmware-backup-script/
The libraries being somewhat old and deprecated, I decided to write my own, based on pyvmomi (https://github.com/vmware/pyvmomi).

Helpful links:

http://vmware.github.io/pyvmomi-community-samples/

https://github.com/vmware/pyvmomi-community-samples

# Usage

You will need to have `python3` and `pyvmomi`.

https://github.com/vmware/pyvmomi#installing

Add the name of the VMs to backup in the `backup.list` file, the VM name which shows in the vSphere Client.

Run the following command with your own VMware environment variables.
```
~/P/SimpleBackup> python backup.py -s vcsa.domain.local -u administrator@vsphere.local -p P@ssW0rd! -nossl --backupDS DS_Destination

```

# Output

```
Copying file [DS_Source] web.domain.local/web.domain.vmx to [DS_Destination] 2022-10-07/web.domain.local/web.domain.local.vmx
File copy finished!
Creating snapshot for VM: web.domain.local
Snapshot creation finished!
Copying disk [DS_Source] web.domain.local/web.domain.local.vmdk to [DS_Destination] 2022-10-07/web.domain.local/web.domain.local.vmdk
Disk copy finished!
Backup finished!
Removing snapshot for VM: web.domain.local
Snapshot deletion finished!
```
