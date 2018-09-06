# -*- coding: utf-8 -*-

"""
Classes for S3 Buckets.
"""

from botocore.client import Config
from botocore.exceptions import ClientError

import json
import mimetypes
from pathlib import Path


class BucketManager:
    """Manage an S3 Bucket."""

    def __init__(self, session):
        self.session = session
        self.s3 = self.session.resource('s3')

    def all_buckets(self):
        """Get an iterator for all buckets."""

        return self.s3.buckets.all()

    def all_objects(self, bucket_name):
        """Get an iterator in an s3 bucket."""

        return self.s3.Bucket(bucket_name).objects.all()

    def create_bucket(self, bucket_name):
        """Create new bucket, or return existing one by name."""

        # 'us-east-1' region needs to use client api instead of resource.
        # If bucket is duplicated, still get 200 ok, but no-op.
        if self.session.region_name == 'us-east-1':
            client = self.session.client(
                's3', 'us-east-1', config=Config(signature_version='s3v4')
            )
            client.create_bucket(Bucket=bucket_name)
            s3_bucket = self.s3.Bucket(bucket_name)

        else:
            try:
                region_config = {
                    'LocationConstraint': self.session.region_name
                }
                s3_bucket = self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration=region_config,
                )
            except ClientError as err:
                if err.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                    s3_bucket = self.s3.Bucket(bucket_name)
                else:
                    raise err

        return s3_bucket

    def set_policy(self, bucket):
        """Set bucket policy to open to public."""
        policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": ["arn:aws:s3:::{}/*".format(bucket.name)]
            }]
        }
        policy = json.dumps(policy)
        bucket.Policy().put(Policy=policy)

    def config_website(self, bucket):
        """Configure the bucket setting for static hosting."""

        website_config = {
            'ErrorDocument': {
                'Key': 'error.html'
            },
            'IndexDocument': {
                'Suffix': 'index.html'
            }
        }

        bucket.Website().put(WebsiteConfiguration=website_config)

    def sync(self, pathname, bucket_name):
        """Sync contents of path to buckets."""

        root = Path(pathname).expanduser().resolve()
        bucket = self.s3.Bucket(bucket_name)

        def handle_directory(target):
            for path in target.iterdir():
                if path.is_dir():
                    handle_directory(path)
                elif path.is_file():
                    self.upload_file(
                        bucket,
                        str(path),
                        str(path.relative_to(root))
                    )
        handle_directory(root)

    @staticmethod
    def upload_file(bucket, path, key):
        content_type = mimetypes.guess_type(key)[0] or 'text/plain'
        bucket.upload_file(
            path,
            key,
            ExtraArgs={
                'ContentType': content_type,
            }
        )
