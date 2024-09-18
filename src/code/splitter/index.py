import json
import os
import oss2
from langchain_text_splitters import RecursiveCharacterTextSplitter


# TODO: 此函数 runtime role 需要添加访问 OSS 的权限
def handler(event, context):
    """
    event:
    {
        "region": "region",
        "bucketName": "xxx",
        "objectName": "xxx"
    }
    """
    print("event: ", event)
    event_obj = json.loads(event)
    region = event_obj["region"]
    bucket_name = event_obj["bucketName"]
    object_name = event_obj["objectName"]

    # load data from oss
    # 如果与当前函数同 region=>内网拉取，else => 外网拉取
    creds = context.credentials

    # 设置权鉴，供OSS sdk使用。
    # Setup auth, required by OSS sdk.
    auth = oss2.StsAuth(
        creds.access_key_id,
        creds.access_key_secret,
        creds.security_token)

    endpoint = f"http://oss-{region}.aliyuncs.com"
    if context.region == event_obj["region"]:
        endpoint = f"http://oss-{context.region}-internal.aliyuncs.com"

    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    local_path = f'/tmp/{bucket_name}/{object_name}'
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    # with open(local_path, 'w') as file:
    #     pass  # 不做任何操作，文件会被创建但内容为空

    print("local path: ", local_path)
    print("event obj: ", event_obj)
    bucket.get_object_to_file(object_name, local_path)

    splitter = TextSplitter(local_path)
    splitter.set_source(f"oss://{bucket_name}/{object_name}")
    return splitter.split_text()

class TextSplitter:
    def __init__(self, file_path):
        with open(file_path) as f:
            self.content = f.read()
            self.source = file_path
        self.text_splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n\n",
                "\n",
                " ",
                ".",
                ",",
                "\u200b",  # Zero-width space
                "\uff0c",  # Fullwidth comma
                "\u3001",  # Ideographic comma
                "\uff0e",  # Fullwidth full stop
                "\u3002",  # Ideographic full stop
                "",
            ],
            # Set a really small chunk size, just to show.
            # TODO:这些配置可以通过环境变量去配
            chunk_size=os.getenv("CHUNK_SIZE", 300),
            chunk_overlap=os.getenv("CHUNK_OVERLAP", 100),
            length_function=len,
            is_separator_regex=True,
        )

    def set_source(self, source):
        self.source = source

    def split_text(self):
        res = self.text_splitter.split_text(self.content)
        resp = []
        for i, chunk in enumerate(res):
            resp.append({
                "document": chunk,
                "source": self.source,
            })

            # 打印分割后的文本块
            print(f"Chunk {i + 1}: {chunk}")

        return resp

