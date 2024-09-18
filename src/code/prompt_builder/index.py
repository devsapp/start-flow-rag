# 基于 prompt_template 生成 prompt
import json

# RAG Template
template = """
根据上下文回答问题，请用简体中文简洁地回答"。

    上下文:
    \"\"\"
    {}
    \"\"\"

    问题: {}
    """


def handler(event, ctx):
    evt_obj = json.loads(event)
    query = evt_obj["query"]
    context = evt_obj["context"]
    return template.format(context, query)
