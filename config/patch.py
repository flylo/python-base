import logging
from types import MethodType
from functools import partial
from kubernetes.client import CoreV1Api, ApiClient
from kubernetes.client.rest import ApiException

logger = logging.getLogger('basic')


class RetryingApiWrapper(object):

    def __init__(self,
                 client_provider,
                 api_cls,
                 failure_tolerance=None,
                 status_codes_to_catch=None):
        self._client_provider = client_provider
        self.num_failures = 0
        self._failure_tolerance = failure_tolerance
        self._status_codes = status_codes_to_catch
        self._api_clazz = api_cls
        self._api = None
        self.__refresh_api()

    def __refresh_api(self):
        self._api = self._api_clazz(api_client=self._client_provider())

    def wrap_api_call(self, unbound_method, *args, **kwargs):
        try:
            partially_applied_method = partial(unbound_method, *args, **kwargs)
            bound_method = MethodType(partially_applied_method, self._api, self._api_clazz)
            return bound_method()
        except ApiException as e:
            logger.info('Caught exception %s in %s ' % (e, unbound_method.__name__,))
            self.num_failures += 1
            if self._status_codes is not None:
                if e.status not in self._status_codes:
                    raise e
            if self._failure_tolerance is not None:
                if self.num_failures > self._failure_tolerance:
                    raise e
            self.__refresh_api()
            return self.wrap_api_call(unbound_method, *args, **kwargs)


# retry_wrapper = RetryingApiWrapper(lambda x: ApiClient(), api_cls=CoreV1Api)
# retry_wrapper.wrap_api_call(CoreV1Api.connect_delete_namespaced_pod_proxy)
