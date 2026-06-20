                   Raw Regulatory Data
                            |
                            v
                +-----------------------+
                | Source Governance     |
                | Deduplicate Sources   |
                | Categorize Citations  |
                +-----------+-----------+
                            |
                            | SourceGovernanceRecord
                            v
                +-----------------------+
                | RegulatoryEntry       |
                | (Pydantic Schema)     |
                +-----------+-----------+
                            |
        +-------------------+--------------------+
        |                   |                    |
        |                   |                    |
        v                   v                    v
+----------------+   +----------------+   +------------------+
| Validation     |   | Confidence     |   | Contradiction    |
| Engine         |   | Scorer         |   | Detector         |
+-------+--------+   +--------+-------+   +--------+---------+
        |                     |                     |
        | ValidationReport    | ConfidenceScore     |
        |                     | ContradictionRecord |
        +----------+----------+----------+----------+
                   |                     |
                   +----------+----------+
                              |
                              v
                    +--------------------+
                    | Audit Logger       |
                    | Immutable JSON Log |
                    +---------+----------+
                              |
                              |
                              v
                  +------------------------+
                  | Stored RegulatoryEntry |
                  | Version Repository     |
                  +-----------+------------+
                              |
                              |
                 Updated Entry |
                              |
                              v
                    +------------------+
                    | Delta Tracker    |
                    | VersionRecord    |
                    +------------------+