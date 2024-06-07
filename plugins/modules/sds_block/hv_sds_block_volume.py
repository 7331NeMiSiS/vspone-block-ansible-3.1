import json

__metaclass__ = type

DOCUMENTATION = '''
---
module: hv_sds_block_volume
short_description: Manage Hitachi sds block storage system volumes.
description:
  - This module allows the creation, updation and deletion of volume, adding and removing compute code.
  - It supports various volume operations based on the specified state.
version_added: '3.0.0'
author:
  - Hitachi Vantara, LTD. VERSION 3.0.0
requirements:
options:
  state:
    description: The level of the volume task. Choices are 'present', 'absent'.
    type: str
    required: true
  connection_info:
    description: Information required to establish a connection to the storage system.
    required: true
    type: dict
    suboptions:
      address:
        description: IP address or hostname of the storage system.
        type: str
        required: true
      username:
        description: Username for authentication.
        type: str
        required: true
      password:
        description: Password for authentication.
        type: str
        required: true
      connection_type:
        description: Type of connection to the storage system.
        type: str
        required: false
        choices: ['direct', 'gateway']

  spec:
    description: Specification for the volume task.
    type: dict
    required: true
    suboptions:
      id:
        description: The id of the volume.
        type: str
        required: false
      name:
        description: The name of the volume.
        type: str
        required: false
      nickname:
        description: The nickname of the volume.
        type: str
        required: false
      capacity:
        description: The capacity of the volume.
        type: str
        required: false
      saving_setting:
        description: Settings of the data reduction function. Disabled or  Compression.
        type: str
        required: false
      pool_name:
        description: he name of the storage pool where the volume is created.
        type: str
        required: false
      state:
        description: The state of the volume task. Choices are 'add_compute_node', 'remove_compute_node'.
        type: str
        required: false
      compute_nodes:
        description: The array of name of compute nodes to which the volume is attached.
        type: list
        required: false

'''

EXAMPLES = '''
- name: Create volume
  hv_sds_block_volume:
    state: present
    connection_info:
      address: vssb.company.com
      username: "admin"
      password: "password"
    spec:
      pool_name: "SP01"
      name: "RD-volume-4"
      capacity: 99
      compute_nodes: ["CAPI123678", "ComputeNode-1"]

- name: Delete volume by ID
  hv_sds_block_volume:
    state: absent
    connection_info:
      address: vssb.company.com
      username: "admin"
      password: "password"
    spec:
      id: "df63a5d9-32ea-4ae1-879a-7c23fbc574db"

- name: Delete volume by name
  hv_sds_block_volume:
    state: absent
    connection_info:
      address: vssb.company.com
      username: "admin"
      password: "password"
      connection_type: "direct"
    spec:
      name: "RD-volume-4"

- name: Expand volume
  hv_sds_block_volume:
    state: present
    connection_info:
      address: vssb.company.com
      username: "admin"
      password: "password"
    spec:
      name: "RD-volume-4"
      capacity: 202

- name: Update volume nickname
  hv_sds_block_volume:
    state: present
    connection_info:
      address: vssb.company.com
      username: "admin"
      password: "password""
    spec:
      name: "RD-volume-4"
      nickname: "RD-volume-0004"
  
- name: Update volume name
  hv_sds_block_volume:
    state: present
    connection_info:
      address: vssb.company.com
      username: "admin"
      password: "password"
    spec:
      id: "aba5c900-b04c-4beb-8ca4-ed53537afb09"
      name: "RD-volume-0004"
      nickname: "RD-volume-0004"

- name: Remove compute node
  hv_sds_block_volume:
    state: present
    connection_info:
      address: vssb.company.com
      username: "admin"
      password: "password"
      connection_type: "direct"
    spec:
      state: "remove_compute_node"
      id: "aba5c900-b04c-4beb-8ca4-ed53537afb09"
      compute_nodes: ["ComputeNode-1"]

- name: Add compute node
  hv_sds_block_volume:
    state: present
    connection_info:
      address: vssb.company.com
      username: "admin"
      password: "password"
    spec:
      state: "add_compute_node"
      id: "aba5c900-b04c-4beb-8ca4-ed53537afb09"
      compute_nodes: ["ComputeNode-1"]
'''

