#!/usr/bin/env python

from pyVmomi import vmodl, vim
from tools import cli, tasks, service_instance, pchelper
from datetime import datetime

data = {}
nameOfSnapshot = 'Backup'
backupToDatastore = ''


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
    parser.add_custom_argument('--backupDS', required=True, help='Datastore name to backup to.')
    args = parser.get_args()

    global backupToDatastore
    backupToDatastore = '[' + args.backupDS + ']'

    try:
        si = service_instance.connect(args)
    except vim.fault.InvalidLogin as il:
        print(il.msg)
        return -1

    try:
        content = si.RetrieveContent()
        children = content.rootFolder.childEntity
        fileMgr = content.fileManager
        diskMgr = content.virtualDiskManager

        # Check Backup Datastore exists
        datastore = pchelper.search_for_obj(content, [vim.Datastore], args.backupDS)
        if not datastore:
            print("Datastore [", args.backupDS, "] cannot be found...")
            return -1

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
                    vmsToBackup = open('backup.list', 'r')
                    for vmToBackup in vmsToBackup:
                        for vm in vms:  # Iterate through each VM on the host
                            if str(vmToBackup.rstrip()) in vm.summary.config.name:
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
                                    # if device.__class__.__name__ == 'vim.vm.device.VirtualDisk':
                                    if isinstance(device, vim.vm.device.VirtualDisk):
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

    except vmodl.MethodFault as error:
        print("Caught vmodl fault : " + error.msg)
        return -1


# Start program
if __name__ == "__main__":
    main()
