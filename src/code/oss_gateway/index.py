# -*- coding: utf-8 -*-
import os
import json
from alibabacloud_fnf20190315.client import Client as fnf20190315Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_fnf20190315 import models as fnf_20190315_models
from alibabacloud_tea_util import models as util_models


def handler(event, context):
    # 通过context.credentials 获取密钥信息。
    # Access credentials through context.credentials
    creds = context.credentials

    # Load event content.
    event_obj = json.loads(event)
    print(event_obj)

    # Get oss event related parameters passed by oss trigger.
    info = event_obj['events'][0]
    bucket_name = info['oss']['bucket']['name']
    region = info['region']
    object_name = info['oss']['object']['key']

    payload = {
        "bucketName": bucket_name,
        "region": region,
        "objectName": object_name
    }
    client = create_client(creds.access_key_id,
                           creds.access_key_secret,
                           creds.security_token,
                           context.region)

    return start_execution(client, payload)


def create_client(ak, sk, security_token, region) -> fnf20190315Client:
    """
    使用AK&SK初始化账号Client
    @return: Client
    @throws Exception
    """
    config = open_api_models.Config(
        access_key_id=ak,
        access_key_secret=sk,
        security_token=security_token
    )
    config.endpoint = f'{region}.fnf.aliyuncs.com'
    return fnf20190315Client(config)


def start_execution(client, payload) -> None:
    start_sync_execution_request = fnf_20190315_models.StartSyncExecutionRequest(
        flow_name=os.getenv("flow_name"),
        input=json.dumps(payload)
    )
    runtime = util_models.RuntimeOptions()
    try:
        client.start_sync_execution_with_options(start_sync_execution_request, runtime)
        return {"statusCode": 200, "body": "success"}
    except Exception as error:
        print(error)
        raise error
