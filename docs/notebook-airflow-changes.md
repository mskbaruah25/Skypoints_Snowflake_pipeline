# Approved notebook changes for Airflow

These changes were explicitly approved and have been applied. All other cell sources, saved outputs, and notebook metadata were preserved.

Each notebook gets one new cell immediately after its imports, tagged `parameters`:

```python
# Airflow supplies this date. For a manual notebook run, None uses today.
partition_date = None
```

Airflow passes an eight-character `partition_date` string through Papermill. The configuration cell uses that date; a manual notebook run defaults to today in Asia/Kolkata.

The existing landing bucket root remains the file source. The selected date labels that delivery in RAW and selects the same partition in STAGING and GOLD. No date folders are introduced.

The diffs below refer to the **current cell numbers, before insertion of the new cell**. They cover imports, runtime configuration, credential loading, and the configured bucket name. Parsing, fingerprinting, validation, and Snowflake publication cells retain their existing source.

## RAW notebook

### Original cell 1

```diff
--- raw.ipynb / current cell 1
+++ raw.ipynb / proposed cell 1
@@ -3,6 +3,9 @@
 import os
 import sys
 from uuid import uuid4
+from datetime import datetime
+from pathlib import Path
+from zoneinfo import ZoneInfo

 import snowflake.connector
 from cryptography.hazmat.primitives import serialization
```

### Original cell 2

```diff
--- raw.ipynb / current cell 2
+++ raw.ipynb / proposed cell 2
@@ -1,35 +1,61 @@
-# Processing date (DDMMYYYY). Keep the same date when retrying this batch.
-partition_date = "23112026"
+# Use the date supplied by Airflow, or today's date for a manual notebook run.
+processing_timezone = "Asia/Kolkata"
+if partition_date is None:
+    partition_date = datetime.now(
+        ZoneInfo(processing_timezone)
+    ).strftime("%d%m%Y")
+
+partition_date = datetime.strptime(partition_date, "%d%m%Y").strftime("%d%m%Y")

 os.environ["PYSPARK_PYTHON"] = sys.executable
-os.environ["JAVA_HOME"] = (
-    "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
+os.environ.setdefault(
+    "JAVA_HOME",
+    "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
 )
-os.environ["PYSPARK_SUBMIT_ARGS"] = "--driver-memory 512m pyspark-shell"
+driver_memory = os.environ.get("SKYPOINTS_SPARK_DRIVER_MEMORY", "512m")
+os.environ["PYSPARK_SUBMIT_ARGS"] = f"--driver-memory {driver_memory} pyspark-shell"
+
+# Docker uses the connector JARs downloaded when its image was built.
+# Local notebook runs retain the existing Maven package configuration.
+spark_jars_dir = os.environ.get("SKYPOINTS_SPARK_JARS")
+spark_jars = (
+    ",".join(str(path) for path in sorted(Path(spark_jars_dir).glob("*.jar")))
+    if spark_jars_dir else ""
+)
+if spark_jars_dir and not spark_jars:
+    raise RuntimeError("No connector JARs were found in SKYPOINTS_SPARK_JARS.")
+
+

 spark = (
     SparkSession.builder
     .appName("SkyPoints")
-    .master("local[1]")
+    .master(os.environ.get("SKYPOINTS_SPARK_MASTER", "local[1]"))
     .config("spark.sql.shuffle.partitions", "2")

     # Load the S3 connector and Snowflake Spark/JDBC connectors.
+    .config("spark.jars", spark_jars)
     .config(
         "spark.jars.packages",
-        "org.apache.hadoop:hadoop-aws:3.3.4,"
-        "net.snowflake:spark-snowflake_2.12:3.2.0-spark_3.5,"
-        "net.snowflake:snowflake-jdbc:4.0.2",
+        "" if spark_jars else (
+            "org.apache.hadoop:hadoop-aws:3.3.4,"
+            "net.snowflake:spark-snowflake_2.12:3.2.0-spark_3.5,"
+            "net.snowflake:snowflake-jdbc:4.0.2"
+        ),
     )

     # Locate MinIO.
-    .config("spark.hadoop.fs.s3a.endpoint", "http://localhost:19000")
+    .config(
+        "spark.hadoop.fs.s3a.endpoint",
+        os.environ.get("MINIO_ENDPOINT", "http://localhost:19000"),
+    )
     .config("spark.hadoop.fs.s3a.endpoint.region", "us-east-1")
     .config("spark.hadoop.fs.s3a.path.style.access", "true")
     .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")

     # Authenticate to MinIO.
-    .config("spark.hadoop.fs.s3a.access.key", "admin")
-    .config("spark.hadoop.fs.s3a.secret.key", "admin123")
+    .config("spark.hadoop.fs.s3a.access.key", os.environ.get("MINIO_ACCESS_KEY", "admin"))
+    .config("spark.hadoop.fs.s3a.secret.key", os.environ.get("MINIO_SECRET_KEY", "admin123"))
     .config(
         "spark.hadoop.fs.s3a.aws.credentials.provider",
         "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
```

