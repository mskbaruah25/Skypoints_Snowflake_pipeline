-- Run after raw.sql and staging.sql.
-- Quoted column names preserve the supplied country layouts exactly.
-- Reference: https://docs.snowflake.com/en/sql-reference/sql/create-table

USE ROLE ACCOUNTADMIN;
USE WAREHOUSE SKYPOINTS_WH;

CREATE SCHEMA IF NOT EXISTS SKYPOINTS.GOLD;

-- USA layout, also used for the remaining countries without separate templates.
CREATE TABLE IF NOT EXISTS SKYPOINTS.GOLD.TABLE_UNITED_STATES (
    "ID"              VARCHAR(18) NOT NULL,
    "Name"            VARCHAR(255) NOT NULL,
    "TierCode"        VARCHAR(5),
    "EnrollmentDate"  DATE NOT NULL,
    "FlightDate"      DATE,
    PARTITION_DATE    VARCHAR(8)
);

-- India deliberately omits the unsupported Individual or Corporate column.
CREATE TABLE IF NOT EXISTS SKYPOINTS.GOLD.TABLE_INDIA (
    "ID"              VARCHAR(18) NOT NULL,
    "Name"            VARCHAR(255) NOT NULL,
    "DOB"             DATE,
    "TierCode"        VARCHAR(5),
    "EnrollmentDate"  DATE NOT NULL,
    "Flight Date"     DATE,
    PARTITION_DATE    VARCHAR(8)
);

CREATE TABLE IF NOT EXISTS SKYPOINTS.GOLD.TABLE_AUSTRALIA (
    "Unique ID"           VARCHAR(18) NOT NULL,
    "Member Name"         VARCHAR(255) NOT NULL,
    "Tier Type"           VARCHAR(5),
    "Date of Birth"       DATE,
    "Date of Enrollment"  DATE NOT NULL,
    "Date of Flight"      DATE,
    PARTITION_DATE        VARCHAR(8)
);

-- These empty tables inherit the USA columns, types and constraints.
CREATE TABLE IF NOT EXISTS SKYPOINTS.GOLD.TABLE_BRAZIL
    LIKE SKYPOINTS.GOLD.TABLE_UNITED_STATES;

CREATE TABLE IF NOT EXISTS SKYPOINTS.GOLD.TABLE_PORTUGAL
    LIKE SKYPOINTS.GOLD.TABLE_UNITED_STATES;

CREATE TABLE IF NOT EXISTS SKYPOINTS.GOLD.TABLE_UNITED_KINGDOM
    LIKE SKYPOINTS.GOLD.TABLE_UNITED_STATES;

CREATE TABLE IF NOT EXISTS SKYPOINTS.GOLD.TABLE_UNASSIGNED
    LIKE SKYPOINTS.GOLD.TABLE_UNITED_STATES;

-- Track each member's latest published country and actual processing date.
-- Keep exactly these three columns: the notebook uses MERGE ALL BY NAME.
CREATE TABLE IF NOT EXISTS SKYPOINTS.GOLD.MEMBER_LOCATION (
    MEMBER_ID     VARCHAR(18) NOT NULL,
    TARGET_TABLE  VARCHAR(255) NOT NULL,
    RECORD_DATE   DATE NOT NULL
);

-- gold.ipynb creates its session-local _MEMBERS_WORK table during execution.
GRANT USAGE, CREATE TABLE, CREATE STAGE
    ON SCHEMA SKYPOINTS.GOLD TO ROLE SKYPOINTS_PIPELINE_ROLE;

GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON ALL TABLES IN SCHEMA SKYPOINTS.GOLD TO ROLE SKYPOINTS_PIPELINE_ROLE;
