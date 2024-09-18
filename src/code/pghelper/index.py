import psycopg2
import json
import os

# 数据库配置信息
db_config = {
    "dbname": os.getenv("PG_DATABASE"),
    "user": os.getenv("PG_USER"),
    "password": os.getenv("PG_PASSWORD"),
    "host": os.getenv("PG_HOST"),
    "port": os.getenv("PG_PORT", "5432")
}

table_name = os.getenv("tableName")

# 向量维度
dim = int(os.getenv("dimension"))  # 768/1024/1056

indexs = ("source", "document", "embedding")

global vectordb


def initializer(context):
    global vectordb
    vectordb = pgvector(**db_config)


def preStop(context):
    vectordb.close()


"""
Insert:
- Input:
    {
        "action": "insert",
        "body": {
            "embedding": [],
            "source": "xxx",
            "document": "xxx"
        }
    }
- Output
    成功：
    {
        "status": 200
    }
    失败：raise Exception，让上游重试，并让函数观测到失败

Query:
- Input:
      {
        "action": "insert",
        "body": {
            "embedding": []
        }
    }
- Output:
"""


def handler(event, context):
    evt_obj = json.loads(event)
    if evt_obj["action"] == "insert":
        return vectordb.insert(evt_obj["body"])
    elif evt_obj["action"] == "query":
        return vectordb.query(evt_obj["body"])


class pgvector(object):
    def __init__(self, **config):
        self.conn = psycopg2.connect(**config)

        # create table and index
        sql = """
            CREATE TABLE IF NOT EXISTS {0}(
            id bigserial PRIMARY KEY,
            source text, -- 数据源
            document text, -- 文档分块
            embedding vector({1}));    -- 文本嵌入信息, 默认 1536（modelscope 那几个模型应该是 768）
            """.format(table_name, dim)

        cur = self.conn.cursor()
        resp = cur.execute(sql)
        self.conn.commit()
        print("Extension created successfully", resp)

    def insert(self, body):
        try:
            # 创建一个游标对象
            cursor = self.conn.cursor()
            # 插入数据的SQL语句
            insert_query = f"INSERT INTO {table_name} (source, document, embedding) VALUES (%s, %s, %s)"

            # 执行SQL语句
            cursor.execute(insert_query, (body["source"], body["document"], body["embedding"]))

            # 提交事务
            self.conn.commit()

            print("Vector data inserted successfully.")
            return {
                "status": 200
            }

        except psycopg2.Error as e:
            print(f"Error: Could not insert vector data - {e}")
            # raise exception
            raise e
        finally:
            # 关闭游标
            if cursor:
                cursor.close()

    # 从数据库中读取向量数据
    def query(self, body):
        threshhold = 0.5
        max_matched_doc_counts = 2

        # 余弦相似度范围 [-1,1]，1 表示最相似，-1 表示最不相似
        # 余弦距离：1-cosine_similarity，范围 [0,2]，0 表示最相似，2 表示最不相似
        # 通过 pgvector 过滤出相似度大于一定阈值的文档块
        similarity_search_sql = f'''
        SELECT source, document, (embedding <=> '{body["embedding"]}') AS distance
        FROM {table_name} WHERE (embedding <=> '{body["embedding"]}') < {threshhold} order BY distance  LIMIT {max_matched_doc_counts}
        '''

        try:
            cur = self.conn.cursor()
            cur.execute(similarity_search_sql)
            colnames = [desc[0] for desc in cur.description]

            # 获取查询结果
            vectors = cur.fetchall()

            print("Vector data read successfully.", vectors)
            return {
                "status": 200,
                "body": parse_resp(vectors)
            }

        except psycopg2.Error as e:
            print(f"Error: Could not read vector data - {e}")
            raise e
        finally:
            # 关闭游标
            if cur:
                cur.close()

    def close(self):
        self.conn.close()


def parse_resp(vectors):
    return [
        {
            "source": vector[0],
            "document": vector[1],
            "cosine_distance": vector[2]
        }
        for vector in vectors
    ]
