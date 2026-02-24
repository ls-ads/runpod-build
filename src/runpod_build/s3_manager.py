import boto3
import os
import shutil
from botocore.exceptions import ClientError

class S3Manager:
    def __init__(self, access_key: str, secret_key: str, region: str, bucket_name: str):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        self.bucket_name = bucket_name

    def download_directory(self, s3_prefix: str, local_path: str):
        """Downloads all files from S3 with a given prefix to local path."""
        if not os.path.exists(local_path):
            os.makedirs(local_path)

        paginator = self.s3.get_paginator('list_objects_v2')
        for result in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
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
                    self.s3.download_file(self.bucket_name, key, dest_path)

    def upload_file(self, local_path: str, s3_key: str):
        self.s3.upload_file(local_path, self.bucket_name, s3_key)

    def delete_prefix(self, s3_prefix: str):
        """Cleans up S3 objects with a given prefix."""
        paginator = self.s3.get_paginator('list_objects_v2')
        objects_to_delete = []
        for result in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
            if 'Contents' in result:
                for obj in result['Contents']:
                    objects_to_delete.append({'Key': obj['Key']})
        
        if objects_to_delete:
            self.s3.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects_to_delete}
            )

    def object_exists(self, key: str) -> bool:
        """Checks if a specific object exists in the bucket."""
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            raise
