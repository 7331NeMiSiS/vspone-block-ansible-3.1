try:
    from ..common.uaig_constants import Endpoints
    from ..common.ansible_common import dicts_to_dataclass_list
    from ..common.hv_constants import CommonConstants
    from ..model.uaig_subscriber_models import *
    from ..common.hv_log import Log
    from .gateway_manager import UAIGConnectionManager
except ImportError:
    from common.uaig_constants import Endpoints
    from common.ansible_common import dicts_to_dataclass_list
    from common.hv_constants import CommonConstants
    from common.hv_log import Log
    from model.uaig_subscriber_models import *
    from .gateway_manager import UAIGConnectionManager


class SubscriberUAIGateway:

    def __init__(self, connection_info):
        funcName = "SubscriberUAIGateway: init"
        self.logger = Log()
        self.logger.writeEnterSDK(funcName)

        self.connectionManager = UAIGConnectionManager(
            connection_info.address, connection_info.username, connection_info.password, connection_info.api_token)


    def get_subscriber_facts(self, subscriberId):
        funcName = "SubscriberUAIGateway: get_subscriber_facts"
        self.logger.writeEnterSDK(funcName)

        if subscriberId is None or not subscriberId:
            end_point = Endpoints.GET_ALL_SUBSCRIBERS.format(
                partnerId=CommonConstants.PARTNER_ID
            )
        else:
            end_point = Endpoints.GET_SUBSCRIBER.format(
                partnerId=CommonConstants.PARTNER_ID, subscriberId=subscriberId
            )
        try:
            data = self.connectionManager.get(end_point)
            self.logger.writeDebug("{} Response={}", funcName, data)
            self.logger.writeExitSDK(funcName)
            return data
        except:
            return []

    def create_subscriber(self, request):
        funcName = "SubscriberUAIGateway: create_subscriber"
        self.logger.writeEnterSDK(funcName)

        request["partnerId"] = CommonConstants.PARTNER_ID
        if not request.get("softLimit"):
            request["softLimit"] = "80"
        if not request.get("hardLimit"):
            request["hardLimit"] = "90"
        body = request
        end_point = Endpoints.CREATE_SUBSCRIBER
        try:
            data = self.connectionManager.post(end_point, body)
            self.logger.writeDebug("{} Response={}", funcName, data)
            self.logger.writeExitSDK(funcName)
            return data
        except:
            return {}

    def update_subscriber(self, request):
        funcName = "SubscriberUAIGateway: update_subscriber"
        self.logger.writeEnterSDK(funcName)

        body = request
        end_point = Endpoints.UPDATE_SUBSCRIBER.format(
            partnerId=CommonConstants.PARTNER_ID, subscriberId=request["subscriberId"]
        )
        try:
            data = self.connectionManager.patch(end_point, body)
            self.logger.writeDebug("{} Response={}", funcName, data)
            self.logger.writeExitSDK(funcName)
            return data
        except:
            return {}

    def delete_subscriber(self, subscriberId):
        funcName = "SubscriberUAIGateway: delete_subscriber"
        self.logger.writeEnterSDK(funcName)

        end_point = Endpoints.DELETE_SUBSCRIBER.format(subscriberId=subscriberId)
        try:
            data = self.connectionManager.delete(end_point)
            self.logger.writeDebug("{} Response={}", funcName, data)
            self.logger.writeExitSDK(funcName)
            return "Subscriber deleted successfully"
        except Exception as e:
            return "Failed to delete subscriber as " + str(e).lower()
