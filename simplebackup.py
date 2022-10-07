#!/usr/bin/env python

from tools import cli, tasks, service_instance
from datetime import datetime

data = {}
nameOfSnapshot = 'Backup'
backupToDatastore = '[NFS-Backup]'


def createSnapshot(vm):
    print('Creating snapshot for VM:', vm.summary.config.name)
    task: object = vm.CreateSnapshot_Task(name=nameOfSnapshot,
                                          description="Automatic backup " + datetime.now().strftime(
                                              "%Y-%m-%d %H:%M:%s"),
                                          memory=True,
                                          quiesce=False)
    return task


def createFolderOnDatastore(fileManager, datacenter, folderName):
    folderPath = backupToDatastore + " " + folderName

    # Create directory in Datastore
    fileManager.MakeDirectory(name=folderPath,
                              datacenter=datacenter,
                              createParentDirectories=True)

    return folderPath


def copyVmFileToDatastore(fileManager, datacenter, sourceName, destinationName, force):
    # Copy file
    print("Copying file", sourceName, "to", destinationName)
    task = fileManager.CopyDatastoreFile_Task(sourceName=sourceName,
                                              sourceDatacenter=datacenter,
                                              destinationName=destinationName,
                                              destinationDatacenter=None,
                                              force=force)
    return task


def copyVmDiskToDatastore(diskManager, datacenter, sourceName, destinationName, force):
    # Copy disk
    print("Copying disk", sourceName, "to", destinationName)
    task = diskManager.CopyVirtualDisk_Task(sourceName=sourceName,
                                            sourceDatacenter=datacenter,
                                            destName=destinationName,
                                            destSpec=None,
                                            force=force)
    return task


def getSnapshotByName(snapshotList):
    for snapshot in snapshotList:
        if snapshot.name == nameOfSnapshot:
            return snapshot


def removeSnapshot(vm):
    print('Removing snapshot for VM:', vm.summary.config.name)
    snapshot = getSnapshotByName(vm.snapshot.rootSnapshotList)
    task: object = snapshot.snapshot.RemoveSnapshot_Task(removeChildren=True)

    return task


def main():
    """
    Iterate through all datacenters and list VM info.
    """
    parser = cli.Parser()
    args = parser.get_args()
    si = service_instance.connect(args)

    content = si.RetrieveContent()
    children = content.rootFolder.childEntity
    fileMgr = content.fileManager
    diskMgr = content.virtualDiskManager

    for child in children:  # Iterate though DataCenters
        datacenter = child
        data[datacenter.name] = {}  # Add data Centers to data dict
        clusters = datacenter.hostFolder.childEntity
        for cluster in clusters:  # Iterate through the clusters in the DC
            # Add Clusters to data dict
            data[datacenter.name][cluster.name] = {}
            hosts = cluster.host  # Variable to make pep8 compliance
            for host in hosts:  # Iterate through Hosts in the Cluster
                hostname = host.summary.config.name
                # Add VMs to data dict by config name
                data[datacenter.name][cluster.name][hostname] = {}
                vms = host.vm
                for vm in vms:  # Iterate through each VM on the host
                    vmsToBackup = open('backup.list', 'r')
                    for vmToBackup in vmsToBackup:
                        if vmToBackup in vm.summary.config.name:
                            # Create folder
                            folderPath = createFolderOnDatastore(fileMgr,
                                                                 datacenter,
                                                                 datetime.now().strftime("%Y-%m-%d") +
                                                                     "/" + vm.summary.config.name)

                            # Copy VMX file
                            task = copyVmFileToDatastore(fileMgr,
                                                         datacenter,
                                                         vm.config.files.vmPathName,
                                                         folderPath + "/" + vm.summary.config.name + ".vmx",
                                                         True)
                            tasks.wait_for_tasks(si, [task])
                            print('File copy finished!')

                            # Create Snapshot of VM
                            task = createSnapshot(vm)
                            tasks.wait_for_tasks(si, [task])
                            print('Snapshot creation finished!')

                            # Copy the Parent VMDKs
                            for device in vm.config.hardware.device:
                                if device.__class__.__name__ == 'vim.vm.device.VirtualDisk':
                                    task = copyVmDiskToDatastore(diskMgr,
                                                                 datacenter,
                                                                 device.backing.parent.fileName,
                                                                 folderPath + "/" +
                                                                     device.backing.parent.fileName.rsplit('/')[1],
                                                                 False)
                                    tasks.wait_for_tasks(si, [task])
                                    print('Disk copy finished!')
                            print('Backup finished!')

                            task = removeSnapshot(vm)
                            tasks.wait_for_tasks(si, [task])
                            print('Snapshot deletion finished!')
                    vmsToBackup.close()


# Start program
if __name__ == "__main__":
    main()
