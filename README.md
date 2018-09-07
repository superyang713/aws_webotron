# webotron

It is a script that will sync a local dir to an s3 bucket, and optionally
configure Route 53 and cloundfront as well.

## Features

Webotron currently has the following features:

- List bucket
- List contents of a bucket
- Create and set up bucket for static web hosting.
- Sync directory tree to bucket
- Set AWS profile with --profile <profileName>
- Configure route 53 domain
-

## Workflow

```
webotron --profile <profileName> list-buckets
webotron --profile <profileName> list-bucket-object <bucketName>
webotron --profile <profileName> setup-bucket <bucketName>
webotron --profile <profileName> sync <dir> <bucketName>
webotron --profile <profileName> setup-cdn <domainName>

```

Note that the bucket name should be the name as the domain name.


Optionally, you can run the following command if you wish not to deploy it
through cloudfront.

```
webotron.py --profile <profileName> setup-domain <bucketName>
webotron.py --profile <profileName> find-cert <bucketName>
```
