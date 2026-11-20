# Source contract: decisions pending

The assessment is the source of requirements. Preserve its flat-file `H`/`D`
record layout and nested redemption envelope; do not treat the supplied country
CSVs as the specified upstream feed without an explicit conversion step.

Resolve and record these decisions before implementing the parser and SQL:

1. Member identity: the table marks Member Name as a key while JSON references
   Member ID. The proposed durable identity is globally stable Member ID.
2. Latest record: define a producer update version or an ordered source snapshot
   version. Ingestion arrival time and last flight date cannot establish freshness.
3. DOB format: the sample does not settle day/month order. Preserve the raw string.
4. Post Code: it appears in the specification table but not the sample record.
5. Snapshot versus upsert: proposed behaviour is complete-profile upserts; absence
   from a delivery does not delete a member.
6. Country mapping: define canonical values and handling of missing/unknown values.
7. Redemption identity: define transaction-ID scope and status-update ordering.
8. Calculation date: use an explicit as-of date for age and greater-than-90-day
   staleness. Missing optional dates produce unknown derived values.

The proposed delivery lives under `deliveries/<batch_id>/`. A `ready.json` uploaded
last identifies the exact files, checksums/object versions, immutable source version,
and calculation date. Its detailed schema and JSON file framing are not final yet.

Delivery identity and source versions must be retained through raw, staging, and
publication audit records. A changed payload must not overwrite an immutable batch.