### Original cell 3

```diff
--- raw.ipynb / current cell 3
+++ raw.ipynb / proposed cell 3
@@ -1,15 +1,24 @@
-# 1. Read the saved Snowflake credentials.
-sf = dotenv_values(
-    "/Users/mskbaruah/code/Incubyte Take home assignment/"
-    "skypoints-pipeline/.env.local",
-    interpolate=False,
+# Read local credentials for manual runs, or the environment supplied by Docker.
+project_root = Path(
+    os.environ.get(
+        "SKYPOINTS_PROJECT_ROOT",
+        '/Users/mskbaruah/code/Incubyte Take home assignment/skypoints-pipeline',
+    )
 )
+
+sf = {
+    **dotenv_values(project_root / ".env.local", interpolate=False),
+    **os.environ,
+}

 # 2. Prepare the encrypted private key for the Spark connector.
 passphrase = sf.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")

 private_key = serialization.load_pem_private_key(
-    open(sf["SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE"], "rb").read(),
+    Path(
+        sf.get("SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE")
+        or sf["SNOWFLAKE_PRIVATE_KEY_FILE"]
+    ).expanduser().read_bytes(),
     password=passphrase.encode() if passphrase else None,
 )

```

### Original cell 6

```diff
--- raw.ipynb / current cell 6
+++ raw.ipynb / proposed cell 6
@@ -1,6 +1,7 @@


-landing_path = "s3a://skypoints-landing/"
+landing_bucket = os.environ.get("MINIO_BUCKET", "skypoints-landing")
+landing_path = f"s3a://{landing_bucket}/"

 # Read every matching member file into one DataFrame.
 members_raw = (
```

## STAGING notebook

### Original cell 2

```diff
--- staging.ipynb / current cell 2
+++ staging.ipynb / proposed cell 2
@@ -1,41 +1,70 @@
-# Capture the processing date once for both feeds.
+# Use the date supplied by Airflow, or today's date for a manual notebook run.
 processing_timezone = "Asia/Kolkata"
-partition_date = datetime.now(
-    ZoneInfo(processing_timezone)
-).strftime("%d%m%Y")
+if partition_date is None:
+    partition_date = datetime.now(
+        ZoneInfo(processing_timezone)
+    ).strftime("%d%m%Y")
+
+partition_date = datetime.strptime(partition_date, "%d%m%Y").strftime("%d%m%Y")

 # Configure local Spark.
 os.environ["PYSPARK_PYTHON"] = sys.executable
-os.environ["JAVA_HOME"] = (
-    "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
+os.environ.setdefault(
+    "JAVA_HOME",
+    "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
 )
-os.environ["PYSPARK_SUBMIT_ARGS"] = "--driver-memory 512m pyspark-shell"
+driver_memory = os.environ.get("SKYPOINTS_SPARK_DRIVER_MEMORY", "512m")
+os.environ["PYSPARK_SUBMIT_ARGS"] = f"--driver-memory {driver_memory} pyspark-shell"
+
+# Docker uses the connector JARs downloaded when its image was built.
+# Local notebook runs retain the existing Maven package configuration.
+spark_jars_dir = os.environ.get("SKYPOINTS_SPARK_JARS")
+spark_jars = (
+    ",".join(str(path) for path in sorted(Path(spark_jars_dir).glob("*.jar")))
+    if spark_jars_dir else ""
+)
+if spark_jars_dir and not spark_jars:
+    raise RuntimeError("No connector JARs were found in SKYPOINTS_SPARK_JARS.")
+
+

 spark = (
     SparkSession.builder
     .appName("SkyPointsStaging")
-    .master("local[1]")
+    .master(os.environ.get("SKYPOINTS_SPARK_MASTER", "local[1]"))
     .config("spark.sql.shuffle.partitions", "2")
     .config("spark.sql.session.timeZone", processing_timezone)
+    .config("spark.jars", spark_jars)
     .config(
         "spark.jars.packages",
-        "net.snowflake:spark-snowflake_2.12:3.2.0-spark_3.5,"
-        "net.snowflake:snowflake-jdbc:4.0.2",
+        "" if spark_jars else (
+            "net.snowflake:spark-snowflake_2.12:3.2.0-spark_3.5,"
+            "net.snowflake:snowflake-jdbc:4.0.2"
+        ),
     )
     .getOrCreate()
 )

 # Read the existing credentials.
 project_root = Path(
-    "/Users/mskbaruah/code/Incubyte Take home assignment/skypoints-pipeline"
+    os.environ.get(
+        "SKYPOINTS_PROJECT_ROOT",
+        '/Users/mskbaruah/code/Incubyte Take home assignment/skypoints-pipeline',
+    )
 )
-sf = dotenv_values(project_root / ".env.local", interpolate=False)
+sf = {
+    **dotenv_values(project_root / ".env.local", interpolate=False),
+    **os.environ,
+}

 # Prepare the private key.
 passphrase = sf.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")

 private_key = serialization.load_pem_private_key(
-    Path(sf["SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE"]).read_bytes(),
+    Path(
+        sf.get("SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE")
+        or sf["SNOWFLAKE_PRIVATE_KEY_FILE"]
+    ).expanduser().read_bytes(),
     password=passphrase.encode() if passphrase else None,
 )

```

