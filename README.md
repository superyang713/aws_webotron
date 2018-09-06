# webotron

It is a script that will sync a local dir to an s3 bucket, and optionally
configure Route 53 and cloundfront as well.

## Features

Webotron currently has the following features:

- List bucket
- List contents of a bucket
- Create and set up bucket
- Sync directory tree to bucket
- Set AWS profile with --profile <profileName>
- Configure route 53 domain

## Workflow

```
webotron.py --profile <profileName> list-buckets
webotron.py --profile <profileName> list-bucket-object <bucketName>
webotron.py --profile <profileName> setup-bucket <bucketName>
webotron.py --profile <profileName> sync <dir> <bucketName>
webotron.py --profile <profileName> setup-domain <bucketName>
```

Note that the bucket name should be the name as the domain name.
