import re
try:
    from ..provisioner.sdsb_volume_provisioner import SDSBVolumeProvisioner
    from ..provisioner.sdsb_pool_provisioner import SDSBPoolProvisioner
    from ..provisioner.sdsb_compute_node_provisioner import SDSBComputeNodeProvisioner
    from ..model.sdsb_volume_models import *
    from ..common.hv_constants import StateValue
    from ..common.hv_log import Log
    from ..common.ansible_common import log_entry_exit
    from ..message.sdsb_volume_msgs import SDSBVolValidationMsg
except ImportError:
    from provisioner.sdsb_volume_provisioner import SDSBVolumeProvisioner
    from provisioner.sdsb_pool_provisioner import SDSBPoolProvisioner
    from provisioner.sdsb_compute_node_provisioner import SDSBComputeNodeProvisioner
    from model.sdsb_volume_models import *
    from common.hv_constants import StateValue
    from common.hv_log import Log
    from common.ansible_common import log_entry_exit
    from message.sdsb_volume_msgs import SDSBVolValidationMsg

logger = Log()
moduleName = "SDS Block Volume"

class SDSBVolumeSubstates:
    """
    Enum class for SDSB Volume Substates
    """
    ADD_COMPUTE_NODE = "add_compute_node"
    REMOVE_COMPUTE_NODE = "remove_compute_node"