## GOLD notebook

### Original cell 2

```diff
--- gold.ipynb / current cell 2
+++ gold.ipynb / proposed cell 2
@@ -1,31 +1,46 @@
-# Capture the processing date once.
+# Use the date supplied by Airflow, or today's date for a manual notebook run.
 processing_timezone = "Asia/Kolkata"
+if partition_date is None:
+    partition_date = datetime.now(
+        ZoneInfo(processing_timezone)
+    ).strftime("%d%m%Y")

-partition_date = datetime.now(
-    ZoneInfo(processing_timezone)
-).strftime("%d%m%Y")
-
-# Uncomment this to process a specific date.
-# partition_date = "23112026"
-
+partition_date = datetime.strptime(partition_date, "%d%m%Y").strftime("%d%m%Y")

 # Configure local Spark.
 os.environ["PYSPARK_PYTHON"] = sys.executable
-os.environ["JAVA_HOME"] = (
-    "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
+os.environ.setdefault(
+    "JAVA_HOME",
+    "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home",
 )
-os.environ["PYSPARK_SUBMIT_ARGS"] = "--driver-memory 512m pyspark-shell"
+driver_memory = os.environ.get("SKYPOINTS_SPARK_DRIVER_MEMORY", "512m")
+os.environ["PYSPARK_SUBMIT_ARGS"] = f"--driver-memory {driver_memory} pyspark-shell"
+
+# Docker uses the connector JARs downloaded when its image was built.
+# Local notebook runs retain the existing Maven package configuration.
+spark_jars_dir = os.environ.get("SKYPOINTS_SPARK_JARS")
+spark_jars = (
+    ",".join(str(path) for path in sorted(Path(spark_jars_dir).glob("*.jar")))
+    if spark_jars_dir else ""
+)
+if spark_jars_dir and not spark_jars:
+    raise RuntimeError("No connector JARs were found in SKYPOINTS_SPARK_JARS.")
+
+

 spark = (
     SparkSession.builder
     .appName("SkyPointsGold")
-    .master("local[1]")
+    .master(os.environ.get("SKYPOINTS_SPARK_MASTER", "local[1]"))
     .config("spark.sql.shuffle.partitions", "2")
     .config("spark.sql.session.timeZone", processing_timezone)
+    .config("spark.jars", spark_jars)
     .config(
         "spark.jars.packages",
-        "net.snowflake:spark-snowflake_2.12:3.2.0-spark_3.5,"
-        "net.snowflake:snowflake-jdbc:4.0.2",
+        "" if spark_jars else (
+            "net.snowflake:spark-snowflake_2.12:3.2.0-spark_3.5,"
+            "net.snowflake:snowflake-jdbc:4.0.2"
+        ),
     )
     .getOrCreate()
 )
@@ -33,20 +48,26 @@

 # Read the existing credentials.
 project_root = Path(
-    "/Users/mskbaruah/code/Incubyte Take home assignment/skypoints-pipeline"
+    os.environ.get(
+        "SKYPOINTS_PROJECT_ROOT",
+        '/Users/mskbaruah/code/Incubyte Take home assignment/skypoints-pipeline',
+    )
 )

-sf = dotenv_values(
-    project_root / ".env.local",
-    interpolate=False,
-)
+sf = {
+    **dotenv_values(project_root / ".env.local", interpolate=False),
+    **os.environ,
+}


 # Prepare the private key for authentication.
 passphrase = sf.get("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")

 private_key = serialization.load_pem_private_key(
-    Path(sf["SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE"]).read_bytes(),
+    Path(
+        sf.get("SNOWFLAKE_LOCAL_PRIVATE_KEY_FILE")
+        or sf["SNOWFLAKE_PRIVATE_KEY_FILE"]
+    ).expanduser().read_bytes(),
     password=passphrase.encode() if passphrase else None,
 )

```
