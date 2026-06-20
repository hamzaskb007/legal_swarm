                          +-----------------------------------+
                          |      External Data Sources        |
                          |-----------------------------------|
                          | Government Websites               |
                          | Regulatory APIs                   |
                          | Legal Publications                |
                          +----------------+------------------+
                                           |
                                           |
                                           v
        ---------------------------------------------------------------
                             Legal Swarm Core
        ---------------------------------------------------------------

        +-----------------------------------------------------------+
        |                 Source Governance Layer                   |
        | add_citation()                                            |
        | deduplicate()                                             |
        | authority classification                                  |
        +----------------------+------------------------------------+
                               |
                               |
                               v
        +-----------------------------------------------------------+
        |                    Schema Layer                           |
        | RegulatoryEntry                                            |
        | CitationRecord                                             |
        | VersionRecord                                              |
        | ConfidenceScore                                            |
        | ValidationReport                                           |
        +----------------------+------------------------------------+
                               |
             +-----------------+----------------------+
             |                 |                      |
             |                 |                      |
             v                 v                      v

+--------------------+  +--------------------+  +---------------------+
| Validation Module  |  | Confidence Module  |  | Contradiction Module|
+---------+----------+  +---------+----------+  +----------+----------+
          |                       |                        |
          +-----------+-----------+-----------+------------+
                      |                       |
                      v                       v
             +----------------------------------------+
             |          Audit Logger                  |
             | Immutable JSONL Audit Trail            |
             +----------------+-----------------------+
                              |
                              |
                              v
               +-------------------------------+
               | Versioning Module             |
               | Delta Tracker                |
               | Version History              |
               +-------------------------------+
                              |
                              |
                              v
               +-------------------------------+
               | Persistent Storage            |
               | Regulatory Entries            |
               | Audit Logs                    |
               | Version History               |
               +-------------------------------+

                              |
                              |
                              v

               +-------------------------------+
               | Future AI Agent Layer         |
               | (Multi-Agent Orchestration)   |
               +-------------------------------+