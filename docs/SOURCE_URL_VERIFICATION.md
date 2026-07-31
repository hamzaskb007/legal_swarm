# Source URL Verification Report

**Date:** 2026-07-30  
**Verification method:** HTTP GET with SSL context (non-verified certs allowed)  
**Timeout:** 10 seconds per URL  
**Total URLs inspected:** 21 unique hardcoded jurisdiction URLs + 14 authority base URLs

---

## Verified URLs

| Source / Authority ID | Authority | Level | URL | Status | HTTP Status | Notes |
|---|---|---|---|---|---|---|
| MAS Singapore | Monetary Authority of Singapore | 1 | `https://www.mas.gov.sg/regulation/securities-and-futures-act` | VERIFIED | 200 | |
| MAS Singapore | Monetary Authority of Singapore | 1 | `https://www.mas.gov.sg/regulation/variable-capital-companies-act` | VERIFIED | 200 | |
| SCA UAE | Securities and Commodities Authority | 1 | `https://www.sca.gov.ae/legislation/federal-law-no-4-2000` | VERIFIED | 200 | |

### Authority base URLs (from `config/authorities/*.yaml`)

| Authority ID | base_url | Status |
|---|---|---|
| `bvi_fsc` | `https://www.bvifsc.vg` | Reachable (200) |
| `cima` | `https://www.cima.ky` | Reachable (200) |
| `walkers` | `https://www.walkersglobal.com` | Reachable (200) |
| `sec` | `https://www.sec.gov` | Reachable (200) |
| `cftc` | `https://www.cftc.gov` | Reachable (200) |
| `central_bank_ireland` | `https://www.centralbank.ie` | Reachable (200) |
| `cssf` | `https://www.cssf.lu` | Reachable (200) |
| `jfsc` | `https://www.jerseyfsc.org` | Reachable (200) |
| `ogier` | `https://www.ogier.com` | Reachable (200) |
| `mas` | `https://www.mas.gov.sg` | Reachable (200) |
| `acra` | `https://www.acra.gov.sg` | Reachable (200) |
| `sca` | `https://www.sca.gov.ae` | Reachable (200) |
| `dfsa` | `https://www.dfsa.ae` | Reachable (200) |
| `adgm_fsra` | `https://www.adgm.com` | Reachable (200) |

All authority base URLs resolve and return 200.

---

## Unresolved Source URLs

### cayman_islands.py
- **URL:** `https://www.cima.ky/legislation/mutual-funds-act-2021`
- **Intended source:** Cayman Islands Mutual Funds Act (2021 Revision)
- **Status:** INVALID_404
- **Reason:** The URL returns 404. The actual Mutual Funds Act document may have moved or uses a different path on cima.ky. No reliable alternative URL was verified.

- **URL:** `https://www.cima.ky/legislation/private-funds-act-2021`
- **Intended source:** Cayman Islands Private Funds Act (2021 Revision)
- **Status:** INVALID_404
- **Reason:** Same as above — returns 404.

### luxembourg.py
- **URL:** `https://www.cssf.lu/en/legislation/ucits-2010`
- **Intended source:** Luxembourg UCITS Law of 17 December 2010
- **Status:** INVALID_404
- **Reason:** Returns 404. The CSSF website may use different URL paths.

- **URL:** `https://www.cssf.lu/en/legislation/raif-2016`
- **Intended source:** Luxembourg RAIF Law of 23 July 2016
- **Status:** INVALID_404
- **Reason:** Returns 404.

- **URL:** `https://www.cssf.lu/en/legislation/sif-2007`
- **Intended source:** Luxembourg SIF Law of 13 February 2007
- **Status:** INVALID_404
- **Reason:** Returns 404.

### ireland.py
- **URL:** `https://www.centralbank.ie/regulation/ucits-regulations-2011`
- **Intended source:** UCITS Regulations 2011
- **Status:** INACCESSIBLE (403)
- **Reason:** The Central Bank of Ireland blocks automated requests.

