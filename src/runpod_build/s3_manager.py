import boto3
import os
import shutil
from botocore.exceptions import ClientError

class S3Manager:
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.clients = {}

    def _get_client(self, endpoint_url: str):
        """Returns a cached boto3 client for the given endpoint."""
        if endpoint_url not in self.clients:
            self.clients[endpoint_url] = boto3.client(
                's3',
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=endpoint_url
            )
        return self.clients[endpoint_url]

    def download_directory(self, endpoint_url: str, bucket_name: str, s3_prefix: str, local_path: str):
        """Downloads all files from S3 with a given prefix to local path."""
        s3 = self._get_client(endpoint_url)
        if not os.path.exists(local_path):
            os.makedirs(local_path)

        paginator = s3.get_paginator('list_objects_v2')
        for result in paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix):
            if 'Contents' not in result:
                continue
            
            for obj in result['Contents']:
                key = obj['Key']
                # Create local file path
                relative_path = os.path.relpath(key, s3_prefix)
                dest_path = os.path.join(local_path, relative_path)
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                if not key.endswith('/'): # Skip directory objects
                    s3.download_file(bucket_name, key, dest_path)

    def upload_file(self, endpoint_url: str, bucket_name: str, local_path: str, s3_key: str):
        s3 = self._get_client(endpoint_url)
        s3.upload_file(local_path, bucket_name, s3_key)

    def delete_prefix(self, endpoint_url: str, bucket_name: str, s3_prefix: str):
        """Cleans up S3 objects with a given prefix."""
        s3 = self._get_client(endpoint_url)
        paginator = s3.get_paginator('list_objects_v2')
        objects_to_delete = []
        for result in paginator.paginate(Bucket=bucket_name, Prefix=s3_prefix):
            if 'Contents' in result:
                for obj in result['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
        
        if objects_to_delete:
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects_to_delete}
            )

    def object_exists(self, endpoint_url: str, bucket_name: str, key: str) -> bool:
        """Checks if a specific object exists in the bucket."""
        s3 = self._get_client(endpoint_url)
        try:
            s3.head_object(Bucket=bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            raise
