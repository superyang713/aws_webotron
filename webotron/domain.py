# -*- coding: utf-8 -*-

"""
Classes for Route 52 domains.
"""

import uuid

import webotron.util


class DomainManager:
    """Manage for Route 53 domains."""
    def __init__(self, session):
        self.session = session
        self.route53_client = self.session.client('route53')

    def find_hosted_zone(self, domain_name):
        """Find the existing hosted zone that matches the domain_name"""
        paginator = self.route53_client.get_paginator('list_hosted_zones')
        for page in paginator.paginate():
            for zone in page['HostedZones']:
                if domain_name.endswith(zone['Name'][:-1]):
                    return zone

        return None

    def create_hosted_zone(self, domain_name):
        """Create a hosted zone to match domain_name."""
        zone_name = '.'.join(domain_name.split('.')[-2:]) + '.'
        return self.route53_client.create_hosted_zone(
            Name=zone_name,
            CallerReference=str(uuid.uuid4())
        )

    def create_s3_domain_record(self, zone, domain_name):
        """Create a domain record in domain hosted zone for domain_name."""
        s3_endpooint = webotron.util.get_endpoint(self.session.region_name)
        return self.route53_client.change_resource_record_sets(
            HostedZoneId=zone['Id'],
            ChangeBatch={
                'Comment': 'Created by Webotron',
                'Changes': [{
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': domain_name,
                        'Type': 'A',
                        'AliasTarget': {
                            'HostedZoneId': s3_endpooint.zone,
                            'DNSName': s3_endpooint.host,
                            'EvaluateTargetHealth': False,
                        },
                    }
                }]
            }
        )

    def create_cf_domain_record(self, zone, domain_name, cf_domain):
        """Create a domain record in zone for domain_name."""
        return self.route53_client.change_resource_record_sets(
            HostedZoneId=zone['Id'],
            ChangeBatch={
                'Comment': 'Created by webotron',
                'Changes': [{
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': domain_name,
                        'Type': 'A',
                        'AliasTarget': {
                            'HostedZoneId': 'Z2FDTNDATAQYW2',
                            'DNSName': cf_domain,
                            'EvaluateTargetHealth': False
                        }
                    }
                }]
            }
        )
