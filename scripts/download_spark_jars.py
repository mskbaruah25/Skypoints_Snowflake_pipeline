"""Download pinned Maven artifacts and verify Maven-published integrity checksums."""

import argparse
import hashlib
import re
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

MAVEN_BASE = "https://repo.maven.apache.org/maven2"


def published_checksum(url: str) -> tuple[str, str]:
    for algorithm, length in [("sha512", 128), ("sha256", 64), ("sha1", 40)]:
        try:
            with urlopen(f"{url}.{algorithm}", timeout=60) as response:
                digest = response.read(4096).decode("ascii").strip().split()[0].lower()
        except HTTPError as exc:
            if exc.code == 404:
                continue
            raise
        if not re.fullmatch(rf"[0-9a-f]{{{length}}}", digest):
            raise ValueError(f"Malformed {algorithm} checksum published for {url}.")
        return algorithm, digest
    raise RuntimeError(f"No published checksum found for {url}.")


def file_digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_artifact(group: str, artifact: str, version: str, output: Path) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", version):
        raise ValueError("Artifact versions must not contain paths or URL syntax.")
    filename = f"{artifact}-{version}.jar"
    url = f"{MAVEN_BASE}/{group.replace('.', '/')}/{artifact}/{version}/{filename}"
    algorithm, expected = published_checksum(url)
    destination = output / filename
    if destination.is_file() and file_digest(destination, algorithm) == expected:
        return destination
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output, suffix=".part", delete=False) as target:
            temporary = Path(target.name)
            with urlopen(url, timeout=120) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    target.write(chunk)
        if file_digest(temporary, algorithm) != expected:
            raise ValueError(f"Checksum mismatch for {filename}.")
        temporary.replace(destination)
        print(f"Verified {filename} ({algorithm}).")
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hadoop-aws", required=True)
    parser.add_argument("--aws-sdk-bundle", required=True)
    parser.add_argument("--snowflake-spark", required=True)
    parser.add_argument("--snowflake-jdbc", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for group, artifact, version in [
        ("org.apache.hadoop", "hadoop-aws", args.hadoop_aws),
        ("com.amazonaws", "aws-java-sdk-bundle", args.aws_sdk_bundle),
        ("net.snowflake", "spark-snowflake_2.12", args.snowflake_spark),
        ("net.snowflake", "snowflake-jdbc", args.snowflake_jdbc),
    ]:
        download_artifact(group, artifact, version, args.output)


if __name__ == "__main__":
    main()
