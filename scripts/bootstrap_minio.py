"""Create the landing bucket and disable notifications for manual Airflow runs."""

import os
from urllib.parse import urlsplit

from minio import Minio
from minio.error import S3Error
from minio.notificationconfig import NotificationConfig


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
    # Remove the old ready.json notification rule from existing buckets too.
    # This changes notification configuration only; objects are left in place.
    client.set_bucket_notification(bucket, NotificationConfig())
    print(f"Landing bucket {bucket} is ready for manually triggered runs.")


if __name__ == "__main__":
    main()
