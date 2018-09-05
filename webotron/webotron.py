import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import click

from pathlib import Path
import mimetypes


session = boto3.Session(profile_name='pythonAutomation-other')
s3 = session.resource('s3')


@click.group()
def cli():
    """Webotron deploys websites to AWS"""
    pass


@cli.command('list-buckets')
def list_buckets():
    """List all s3 buckets"""
    for bucket in s3.buckets.all():
        print(bucket)


@cli.command('list-bucket-object')
@click.argument('bucket')
def list_bucket_objects(bucket):
    """List objects in an s3 bucket"""
    for obj in s3.Bucket(bucket).objects.all():
        print(obj)


@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    """Create and configure a bucket in the same region as the profile"""

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
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                s3_bucket = s3.Bucket(bucket)
            else:
                raise e

    policy = """
    {
    "Version":"2012-10-17",
    "Statement":[{
        "Sid":"PublicReadGetObject",
        "Effect":"Allow",
        "Principal": "*",
        "Action":["s3:GetObject"],
        "Resource":["arn:aws:s3:::%s/*"]
        }]
    }
    """ % s3_bucket.name  # Not using format due to keyerror.
    policy = policy.strip()
    pol = s3_bucket.Policy()
    pol.put(Policy=policy)

    website = s3_bucket.Website()
    website.put(
        WebsiteConfiguration={
            'ErrorDocument': {
                'Key': 'error.html'
            },
            'IndexDocument': {
                'Suffix': 'index.html'
            }
        }
    )

    return


@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    """Sync contents of PATHNAME to BUCKET"""

    s3_bucket = s3.Bucket(bucket)
    root = Path(pathname).expanduser().resolve()

    def handle_directory(target):
        for p in target.iterdir():
            if p.is_dir():
                handle_directory(p)
            elif p.is_file():
                upload_file(s3_bucket, str(p), str(p.relative_to(root)))
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