class SDSBVolumeReconciler:

    def __init__(self, connection_info):
        self.connection_info = connection_info
        self.provisioner = SDSBVolumeProvisioner(self.connection_info)
        # self._validate_parameters()

    @log_entry_exit
    def reconcile_volume(self, state, spec):
        logger.writeDebug("RC:=== reconcile_volume ===")

        if spec is None:
            raise ValueError(SDSBVolValidationMsg.NO_SPEC.value)

        if state.lower() == StateValue.PRESENT:
            if spec.id is not None:
                logger.writeDebug("RC:=== spec.id is not None ===")
                # user provided an id of the volume, so this must be an update
                volume = self.get_volume_by_id(spec.id)
                if volume is not None:
                    vol = volume
                    logger.writeDebug("RC:volume={}", vol)
                    return self.update_sdsb_volume(vol, spec)
                else:
                    logger.writeDebug(
                        "RC:=== spec.id is not None but volume is None ==="
                    )
                    raise ValueError(SDSBVolValidationMsg.VOL_ID_ABSENT.value.format(spec.id))

            else:
                # this could be a create or an update
                if spec.name is not None:
                    logger.writeDebug("RC:=== spec.name is not None ===")
                    volume = self.get_volume_by_name(spec.name)

                    if volume is not None:
                        # this is an update
                        vol = volume
                        logger.writeDebug("RC:volume={}", vol)
                        return self.update_sdsb_volume(vol, spec)
                    else:
                        # this is a create
                        return self.create_sdsb_volume(spec)
                else:
                    raise ValueError(SDSBVolValidationMsg.NO_NAME_ID.value)

        if state.lower() == StateValue.ABSENT:
            logger.writeDebug("RC:=== Delete Volume ===")
            logger.writeDebug("RC:state = {}", state)
            logger.writeDebug("RC:spec = {}", spec)
            if spec.id is not None:
                # user provided an id of the volume, so this must be a delete
                # compue_node_id = self.delete_compute_node_by_id(spec.id)
                # return compue_node_id
                volume_id = spec.id
            elif spec.name is not None:
                # user provided an compute node name, so this must be a delete
                volume = self.get_volume_by_name(spec.name)
                logger.writeDebug("RC:volume={}", volume)
                volume_id = volume.id
                # compue_node_id = self.delete_compute_node_by_id(compute_node.id)
                # return compute_node.nickname
            else:
                raise ValueError(SDSBVolValidationMsg.NO_NAME_ID.value)

            vol_id = self.delete_volume_by_id(volume_id)
            if vol_id is not None:
                return "Volume has been deleted successfully."
            else:
                return "Could not delete volume."


    @log_entry_exit
    def get_pool_id(self, pool_name):
        pool_details = SDSBPoolProvisioner(self.connection_info).get_pool_by_name(pool_name)
        if pool_details:
            return pool_details.id
        else:
            return None

    @log_entry_exit
    def get_compute_nodes_summary(self, vol_id):
        server_ids = self.get_volume_compute_node_ids(vol_id)
        cn_prov = SDSBComputeNodeProvisioner(self.connection_info)
        cn_summary_list = []
        for id in server_ids:
            compute_node = cn_prov.get_compute_node_by_id(id)
            cnsi = ComputeNodeSummaryInfo(id, compute_node.nickname)
            cn_summary_list.append(cnsi)
        
        return cn_summary_list

    @log_entry_exit
    def get_volumes(self, volume_spec=None):
        volumes = self.provisioner.get_volumes(volume_spec)

        vols_with_cn_list = []
        for vol in volumes.data:
            if vol.numberOfConnectingServers > 0:
                cn_summary = self.get_compute_nodes_summary(vol.id)
            else:
                cn_summary = []
            vol_with_cn = SDSBVolumeAndComputeNodeInfo(vol, cn_summary)
            vols_with_cn_list.append(vol_with_cn)

        # return volumes
        return SDSBVolumeAndComputeNodeList(data=vols_with_cn_list)

    @log_entry_exit
    def get_all_volume_names(self):
        return self.provisioner.get_all_volume_names()
    
    @log_entry_exit
    def get_volume_by_id(self, id):
        volume = self.provisioner.get_volume_by_id(id)
        logger.writeDebug("RC:get_volume_by_id:volume={}", volume)
        return volume

    @log_entry_exit
    def get_volume_by_name(self, vol_name):
        vol= self.provisioner.get_volume_by_name(vol_name)
        return vol

    @log_entry_exit
    def create_sdsb_volume(self, spec):

        logger.writeDebug("RC:create_sdsb_volume:spec={}", spec)
        if spec.pool_name is None:
            raise ValueError(SDSBVolValidationMsg.POOL_NAME_EMPTY.value) 

        pool_id = self.get_pool_id(spec.pool_name)
        if not pool_id:
            raise ValueError(SDSBVolValidationMsg.POOL_NAME_NOT_FOUND.value.format(spec.pool_name))
        
        if spec.capacity is None:
            raise  ValueError(SDSBVolValidationMsg.CAPACITY.value)
        
        capacity = self.get_size_mb(spec.capacity)
        savings = self.get_saving_setting(spec.saving_setting)

        if spec.state is not None and spec.state.lower() == SDSBVolumeSubstates.REMOVE_COMPUTE_NODE:
            raise ValueError(SDSBVolValidationMsg.CONTRADICT_INFO.value)

        vol_id = self.create_volume(pool_id, spec.name, capacity, savings)
        if not vol_id:
            raise Exception("Failed to create volume")

        if spec.compute_nodes is not None and len(spec.compute_nodes) > 0:
            logger.writeDebug("RC:create_sdsb_volume:spec.compute_nodes={} vol_id={}", spec.compute_nodes, vol_id)
            self.add_volume_to_compute_nodes(spec.compute_nodes, vol_id)

        cn_summary = self.get_compute_nodes_summary(vol_id)
        vol = self.get_volume_by_id(vol_id)

        vol_with_cn = SDSBVolumeAndComputeNodeInfo(vol, cn_summary)

        # return self.get_volume_by_id(vol_id)
        return vol_with_cn
        

    @log_entry_exit
    def get_compute_node_ids(self, compute_nodes):
        cn_prov = SDSBComputeNodeProvisioner(self.connection_info)   
        cn_ids = []
        for cn in compute_nodes:
            cn_detail = cn_prov.get_compute_node_by_name(cn)
            logger.writeDebug("RC:get_compute_node_ids:cn_detail={}", cn_detail)
            if cn_detail is not None:
                cn_ids.append(cn_detail.id)

        return cn_ids


    @log_entry_exit
    def add_volume_to_compute_nodes(self, compute_nodes, vol_id):
        
        cn_ids = self.get_compute_node_ids(compute_nodes)
        if len(cn_ids) != len(compute_nodes):
            raise  ValueError(SDSBVolValidationMsg.COMPUTE_NODES_EXIST.value)

        cn_prov = SDSBComputeNodeProvisioner(self.connection_info)
        for id in cn_ids:
            cn_prov.attach_volume_to_compute_node(id, vol_id)

    @log_entry_exit
    def get_size_mb(self, size):
        logger.writeInfo("RC:get_size_mb size={}", size)
        match = re.match(r"(^\d*[.]?\d*)(\D*)", str(size))
        if match:
            sizetype = match.group(2).upper().strip() or "MB"
            logger.writeInfo("RC:get_size_mb sizetype={}", sizetype)
            if sizetype not in ("GB", "TB", "MB"):
                raise  ValueError(SDSBVolValidationMsg.CAPACITY_UNITS.value) 
            else:
                size = float(match.group(1))
                if sizetype == "TB":
                    size = size * 1024 * 1024
                if sizetype == "GB":
                    size *= 1024
            return int(size)

    @log_entry_exit
    def get_saving_setting(self, saving_setting):
        if not saving_setting:
            return "Disabled"
        
        if saving_setting.lower() not in ("disabled", "compression"):
            raise ValueError(SDSBVolValidationMsg.SAVING_SETTING.value)
        
        if saving_setting.lower() == "disabled":
            return "Disabled"
        else:
            return "Compression"

    @log_entry_exit        
    def create_volume(self, pool_id, name, capacity, savings):
        self.connection_info.changed = True
        return self.provisioner.create_volume(pool_id, name, capacity, savings)


    @log_entry_exit
    def get_volume_compute_node_ids(self, vol_id):
        cn_prov = SDSBComputeNodeProvisioner(self.connection_info)
        return cn_prov.get_volume_compute_node_ids(vol_id)

    @log_entry_exit
    def detach_volume_from_compute_node(self, cn_id, vol_id):
        self.connection_info.changed = True
        cn_prov = SDSBComputeNodeProvisioner(self.connection_info)
        cn_prov.detach_volume_from_compute_node(cn_id, vol_id)

    @log_entry_exit
    def detach_compute_nodes_from_volume(self, vol_id):
        server_ids = self.get_volume_compute_node_ids(vol_id)
        for id in server_ids:
            logger.writeDebug(
                "RC:detach_compute_nodes_from_volume: server_id={} vol_id={}", id, vol_id
            )
            # detach the volume from the compute node
            self.detach_volume_from_compute_node(id, vol_id)

    @log_entry_exit
    def delete_volume_by_id(self, id):
        self.detach_compute_nodes_from_volume(id)
        # get the volume information
        vol = self.provisioner.get_volume_by_id(id)
        logger.writeDebug("RC:delete_volume_by_id:vol={}", vol)
        # if the volume is not attached to any compute node, delete the volume
        response = None
        if vol.numberOfConnectingServers == 0:
            self.connection_info.changed = True
            response = self.provisioner.delete_volume(id)
            logger.writeDebug("RC:delete_volume_by_id:response={}", response)
        return response

    @log_entry_exit
    def attach_volume_to_compute_node(self, cn_id, vol_id):

        cn_prov = SDSBComputeNodeProvisioner(self.connection_info)
        self.connection_info.changed = True
        cn_prov.attach_volume_to_compute_node(cn_id, vol_id)

    @log_entry_exit
    def update_sdsb_volume(self, volume_data, spec):

        self.expand_volume_capacity(volume_data, spec)
        self.update_volume(volume_data, spec)

        if spec.state is not None:
            if spec.state.lower() == SDSBVolumeSubstates.ADD_COMPUTE_NODE:
                self.update_add_compute_nodes(volume_data.id, spec.compute_nodes)
            elif spec.state.lower() == SDSBVolumeSubstates.REMOVE_COMPUTE_NODE:
                self.update_remove_compute_nodes(volume_data.id, spec.compute_nodes)
            else:
                raise Exception(
                    "Invalid state provided in the spec. Valid states in the spec are : {}, and {}",
                    SDSBVolumeSubstates.ADD_COMPUTE_NODE,
                    SDSBVolumeSubstates.REMOVE_COMPUTE_NODE
                )
        cn_summary = self.get_compute_nodes_summary(volume_data.id)
        vol = self.get_volume_by_id(volume_data.id)

        vol_with_cn = SDSBVolumeAndComputeNodeInfo(vol, cn_summary)

        # return self.get_volume_by_id(vol_id)
        return vol_with_cn
        #return self.get_volume_by_id(volume_data.id)

    @log_entry_exit
    def update_add_compute_nodes(self, volume_id, compute_nodes):
        if compute_nodes is None or len(compute_nodes) == 0:
            return

        # get the compute node ids supplied in the spec
        cn_ids = self.get_compute_node_ids(compute_nodes)

        # get the compute node ids to which this volume is attached
        server_ids = self.get_volume_compute_node_ids(volume_id)

        for id in cn_ids:
            if id not in server_ids:
                logger.writeDebug(
                    "RC:update_add_compute_nodes: server_id={} vol_id={}", id, volume_id
                )
                # detach the volume from the compute node
                self.attach_volume_to_compute_node(id, volume_id)

    @log_entry_exit
    def update_remove_compute_nodes(self, volume_id, compute_nodes):

        if compute_nodes is None or len(compute_nodes) == 0:
            return

        # if len(compute_nodes) == 0:
        #     self.detach_compute_nodes_from_volume(volume_id)
        #     return

        # get the compute node ids supplied in the spec
        cn_ids = self.get_compute_node_ids(compute_nodes)

        # get the compute node ids to which this volume is attached
        server_ids = self.get_volume_compute_node_ids(volume_id)

        for id in cn_ids:
            if id in server_ids:
                logger.writeDebug(
                    "RC:update_remove_compute_nodes: server_id={} vol_id={}", id, volume_id
                )
                # detach the volume from the compute node
                self.detach_volume_from_compute_node(id, volume_id)
        return

    @log_entry_exit
    def expand_volume_capacity(self, volume_data, spec):
        # Expand the volume if its required
        if spec.capacity:
            size_mb = self.get_size_mb(spec.capacity)
            expand_val = size_mb - (
                volume_data.totalCapacity if volume_data.totalCapacity else 0
            )
            logger.writeDebug(
                    "RC:expand_volume_capacity:expand_val={}", expand_val
            )
            if (expand_val > 0):
                self.provisioner.expand_volume_capacity(volume_data.id, expand_val)
                self.connection_info.changed = True
            elif (expand_val < 0):
                raise ValueError(SDSBVolValidationMsg.INVALID_CAPACITY.value)
            else:
                pass
        return

    @log_entry_exit
    def update_volume(self, volume_data, spec):
        # update the volume by comparing the existing details
        new_name = None
        new_nickname = None
        if (spec.name and spec.name != volume_data.name):
            new_name = spec.name
        if (spec.nickname and spec.nickname != volume_data.nickname):
            new_nickname = spec.nickname
        logger.writeDebug(
            "RC:update_volume:new_name= {}, new_nickname={}", new_name, new_nickname
        )
        if new_name or new_nickname:
            self.provisioner.update_volume(volume_data.id, new_name, new_nickname)
            self.connection_info.changed = True
        return
