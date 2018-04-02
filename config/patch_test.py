import os

import multiprocessing
import unittest
import uuid
from functools import partial
from time import sleep

import functools

import datetime
from kubernetes.client import V1ObjectMeta, V1PodSpec, V1Pod, ApiClient, CoreV1Api
from kubernetes.config import new_client_from_config
from kubernetes.config.kube_config import KubeConfigLoader, ConfigNode
from kubernetes.config.kube_config_test import TEST_DATA_BASE64

from config.kube_config_test import TEST_TOKEN_EXPIRY, TEST_USERNAME, TEST_PASSWORD, TEST_ANOTHER_DATA_BASE64, \
    BaseTestCase, FakeConfig, TEST_HOST
# from config.patch import RetryingApiWrapper
from config.patch import RetryingApiWrapper


def _create_pod_payload(pod_name, container_payload, volumes):
    spec = V1PodSpec(containers=[container_payload],
                     restart_policy="Never",
                     volumes=volumes)
    return V1Pod(spec=spec, metadata=V1ObjectMeta(name=pod_name))


def provide_exception_throwing_payload(pod_name):
    pod_payload = _create_pod_payload(pod_name=pod_name,
                                      container_payload=None,
                                      volumes=[None])
    return pod_payload


def eventually_assert_process_exitcode(target_process, duration_seconds,
                                       expected_exit_code, *args):
    p = multiprocessing.Process(target=target_process,
                                args=list(args))
    p.start()
    sleep(duration_seconds)
    p.terminate()
    p.join()
    assert p.exitcode == expected_exit_code


# class BaseRetryingTestCase():
class TestPatch(BaseTestCase):
    TEST_KUBE_CONFIG = {
        "contexts": [
            {
                "name": "expired_gcp",
                "context": {
                    "cluster": "default",
                    "user": "expired_gcp"
                }
            }
        ],
        "users": [
            {
                "name": "expired_gcp",
                "user": {
                    "auth-provider": {
                        "name": "gcp",
                        "config": {
                            "access-token": TEST_DATA_BASE64,
                            "expiry": TEST_TOKEN_EXPIRY,  # always in past
                        }
                    },
                    "token": TEST_DATA_BASE64,  # should be ignored
                    "username": TEST_USERNAME,  # should be ignored
                    "password": TEST_PASSWORD,  # should be ignored
                }
            }],
        "clusters": [
            {
                "name": "default",
                "cluster": {
                    "server": TEST_HOST
                }
            }]
    }
    config = KubeConfigLoader(
        config_dict=TEST_KUBE_CONFIG, active_context="expired_gcp").load_and_set(FakeConfig(verify_ssl=False))

    @staticmethod
    def client_provider():
        return ApiClient(configuration=ConfigNode("trollname",
                                                  TestPatch.config))

    def test_stuff(self):
        retry_wrapper = RetryingApiWrapper(TestPatch.client_provider,
                                           api_cls=CoreV1Api,
                                           failure_tolerance=1)
        retry_wrapper.wrap_api_call(CoreV1Api.read_namespaced_pod,
                                    "trollname", "trollnamespace")
        #
        # def cred(): return None
        #
        # cred.token = TEST_ANOTHER_DATA_BASE64
        # cred.expiry = datetime.datetime.now()

        # loader = KubeConfigLoader(
        #     config_dict=self.TEST_KUBE_CONFIG,
        #     active_context="expired_gcp",
        #     get_google_credentials=lambda: cred)
        # loader._config

#
# class TestKubernetesClient(KubeConfigTestCase):
#     name = "test-pod-%s" % str(uuid.uuid4())
#
#     # we catch 422 because that is the "Unprocessable Entity" exception
#     # we've created with our malformed payload
#     @nottest
#     def _provide_default_client(self, failure_tolerance, status_codes_to_catch={422}):
#         return
#         # return SimpleKubernetesPodClient(image_id=None, pod_name=self.name,
#         #                                  failure_tolerance=failure_tolerance,
#         #                                  status_codes_to_catch=status_codes_to_catch)
#
#     def test_expiry_refresh(self):
#         client = self._provide_default_client(failure_tolerance=1)
#         self.assertRaises(ApiException, client.submit_pod,
#                           provide_exception_throwing_payload(self.name))
#         first_expiry = get_config_expiry(TEST_KUBE_CFG)
#         set_config_expiry(TEST_KUBE_CFG, EXPIRED_TIMESTAMP)
#         expired_expiry = get_config_expiry(TEST_KUBE_CFG)
#         assert first_expiry > expired_expiry
#         # we make a new client to reset the exception counter
#         client = self._provide_default_client(failure_tolerance=1)
#         self.assertRaises(ApiException, client.submit_pod,
#                           provide_exception_throwing_payload(self.name))
#         new_expiry = get_config_expiry(TEST_KUBE_CFG)
#         # NOTE we use >= here because jenkins box does some caching of the original expiry time
#         assert new_expiry >= first_expiry
#
#     def test_failure_counter(self):
#         client = self._provide_default_client(failure_tolerance=5)
#         self.assertRaises(ApiException, client.submit_pod,
#                           provide_exception_throwing_payload(self.name))
#         assert client.api.num_failures == 6
#
#     def test_undefined_failure_tolerance(self):
#         non_failure_exit_code = -15
#         failure_exit_code = 1
#         duration_seconds = 5
#         # assert that a client run for n seconds errors when tolerance is defined
#         client = self._provide_default_client(failure_tolerance=1)
#         eventually_assert_process_exitcode(client.submit_pod, duration_seconds,
#                                            failure_exit_code,
#                                            provide_exception_throwing_payload(self.name))
#         # assert that a client run for n seconds doesnt error when tolerance is undefined
#         client = self._provide_default_client(failure_tolerance=None)
#         eventually_assert_process_exitcode(client.submit_pod, duration_seconds,
#                                            non_failure_exit_code,
#                                            provide_exception_throwing_payload(self.name))
#
#     def test_status_code_checking(self):
#         # we expect to be throwing 422s with this bad payload...
#         client = self._provide_default_client(failure_tolerance=3)
#         self.assertRaises(ApiException, client.submit_pod,
#                           provide_exception_throwing_payload(self.name))
#         # ...therefore, it should run until failure tolerance is surpassed
#         assert client.api.num_failures == 4
#         # we should not be throwing 401s...
#         client = self._provide_default_client(failure_tolerance=3, status_codes_to_catch={401})
#         self.assertRaises(ApiException, client.submit_pod,
#                           provide_exception_throwing_payload(self.name))
#         # ...therefore, it should fail on the first try
#         assert client.api.num_failures == 1
