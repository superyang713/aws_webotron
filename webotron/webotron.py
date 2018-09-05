#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Webotron: Deploy websites with AWS.

Webotron automates the process of deploying static websites to AWS.
- configure AWS S3 buckets
    - Create them
    - Set them up for static website hosting
    - Deploy local files to them
- Configure DNS with AWS Route 53
- Configure a Content Delivery Network and SSL with AWS
"""

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
import click
import json

from pathlib import Path
import mimetypes


session = boto3.Session(profile_name='pythonAutomation-other')
s3 = session.resource('s3')


@click.group()
def cli():
    """Webotron deploys websites to AWS."""
    pass


@cli.command('list-buckets')
def list_buckets():
    """List all s3 buckets."""
    for bucket in s3.buckets.all():
        print(bucket)


@cli.command('list-bucket-object')
@click.argument('bucket')
def list_bucket_objects(bucket):
    """List objects in an s3 bucket."""
    for obj in s3.Bucket(bucket).objects.all():
        print(obj)


@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    """Create and configure a bucket in the same region as the profile."""

    # 'us-east-1' region needs to use client api instead of resource.
    # If bucket is duplicated, still get 200 ok, but no-op.
    if session.region_name == 'us-east-1':
        client = session.client(
            's3', 'us-east-1', config=Config(signature_version='s3v4')
        )
        client.create_bucket(Bucket=bucket)
        s3_bucket = s3.Bucket(bucket)

    else:
        try:
            region_config = {'LocationConstraint': session.region_name}
            s3_bucket = s3.create_bucket(
                Bucket=bucket,
                CreateBucketConfiguration=region_config,
            )
        except ClientError as error:
            if error.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                s3_bucket = s3.Bucket(bucket)
            else:
                raise error

    policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": ["arn:aws:s3:::{}/*".format(s3_bucket.name)]
        }]
    }

    website_config = {
        'ErrorDocument': {
            'Key': 'error.html'
        },
        'IndexDocument': {
            'Suffix': 'index.html'
        }
    }

    policy = json.dumps(policy)
    s3_bucket.Policy().put(Policy=policy)
    s3_bucket.Website().put(WebsiteConfiguration=website_config)

    return


@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    """Sync contents of PATHNAME to BUCKET."""

    s3_bucket = s3.Bucket(bucket)
    root = Path(pathname).expanduser().resolve()

    def handle_directory(target):
        for path in target.iterdir():
            if path.is_dir():
                handle_directory(path)
            elif path.is_file():
                upload_file(s3_bucket, str(path), str(path.relative_to(root)))
    handle_directory(root)


def upload_file(s3_bucket, path, key):
    content_type = mimetypes.guess_type(key)[0] or 'text/plain'
    s3_bucket.upload_file(
        path,
        key,
        ExtraArgs={
            'ContentType': content_type,
        }
    )


if __name__ == '__main__':
    cli()