RETURN = '''
data:
  description: The volume information.
  returned: always
  type: dict
  elements: dict/list
  sample: 
    {
      "compute_node_info": [
          {
              "id": "4f9041aa-ab2f-4789-af2e-df4a0178a4d3",
              "name": "asishtest"
          }
      ],
      "volume_info": {
          "data_reduction_effects": {
              "post_capacity_data_reduction": 0,
              "pre_capacity_data_reduction_without_system_data": 0,
              "system_data_capacity": 0
          },
          "data_reduction_progress_rate": false,
          "data_reduction_status": "Disabled",
          "full_allocated": false,
          "id": "ef69d5c6-ed7c-4302-959f-b8b8a7382f3b",
          "naa_id": "60060e810a85a000600a85a000000017",
          "name": "vol010",
          "nickname": "vol010",
          "number_of_connecting_servers": 1,
          "number_of_snapshots": 0,
          "pool_id": "cb9f7ecf-ceba-4d8e-808b-9c7bc3e59c03",
          "pool_name": "SP01",
          "protection_domain_id": "645c36b6-da9e-44bb-b711-430e06c7ad2b",
          "qos_param": {
              "upper_alert_allowable_time": -1,
              "upper_alert_time": false,
              "upper_limit_for_iops": -1,
              "upper_limit_for_transfer_rate": -1
          },
          "saving_mode": false,
          "saving_setting": "Disabled",
          "snapshot_attribute": "-",
          "snapshot_status": false,
          "status": "Normal",
          "status_summary": "Normal",
          "storage_controller_id": "fc22f6d3-2bd3-4df5-b5db-8a728e301af9",
          "total_capacity_mb": 120,
          "used_capacity_mb": 0,
          "volume_number": 23,
          "volume_type": "Normal",
          "vps_id": "(system)",
          "vps_name": "(system)"
        }
    }

'''

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.hitachivantara.vspone_block.plugins.module_utils.common.hv_constants import (
    StateValue,
)
from ansible_collections.hitachivantara.vspone_block.plugins.module_utils.reconciler.sdsb_volume import (
    SDSBVolumeReconciler,
)
from ansible_collections.hitachivantara.vspone_block.plugins.module_utils.reconciler.sdsb_properties_extractor import (
    VolumePropertiesExtractor,
     VolumeAndComputeNodePropertiesExtractor
)
from ansible_collections.hitachivantara.vspone_block.plugins.module_utils.common.hv_log import Log
from ansible_collections.hitachivantara.vspone_block.plugins.module_utils.common.sdsb_utils import (
    SDSBVolumeArguments,
    SDSBParametersManager,
)

logger = Log()


class SDSBVolumeManager:
    def __init__(self):

        self.argument_spec = SDSBVolumeArguments().volume()
        logger.writeDebug(
            f"MOD:hv_sds_block_volume:argument_spec= {self.argument_spec}"
        )
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True,
            # can be added mandotary , optional mandatory arguments
        )

        params_manager = SDSBParametersManager(self.module.params)
        self.state = params_manager.get_state()
        self.connection_info = params_manager.get_connection_info()
        # logger.writeDebug(f"MOD:hv_sds_block_volume:argument_spec= {self.connection_info}")
        self.spec = params_manager.get_volume_spec()
        logger.writeDebug(f"MOD:hv_sds_block_compute_node:argument_spec= {self.spec}")

    def apply(self):
        volumes = None
        volumes_data_extracted = None

        logger.writeInfo(
            f"{self.connection_info.connection_type} connection type"
        )
        try:
            sdsb_reconciler = SDSBVolumeReconciler(self.connection_info)
            volumes = sdsb_reconciler.reconcile_volume(self.state, self.spec)

            logger.writeDebug(f"MOD:hv_sds_block_volume:volumnes= {volumes}")
            if self.state.lower() == StateValue.ABSENT:
                volumes_data_extracted = volumes
            else:
                output_dict = volumes.to_dict()
                volumes_data_extracted =  VolumeAndComputeNodePropertiesExtractor().extract_dict(
                    output_dict
                )

        except Exception as e:
            self.module.fail_json(msg=str(e))

        response = {"changed": self.connection_info.changed, "data": volumes_data_extracted}
        self.module.exit_json(**response)


def main(module=None):
    obj_store = SDSBVolumeManager()
    obj_store.apply()


if __name__ == "__main__":
    main()
