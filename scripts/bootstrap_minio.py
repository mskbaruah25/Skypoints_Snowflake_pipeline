"""Idempotently create the project bucket and ready-manifest notification filter."""

import os
from urllib.parse import urlsplit

from minio import Minio
from minio.error import S3Error
from minio.notificationconfig import NotificationConfig, QueueConfig


def main() -> None:
    endpoint = urlsplit(os.environ["MINIO_ENDPOINT"])
    if endpoint.scheme not in {"http", "https"} or not endpoint.netloc:
        raise ValueError("MINIO_ENDPOINT must be an HTTP(S) endpoint.")
    client = Minio(
        endpoint.netloc,
        access_key=os.environ["MINIO_ACCESS_KEY"],
        secret_key=os.environ["MINIO_SECRET_KEY"],
        secure=endpoint.scheme == "https",
        region=os.environ.get("MINIO_REGION", "us-east-1"),
    )
    bucket = os.environ.get("MINIO_BUCKET", "skypoints-landing")
    if not client.bucket_exists(bucket):
        try:
            client.make_bucket(bucket)
        except S3Error as exc:
            if exc.code != "BucketAlreadyOwnedByYou":
                raise
    client.set_bucket_notification(
        bucket,
        NotificationConfig(
            queue_config_list=[
                QueueConfig(
                    os.environ["MINIO_WEBHOOK_TARGET_ARN"],
                    ["s3:ObjectCreated:Put", "s3:ObjectCreated:CompleteMultipartUpload"],
                    config_id="skypoints-ready-manifests",
                    prefix_filter_rule=os.environ.get("SKYPOINTS_MANIFEST_PREFIX", "deliveries/"),
                    suffix_filter_rule=os.environ.get("SKYPOINTS_MANIFEST_SUFFIX", "/ready.json"),
                )
            ]
        ),
    )
    print(f"Configured ready-manifest notifications for {bucket}.")


if __name__ == "__main__":
    main()
