# -*- coding: utf-8 -*-

"""
Classes for S3 Buckets.
"""

from botocore.client import Config
from botocore.exceptions import ClientError
from boto3.exceptions import S3UploadFailedError
from boto3.s3.transfer import TransferConfig

import json
import mimetypes
from pathlib import Path
from hashlib import md5
from functools import reduce

import util


class BucketManager:
    """Manage an S3 Bucket."""

    CHUNK_SIZE = 8388608

    def __init__(self, session):
        self.session = session
        self.s3 = self.session.resource('s3')
        self.manifest = {}
        self.transfer_config = TransferConfig(
            multipart_chunksize=self.CHUNK_SIZE,
            multipart_threshold=self.CHUNK_SIZE,
        )

    def get_bucket_url(self, bucket_name):
        """Get the website URL for this bucket."""
        return "http://{}.{}".format(
            bucket_name,
            util.get_endpoint(self.session.region_name).host
        )

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
            try:
                client.create_bucket(Bucket=bucket_name)
                s3_bucket = self.s3.Bucket(bucket_name)
            except ClientError:
                print('Abort: The bucket name has been occupised.')
                exit()

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
        self.load_manifest(bucket_name)

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

    def load_manifest(self, bucket_name):
        """Load manifest for caching purposes."""
        paginator = self.s3.meta.client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket_name):
            for obj in page.get('Contents', []):
                self.manifest[obj['Key']] = obj['ETag']

    @staticmethod
    def hash_data(data):
        """Generate md5 hash for data."""
        hash = md5()
        hash.update(data)
        return hash

    def gen_etag(self, path):
        """Generate etag for file."""
        hashes = []
        with open(path, 'rb') as f:
            while True:
                data = f.read(self.CHUNK_SIZE)

                if not data:
                    break

            hashes.append(self.hash_data(data))

            if not hashes:
                return
            elif len(hashes) == 1:
                return '"{}"'.format(hashes[0].hexdigest())
            else:
                hash = self.hash_data(
                    reduce(lambda x, y: x + y, (h.digest() for h in hashes))
                )
                return '"{}-{}"'.format(hash.hexdigest(), len(hashes))

    def upload_file(self, bucket, path, key):
        """Upload path to s3_bucket at key"""
        content_type = mimetypes.guess_type(key)[0] or 'text/plain'
        etag = self.gen_etag(path)
        if self.manifest.get(key, '') == etag:
            return
        try:
            bucket.upload_file(
                path,
                key,
                ExtraArgs={
                    'ContentType': content_type,
                },
                Config=self.transfer_config
            )
        except S3UploadFailedError:
            print('Are you sure this is your bucket?')
            exit()