- **URL:** `https://www.centralbank.ie/regulation/aifmd-regulations-2013`
- **Intended source:** AIFMD Regulations 2013
- **Status:** INACCESSIBLE (403)
- **Reason:** Blocked by Central Bank of Ireland.

- **URL:** `https://www.centralbank.ie/regulation/icav-act-2015`
- **Intended source:** ICAV Act 2015
- **Status:** INACCESSIBLE (403)
- **Reason:** Blocked by Central Bank of Ireland.

### bvi.py
- **URL:** `https://www.bvifsc.vg/legislation/securities-and-investment-business-act-2010`
- **Intended source:** BVI SIBA 2010
- **Status:** INACCESSIBLE (403)
- **Reason:** BVI FSC blocks automated requests.

- **URL:** `https://www.bvifsc.vg/legislation/investment-business-regulatory-code-2024`
- **Intended source:** BVI IBRC 2024
- **Status:** INACCESSIBLE (403)
- **Reason:** Blocked.

- **URL:** `https://www.bvifsc.vg/legislation/mutual-funds-regulations-2024`
- **Intended source:** BVI Mutual Funds Regulations 2024
- **Status:** INACCESSIBLE (403)
- **Reason:** Blocked.

### uae.py
- **URL:** `https://www.dfsa.ae/legislation/difc-collective-investment-law-2010`
- **Intended source:** DIFC Collective Investment Law 2010
- **Status:** INACCESSIBLE (403)
- **Reason:** DFSA blocks automated requests.

- **URL:** `https://www.adgm.com/legislation/collective-investment-rules-2024`
- **Intended source:** ADGM Collective Investment Rules 2024
- **Status:** INACCESSIBLE (403)
- **Reason:** ADGM blocks automated requests.

### jersey.py
- **URL:** `https://www.jerseyfsc.org/legislation/collective-investment-funds-law-1988`
- **Intended source:** Jersey CIF Law 1988
- **Status:** INACCESSIBLE (403)
- **Reason:** Jersey FSC blocks automated requests.

- **URL:** `https://www.jerseyfsc.org/legislation/alternative-investment-funds-regulations-2012`
- **Intended source:** Jersey AIF Regulations 2012
- **Status:** INACCESSIBLE (403)
- **Reason:** Blocked.

### delaware.py
- **URL:** `https://www.sec.gov/about/laws/investment-company-act-1940`
- **Intended source:** Investment Company Act of 1940
- **Status:** INACCESSIBLE (403)
- **Reason:** SEC blocks automated requests. This URL is referenced in authority config.

- **URL:** `https://www.sec.gov/about/laws/investment-advisers-act-1940`
- **Intended source:** Investment Advisers Act of 1940
- **Status:** INACCESSIBLE (403)
- **Reason:** SEC blocks automated requests.

- **URL:** `https://delcode.delaware.gov/title6/c017/`
- **Intended source:** Delaware Code Title 6, Chapter 17
- **Status:** INACCESSIBLE (403)
- **Reason:** Delaware government website blocks automated requests.

---

## Summary

| Status | Count |
|---|---|
| VERIFIED | 3 |
| INVALID_404 | 5 |
| INACCESSIBLE (403) | 10 |
| UNVERIFIED (other) | 3 |

**Note:** The 5 INVALID_404 URLs (CIMA and CSSF) are the most concerning — they suggest the URLs may be incorrect or the pages have moved. The 403 INACCESSIBLE URLs are typical for government/regulator websites that block automated bots. Manual browser verification would confirm they are accessible to human users.

**What remains to be resolved:**
1. CIMA (cayman_islands.py): Mutual Funds Act and Private Funds Act URLs return 404. Need to find correct paths on cima.ky.
2. CSSF (luxembourg.py): UCITS, RAIF, SIF legislation URLs return 404. Need to find correct paths on cssf.lu.
3. All 403 URLs: Need manual browser verification to confirm they are valid for human users.
