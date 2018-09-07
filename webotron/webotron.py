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
from botocore.exceptions import NoCredentialsError, ProfileNotFound
import click

from webotron.bucket import BucketManager
from webotron.domain import DomainManager
from webotron.certificate import CertificateManager
from webotron.cdn import DistributionManager

from pprint import pprint

session = None
bucket_manager = None
domain_manager = None
cert_manager = None
dist_manager = None


@click.group()
@click.option('--profile', default=None, help="Use a given AWS profile")
def cli(profile):
    """Webotron deploys websites to AWS."""
    global session, bucket_manager, domain_manager, cert_manager, dist_manager
    session_cfg = {}
    if profile:
        session_cfg['profile_name'] = profile
        try:
            session = boto3.Session(**session_cfg)
            bucket_manager = BucketManager(session)
            domain_manager = DomainManager(session)
            cert_manager = CertificateManager(session)
            dist_manager = DistributionManager(session)
        except ProfileNotFound as e:
            print(e)
            exit()
    else:
        raise NoCredentialsError(
            "Please input profile name with --profile flag"
        )
        exit()


@cli.command('list-buckets')
def list_buckets():
    """List all s3 buckets."""
    for bucket in bucket_manager.all_buckets():
        print(bucket)


@cli.command('list-bucket-object')
@click.argument('bucket')
def list_bucket_objects(bucket):
    """List objects in an s3 bucket."""
    for obj in bucket_manager.all_objects(bucket):
        print(obj)


@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    """Create and configure a bucket in the same region as the profile."""

    s3_bucket = bucket_manager.create_bucket(bucket)
    bucket_manager.set_policy(s3_bucket)
    bucket_manager.config_website(s3_bucket)


@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    """Sync contents of PATHNAME to BUCKET."""
    bucket_manager.sync(pathname, bucket)
    print(bucket_manager.get_bucket_url(bucket))


@cli.command('setup-domain')
@click.argument('domain')
def setup_domain(domain):
    """Configure DOMAIN to point to BUCKET"""
    zone = domain_manager.find_hosted_zone(domain) \
        or domain_manager.create_hosted_zone(domain)

    a_record = domain_manager.create_s3_domain_record(zone, domain)
    print("Domain configured: http://{}".format(domain))
    print(a_record)


@cli.command('find-cert')
@click.argument('domain')
def find_cert(domain):
    print(cert_manager.find_matching_cert(domain))


@cli.command('setup-cdn')
@click.argument('domain')
def setup_cdn(domain):
    """Set up CloudFront CDN for DOMAIN pointing to BUCKET."""
    dist = dist_manager.find_matching_dist(domain)

    if not dist:
        cert = cert_manager.find_matching_cert(domain)
        if not cert:  # SSL is not optional at this time
            raise("Error: No matching cert found.")
        dist = dist_manager.create_dist(domain, cert)
        print("Waiting for distribution deployment...")
        dist_manager.await_deploy(dist)

    zone = domain_manager.find_hosted_zone(domain) \
        or domain_manager.create_hosted_zone(domain)
    domain_manager.create_cf_domain_record(zone, domain, dist['DomainName'])

    pprint(dist)
    print("Domain configured: https://{}".format(domain))

    return


if __name__ == '__main__':
    cli()
