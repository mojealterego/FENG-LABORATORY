# Security and operational boundaries

This repository is a laboratory reference implementation for a district-heating telemetry concept, **not an operational industrial control system**.

- Default webhook bind address is localhost. Do not expose raw HTTP to public networks; use a hardened TLS reverse proxy, ingress limits and access controls.
- Configure a long, randomly generated `THERMO_IOT_WEBHOOK_TOKEN` outside source control. Rotate it on compromise. Avoid logging headers or device payloads.
- The Things Stack (or another actual LoRaWAN network server) must validate and decrypt LoRaWAN messages before forwarding. The prototype does not implement a LoRaWAN MIC check.
- The SQLite database is a local prototype; protect filesystem access, backups and retention. Session identifiers are not credentials but may still be operationally sensitive.
- Temperature anomaly candidates are statistical suggestions only; **do not use them to actuate heating infrastructure, override existing safety systems or claim certified leak detection**.
- Work at physical district-heating assets requires operator approval, lockout and site-specific safety procedures.
- Do not commit private applicant identities, unpublished patent claims, device keys, personally identifiable information, or real network endpoints.
- Report security problems through the GitHub repository owner's established private communication channel rather than publishing exploitable details in issues.

No security certification, penetration test, IEC 62443 conformity or production readiness is claimed.
