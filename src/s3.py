from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from contextlib import asynccontextmanager
from fastapi import UploadFile
from botocore.config import Config
from src.config import ACCESS_KEY, SECRET_KEY, BUCKET_NAME


class S3Client:
    def __init__(self, access_key: str, secret_key: str, endpoint_url: str, bucket_name: str):
        self.config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
        }

        self.botocore_config = Config(signature_version="s3v4")
        self.bucket_name = bucket_name
        self.session = get_session()
    
    @asynccontextmanager
    async def get_client(self):
        async with self.session.create_client("s3", **self.config, config=self.botocore_config) as client:
            yield client

    async def upload_file(
            self,
            file: UploadFile,
            object_name: str,
    ):
        try:
            async with self.get_client() as client:
                content = await file.read()
                await client.put_object(
                    Bucket=self.bucket_name,
                    Key=object_name,
                    Body=content,
                )
        except ClientError as e:
            print(f"Error uploading file: {e}")


    async def delete_file(self, object_name: str):
        try:
            async with self.get_client() as client:
                await client.delete_object(Bucket=self.bucket_name, Key=object_name)
        except ClientError as e:
            print(f"Error deleting file: {e}")

    async def get_file(self, object_name: str):
        try:
            async with self.get_client() as client:
                response = await client.get_object(Bucket=self.bucket_name, Key=object_name)
                data = await response["Body"].read()
                return data
        except ClientError as e:
            return None


def get_s3_client() -> S3Client:
    return S3Client(
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        endpoint_url="https://storage.yandexcloud.net",
        bucket_name=BUCKET_NAME,
    )