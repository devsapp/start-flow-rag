# -*- coding: utf-8 -*-
import json
import os

import uvicorn
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Header
from schema import *

from alibabacloud_fnf20190315.client import Client as fnf20190315Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_fnf20190315 import models as fnf_20190315_models
from alibabacloud_tea_util import models as util_models

app = FastAPI()


# Return success to options
@app.options("/v1/chat/completions")
async def root():
    return {"message": "success"}


# 搞清楚 OpenAI 的 Chat 格式嘛

@app.post("/v1/chat/completions")
def create_chat_completion(
        req: CreateChatCompletionRequest,
        x_fc_access_key_id: Optional[str] = Header(None),
        x_fc_access_key_secret: Optional[str] = Header(None),
        x_fc_security_token: Optional[str] = Header(None),
        x_fc_region: Optional[str] = Header(None),
):
    client = create_client(x_fc_access_key_id, x_fc_access_key_secret, x_fc_security_token, x_fc_region)
    return StreamingResponse(start_execution(client, req), media_type="text/event-stream")


def create_client(ak, sk, token, region) -> fnf20190315Client:
    config = open_api_models.Config(
        access_key_id=ak,
        access_key_secret=sk,
        security_token=token
    )
    config.endpoint = f'{region}.fnf.aliyuncs.com'
    return fnf20190315Client(config)


def start_execution(client, req):
    print("Start execution req: ", req.json())

    start_sync_execution_request = fnf_20190315_models.StartSyncExecutionRequest(
        flow_name=os.getenv("FLOW_NAME"),
        input=json.dumps({
            "query": req.messages[-1].content,
            "req": req.json()
        })
    )
    runtime = util_models.RuntimeOptions(
            read_timeout=60000,
            connect_timeout=60000)
    try:
        resp = client.start_sync_execution_with_options(start_sync_execution_request, runtime)
        return json.loads(resp.body.output)["Body"]

    except Exception as error:
        print(error)
        raise error


if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", reload=True)
