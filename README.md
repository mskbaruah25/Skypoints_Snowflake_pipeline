# SkyPoints Pipeline

Hello there, reviewer. This project implements the SkyPoints pipeline described in [DE_Assessment_file.pdf](https://incubytein-my.sharepoint.com/:b:/g/personal/tanuja_incubyte_co/IQBvHDRVzESATYSafwTDmtJiAcPV70SUV7UR-ife4CGKSes?e=x0zODI).

First things first.

**If you just want to review the end goals, you can directly log in to Snowflake and check the tables and databases. To check the databases, please log in to this Snowflake workspace using the following details:**

**Workspace:** [Open Snowflake](https://app.snowflake.com/vgbuylt/wz85427)

**Username:** `SKYPOINTS_EVALUATOR`

**Password:** `Incubyteskypoints1`

This login provides read-only access to the existing pipeline results.

## 1. Review the results in Snowflake

1. Sign in using the details above.

2. Select the role SKYPOINTS_REVIEWER_ROLE if not already selected by default.

3. Open Catalogue → Explorer and expand the SKYPOINTS database. You will find these three schemas. [Snowflake navigation guide](https://docs.snowflake.com/en/user-guide/ui-snowsight-data).

| Schema | What to inspect |
| --- | --- |
| RAW | Original member records, redemption payloads, and ingestion-control tables. |
| STAGING | Parsed, validated member and redemption tables. |
| GOLD | Country-specific member tables, including India, Australia, and the United States. |

4. To run SQL, open Workspaces, and create a SQL File, select SKYPOINTS_REVIEWER_ROLE(if not already selected by default) and warehouse SKYPOINTS_WH. [SQL editor guide](https://docs.snowflake.com/en/user-guide/ui-snowsight/workspaces). You ll probably be able to run queries directly. I just gave the information about the role and warehouse, just in case.

5. You can write any read-only queries. For example, these two queries:

```sql
-- Review cleaned member records and derived fields.
SELECT
    MEMBER_ID,
    MEMBER_NAME,
    COUNTRY,
    AGE,
    STALE_MEMBER,
    PARTITION_DATE
FROM SKYPOINTS.STAGING.MEMBERS
LIMIT 10;
```

```sql
-- Review the country-specific output layout.
SELECT *
FROM SKYPOINTS.GOLD.TABLE_INDIA
LIMIT 10;
```

You can also inspect TABLE_AUSTRALIA and TABLE_UNITED_STATES in the GOLD schema.

Now, coming to the pipeline, here is how you can use this repository to set up the pipeline that populates the Snowflake tables.

## 2. Run one complete pipeline locally using Docker

One pipeline run takes **both files from one sample folder**, processes them through **RAW → STAGING → GOLD**, and saves the results in Snowflake.

**Prerequisites:** Git, Docker with Docker Compose, and a Snowflake pipeline user with write permissions and key-pair authentication. The evaluator login above provides read-only access.

### 1. Clone the repository

```bash
git clone https://github.com/mskbaruah25/Skypoints_Snowflake_pipeline.git skypoints-pipeline
cd skypoints-pipeline
```

### 2. Configure the Snowflake connection

For a new Snowflake deployment, run the files inside [snowflake setup queries](snowflake%20setup%20queries) as an administrator, in this order:

1. [raw.sql](snowflake%20setup%20queries/raw.sql)
2. [staging.sql](snowflake%20setup%20queries/staging.sql)
3. [gold.sql](snowflake%20setup%20queries/gold.sql)

Your pipeline user must have `SKYPOINTS_PIPELINE_ROLE` and a registered RSA public key. See [Snowflake’s key-pair setup instructions](https://docs.snowflake.com/en/user-guide/key-pair-auth).

Place its private key at `secrets/snowflake_key.p8`. Keep the included `.env` settings for the local services, then create `.env.local` in the repository root and fill in your connection details:

```dotenv
SNOWFLAKE_ACCOUNT=YOUR_ORGANIZATION-YOUR_ACCOUNT
SNOWFLAKE_USER=YOUR_PIPELINE_USER
SNOWFLAKE_ROLE=SKYPOINTS_PIPELINE_ROLE
SNOWFLAKE_WAREHOUSE=SKYPOINTS_WH
SNOWFLAKE_DATABASE=SKYPOINTS
SNOWFLAKE_SECRETS_DIR=./secrets
SNOWFLAKE_PRIVATE_KEY_FILE=/run/secrets/snowflake_key.p8
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE='YOUR_KEY_PASSPHRASE'
```

Private Snowflake pipeline credentials and keys are not included in the repository. For an existing deployment, use the configured pipeline user and existing warehouse tables.

### 3. Start the services

Start Docker Desktop, then run:

```bash
docker compose --env-file .env --env-file .env.local --profile airflow up -d --build
```

Wait for the services to become healthy. The `airflow-init` and `minio-init` containers finishing with exit code `0` is expected.

### 4. Select one sample pair

The [sample files](Sample%20files/pairs) are included in the repository:

```text
Sample files/
└── pairs/
    ├── drop_0001/
    │   ├── members_0001.txt
    │   └── redemptions_0001.json
    ├── drop_0002/
    │   ├── members_0002.txt
    │   └── redemptions_0002.json
    └── ... up to drop_0010
```

Each `drop` folder contains one complete delivery: a member flat file and a redemption JSON file matching the assignment’s source formats.

For a fresh deployment, use the two files inside **`Sample files/pairs/drop_0001/`**. For an already populated Snowflake deployment, choose a pair that has not previously been ingested.

### 5. Upload both files to MinIO

1. Open [MinIO](http://localhost:19001).
2. Log in with **username `admin`** and **password `admin123`**.
3. Open the **`skypoints-landing`** bucket.
4. Upload both files from your chosen `drop` folder directly into the bucket’s root. For `drop_0001`, these are **`members_0001.txt`** and **`redemptions_0001.json`**.

For the `drop_0001` example, the landing bucket should contain the two files themselves:

```text
skypoints-landing/
├── members_0001.txt
└── redemptions_0001.json
```

Keep only the intended delivery at the bucket root. Move previously processed pairs to a separate archive bucket before uploading another pair.

### 6. Trigger one run in Airflow

1. Open [Airflow](http://localhost:18080).
2. Log in with **username `admin`** and **password `admin`**.
3. Open the DAG **`skypoints_ingestion`**.
4. Click **Trigger**.
5. Enter a `partition_date` in **DDMMYYYY** format—for example, **`24112026`**.
6. Confirm the trigger once.

A single trigger executes all three notebooks in sequence using the same processing date. Uploading files alone does not trigger the pipeline.

### 7. Check the execution and results

Airflow runs:

```text
load_raw → load_staging → load_gold
```

Wait until all three tasks turn green. If a task fails, open that task’s **Logs** to inspect the error.

In the Snowflake account configured in `.env.local`, check the RAW, STAGING, and GOLD tables. For example:

```sql
SELECT *
FROM SKYPOINTS.STAGING.MEMBERS
WHERE PARTITION_DATE = '24112026'
LIMIT 10;
```

The processing date labels the delivery. **It does not filter MinIO files by their upload date:** RAW reads every matching file currently at the landing bucket’s root.

An identical, already registered batch is skipped by RAW. When retrying the same delivery, use its original processing date. For a new delivery, use another unprocessed sample pair.

### 8. Stop the services when finished

```bash
docker compose --env-file .env --env-file .env.local --profile airflow stop
```

Stopping the services retains MinIO files, Airflow metadata, and logs in Docker volumes.

## 3. Project architecture

The processing services run locally in Docker. Business data is stored in Snowflake throughout the RAW, STAGING, and GOLD stages.

| Component | Purpose |
| --- | --- |
| MinIO | Provides the S3-compatible landing bucket for source files. |
| Airflow | Accepts a processing date and runs the three notebooks in sequence. |
| PySpark | Reads source files and performs parsing, validation, cleaning, and transformations. |
| Snowflake | Stores RAW records, STAGING data, and GOLD country tables. |
| PostgreSQL | Stores Airflow’s orchestration metadata. |

The three processing stages are:

1. RAW: Reads member TXT files and redemption JSON files from MinIO. Preserves source content and ingestion metadata. Uses buffers and a batch fingerprint to publish records and register a successful batch together.

2. STAGING: Reads the selected RAW partition, parses the records, validates fields, cleans member IDs, checks duplicates and conflicts, and calculates age and member staleness. Rerunning a partition refreshes that partition’s staging rows.

3. GOLD: Reads the selected STAGING partition and publishes members into country-specific tables. India and Australia use their supplied column layouts; other countries use the USA layout. India’s unsupported “Individual or Corporate” field is omitted. Member-location tracking supports country changes and prevents older partitions from replacing newer published records.

Airflow is manually triggered. Uploading files alone does not start processing. MinIO files, Airflow metadata, and execution logs persist in Docker volumes; the business tables remain in Snowflake.
