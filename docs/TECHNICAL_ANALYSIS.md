# CardDemo Technical Analysis & Modernization Plan

Generated with the Devin Wiki for `surajpinnamaraju-ctrl/aws-mainframe-modernization-carddemo_Devin`
(https://app.devin.ai/wiki/surajpinnamaraju-ctrl/aws-mainframe-modernization-carddemo_Devin) plus a
file-by-file read of the source tree.

## 1. What this repository is

CardDemo is an AWS sample mainframe application that simulates a credit-card
management system. It has two operational layers:

- **Online layer** — CICS pseudo-conversational COBOL programs driving BMS
  (Basic Mapping Support) 3270 screens; session state is carried in the
  `COMMAREA` copybook `COCOM01Y`.
- **Batch layer** — JCL jobs running COBOL batch programs and IBM utilities
  (`IDCAMS`, `IEBGENER`, `IEFBR14`, `SORT`, `DSNTEP4`, `DSNTIAUL`, `FTP`,
  `IKJEFT1B`) against VSAM (KSDS/ESDS/RRDS) and sequential datasets.

Persistence is VSAM KSDS files whose record layouts are defined by COBOL
copybooks. Three optional add-on modules extend the base app with Db2, IMS DB,
and IBM MQ.

## 2. Target stack — choice and reasoning

| Tier | Choice | Reasoning |
|:-----|:-------|:----------|
| Backend | **Python 3.12 + FastAPI + SQLite** | REST endpoints replace pseudo-conversational CICS transactions one-to-one; the `COMMAREA` becomes request/response DTOs. Fixed-length copybook layouts map directly onto Pydantic models, and `COMP`/`COMP-3` packed/zoned decimals map onto `Decimal` (exact money math, no float drift). SQLite seeded at startup from the repo's own ASCII data files reproduces the VSAM KSDS keyed-access model with zero external dependencies — ideal for a single Cloud Run service. `pytest` gives fast unit tests, and PyPI egress is reliable from this environment (Maven Central is rate-limited here, which makes a Java/Spring build the riskier choice). |
| Frontend | **React 18 + TypeScript + Vite + Vitest** | Each BMS map becomes a React screen; React Router replaces `EXEC CICS XCTL`/menu navigation; `axios` replaces `EXEC CICS LINK` calls into the backend. Vitest mirrors pytest for unit coverage. The production build is static assets served by nginx — small, stateless, Cloud Run friendly. |
| Packaging | **Docker** (python:3.12-slim for backend; node:20 build + nginx:alpine for frontend) | Cloud Run runs one container per service; frontend calls the backend's public URL injected at runtime via `config.js`. |
| Deploy | **Google Cloud Run** (two services), **Artifact Registry** for images, **GitHub Actions** for CI | Required by the task. Both services scale to zero — fitting for a demo workload. |

What is deliberately *not* carried over: CICS, BMS, RACF, VSAM/JCL runtime
semantics, MQ/IMS/Db2 middleware. Their *features* are re-implemented in the
new stack (see §6), not the middleware itself.

## 3. Repository inventory — every file mapped to a feature

### 3.1 `app/cbl/` — COBOL programs (30)

Online CICS programs:

| Program | BMS map | Trans | Feature |
|:--------|:--------|:------|:--------|
| `COSGN00C.cbl` | `COSGN00` | CC00/CSGN | Signon — validates userid/password against USRSEC, routes admin vs regular users |
| `COMEN01C.cbl` | `COMEN01` | CM00/CMEN | Main menu — routes options 1–11 to feature programs |
| `COADM01C.cbl` | `COADM01` | CA00/CADM | Admin menu — routes options 1–6 to admin functions |
| `COACTVWC.cbl` | `COACTVW` | CAVW | Account view — reads ACCTFILE + XREFFILE + CUSTFILE, shows balance/limits |
| `COACTUPC.cbl` | `COACTUP` | CAUP | Account update — edits status, limits, dates, address; heavy field validation (phone masks, SSN, signed numerics) |
| `COCRDLIC.cbl` | `COCRDLI` | CCLI | Credit card list — paginated browse (STARTBR/READNEXT) of cards by account |
| `COCRDSLC.cbl` | `COCRDSL` | CCDL | Credit card view/detail — card number, embossed name, expiry, status |
| `COCRDUPC.cbl` | `COCRDUP` | CCUP | Credit card update — name/expiry/status changes, REWRITE to CARDFILE |
| `COTRN00C.cbl` | `COTRN00` | CT00 | Transaction list — paginated browse of TRANSACT by card/account, PF7/PF8 paging |
| `COTRN01C.cbl` | `COTRN01` | CT01 | Transaction view — full detail of one transaction |
| `COTRN02C.cbl` | `COTRN02` | CT02 | Transaction add — validates card, account, type/category, posts new record |
| `CORPT00C.cbl` | `CORPT00` | CR00 | Transaction report by date range — submits batch job `TRANREPT` via internal reader |
| `COBIL00C.cbl` | `COBIL00` | CB00 | Bill payment — confirms and posts a full-balance payment transaction |
| `COUSR00C.cbl` | `COUSR00` | CU00 | Admin: list users (USRSEC), select for update/delete |
| `COUSR01C.cbl` | `COUSR01` | CU01 | Admin: add user |
| `COUSR02C.cbl` | `COUSR02` | CU02 | Admin: update user |
| `COUSR03C.cbl` | `COUSR03` | CU03 | Admin: delete user (protects last admin) |
| `CSUTLDTC.cbl` | — | (called) | Date utility — validates/converts dates; used by COACTUPC, COTRN02C, COBIL00C, CORPT00C |

Batch COBOL programs:

| Program | Driven by JCL | Feature |
|:--------|:--------------|:--------|
| `CBTRN01C.cbl` | (reader) | Reads DALYTRAN + validates against XREF/CARD/ACCT/CUST/TRANSACT |
| `CBTRN02C.cbl` | `POSTTRAN` | **Daily posting engine** — validates each daily transaction (card→xref→account), writes rejects to DALYREJS, updates account balance + transaction-category balance, appends to TRANSACT |
| `CBTRN03C.cbl` | `TRANREPT` | Prints the transaction detail report for a date range (uses `CVTRA07Y` layouts) |
| `CBACT01C.cbl` | `READACCT` | Reads/prints account file |
| `CBACT02C.cbl` | `READCARD` | Reads/prints card file |
| `CBACT03C.cbl` | `READXREF` | Reads/prints card cross-reference file |
| `CBACT04C.cbl` | `INTCALC` | **Interest calculator** — applies disclosure-group interest rate to each account's current balance, posts interest transaction |
| `CBCUS01C.cbl` | `READCUST` | Reads/prints customer file |
| `CBSTM03A.CBL` | `CREASTMT` | **Statement driver** — control-break logic over transactions per account/card, builds text + HTML statement lines (`ST-LINE0..15`) |
| `CBSTM03B.CBL` | `CREASTMT` | I/O subprogram for CBSTM03A via `WS-M03B-AREA` (open/read/close TRNXFILE, XREFFILE, CUSTFILE, ACCTFILE) |
| `CBEXPORT.cbl` | `CBEXPORT` | Branch-migration export — serializes CUST/ACCT/XREF/TRANSACT/CARD into 500-byte polymorphic `CVEXPORT` records |
| `CBIMPORT.cbl` | `CBIMPORT` | Branch-migration import — dispatches export records by type discriminator into normalized outputs + error log |
| `COBSWAIT.cbl` | `WAITSTEP` | Wait/sleep utility (parm in centiseconds) |

### 3.2 `app/cpy/` — data copybooks → entities

| Copybook | Record | Entity / role |
|:---------|:-------|:--------------|
| `CVACT01Y` | `ACCOUNT-RECORD` (300B) | Account: id, status, curr-bal, credit/cash limits, open/expire/reissue dates, cycle debit/credit, group-id |
| `CVACT02Y` | `CARD-RECORD` (150B) | Card: number, acct-id, CVV, embossed name, expiry, status |
| `CVACT03Y` | `CARD-XREF-RECORD` (50B) | Card→customer→account cross-reference |
| `CVCUS01Y` / `CUSTREC.cpy` | `CUSTOMER-RECORD` (500B) | Customer: names, 3-line address, phones, SSN, govt id, DOB, EFT acct, primary-cardholder flag, FICO |
| `CSUSR01Y` | `SEC-USER-DATA` (80B) | User security: id, fname, lname, password, type (A/U) |
| `CVTRA01Y` | `TRAN-CAT-BAL-RECORD` (50B) | Per-account transaction-category balance |
| `CVTRA02Y` | `DIS-GROUP-RECORD` (50B) | Disclosure group — interest rate by acct-group+type+category |
| `CVTRA03Y` | `TRAN-TYPE-RECORD` (60B) | Transaction type code+description |
| `CVTRA04Y` | `TRAN-CAT-RECORD` (60B) | Transaction category (type+cat+desc) |
| `CVTRA05Y` | `TRAN-RECORD` (350B) | Posted transaction (id, type, cat, source, desc, amount, merchant, card, timestamps) |
| `CVTRA06Y` | `DALYTRAN-RECORD` (350B) | Daily transaction input feed (same shape + card num) |
| `CVTRA07Y` | report layouts | Report headers/totals for `CBTRN03C` |
| `CVEXPORT.cpy` | `EXPORT-RECORD` (500B) | Polymorphic export record: 40B header + `REDEFINES` payload (C/A/T/X/K types) |
| `COSTM01.CPY` | `TRNX-RECORD` | Statement transaction layout (key = card+id) |
| `COCOM01Y` | `CARDDEMO-COMMAREA` | Session state passed between programs (≈ session token) |
| `COADM02Y`, `COMEN02Y` | menu option arrays | Menu option tables for admin/main menus |
| `CSDAT01Y`, `CSLKPCDY`, `CSMSG01Y`, `CSMSG02Y`, `CSSETATY`, `CSSTRPFY`, `CSUTLDPY`, `CSUTLDWY`, `CODATECN`, `COTTL01Y`, `UNUSED1Y` | misc | Date-utility interface (`CSUTLDWY`/`CSUTLDPY`), message texts, screen titles, string helpers |

### 3.3 `app/bms/` + `app/cpy-bms/` — 17 screen maps

`COACTUP`, `COACTVW`, `COADM01`, `COBIL00`, `COCRDLI`, `COCRDSL`, `COCRDUP`,
`COMEN01`, `CORPT00`, `COSGN00`, `COTRN00`, `COTRN01`, `COTRN02`, `COUSR00`,
`COUSR01`, `COUSR02`, `COUSR03` — one BMS physical map + one symbolic copybook
per screen listed in §3.1. → modernized as React screens/routes.

### 3.4 `app/jcl/` — 37 batch jobs

| JCL | Program | Feature |
|:----|:--------|:--------|
| `DUSRSECJ` | IEBGENER+IDCAMS | Seed USRSEC (ADMIN001–005, USER0001–005 / `PASSWORD`) |
| `ACCTFILE` | IDCAMS | Define+load account KSDS from `ACCTDATA.PS` |
| `CARDFILE` | IDCAMS | Define+load card KSDS |
| `CUSTFILE`, `DEFCUST` | IDCAMS | Define+load customer KSDS |
| `XREFFILE` | IDCAMS | Define+load xref KSDS |
| `TRANFILE` | IDCAMS | Load TRANSACT KSDS |
| `DISCGRP`, `TCATBALF`, `TRANCATG`, `TRANTYPE` | IDCAMS | Load reference tables |
| `DALYREJS`, `DEFGDGB`, `DEFGDGD`, `REPTFILE` | IDCAMS | Define GDGs (reject file, backups, reports, Db2 extracts) |
| `ESDSRRDS` | IEBGENER+IDCAMS | Define ESDS/RRDS datasets |
| `TRANIDX` | IDCAMS | Alternate index on TRANSACT (card-num) |
| `TRANBKP` | IDCAMS | Backup transaction master |
| `COMBTRAN` | SORT+IDCAMS | Merge system + daily transactions |
| `CLOSEFIL`, `OPENFIL` | IEFBR14/CEMT | Close/open files in CICS around batch |
| `POSTTRAN` | CBTRN02C | Daily posting |
| `INTCALC` | CBACT04C | Interest calculation |
| `CREASTMT` | SORT+IDCAMS+CBSTM03A | Statement generation |
| `TRANREPT` | SORT+CBTRN03C | Transaction detail report |
| `READACCT`/`READCARD`/`READCUST`/`READXREF` | CBACT01C/02C/03C/CBCUS01C | File print/audit utilities |
| `PRTCATBL` | IEFBR14+SORT | Print transaction-category balance table |
| `CBEXPORT`, `CBIMPORT` | CBEXPORT/CBIMPORT | Branch migration export/import |
| `CBADMCDJ` | DFHCSDUP | CICS resource definition |
| `FTPJCL` | FTP | Dataset FTP transfer |
| `TXT2PDF1` | IKJEFT1B | Text→PDF conversion of statements |
| `INTRDRJ1`, `INTRDRJ2` | IEBGENER→INTRDR | Submit jobs via internal reader |
| `WAITSTEP` | COBSWAIT | Wait between batch steps |

### 3.5 `app/data/` — seed data

| File | Records | Copybook | Entity |
|:-----|:--------|:---------|:-------|
| `acctdata.txt` | 50 | CVACT01Y | Accounts (zoned-signed money fields) |
| `carddata.txt` | 50 | CVACT02Y | Cards |
| `cardxref.txt` | 50 | CVACT03Y | Xref |
| `custdata.txt` | 50 | CVCUS01Y | Customers |
| `dailytran.txt` | 300 | CVTRA06Y | Daily transaction feed |
| `discgrp.txt` | 51 | CVTRA02Y | Disclosure groups / interest rates |
| `tcatbal.txt` | 50 | CVTRA01Y | Category balances |
| `trancatg.txt` | 18 | CVTRA04Y | Transaction categories |
| `trantype.txt` | 7 | CVTRA03Y | Transaction types |
| `EBCDIC/AWS.M2.CARDDEMO.*` | binary | — | EBCDIC equivalents incl. USRSEC, EXPORT.DATA |
| `app/catlg/LISTCAT.txt` | — | — | IDCAMS LISTCAT of all clusters |

Money fields use zoned-decimal sign overpunch (`{`=+0, `}`=−0, `A`–`I`=+1..9,
`J`–`R`=−1..9) with implied `V99`.

### 3.6 Optional modules (`app/app-*/`)

- **`app-authorization-ims-db2-mq`** — pending credit-card authorizations:
  `COPAUS0C` (auth request menu), `COPAUS1C`/`COPAUS2C` (pending summary/detail),
  `COPAUA0C` (MQ-triggered engine), `CBPAUP0C` (batch purge of expired auths,
  `CBPAUP0J`); BMS `COPAU00`/`COPAU01`; IMS DBD/PSB (`DBPAUTP0`, `PSBPAUTB`/`L`);
  DB2 DDL `AUTHFRDS`/`XAUTHFRD`; JCL for IMS load/unload (`LOADPADB`,
  `UNLDPADB`, `UNLDGSAM`, `DBPAUTP0`) — → REST: list/get/expire authorizations.
- **`app-transaction-type-db2`** — transaction-type reference data in Db2:
  `COTRTLIC` (list/delete via cursor), `COTRTUPC` (add/update), `COBTUPDT`
  (batch maintenance, `MNTTRDB2`), DDL `TRNTYPE`/`TRNTYCAT`, `TRANEXTR` extract —
  → REST CRUD on transaction types/categories.
- **`app-vsam-mq`** — MQ-driven inquiries: `CODATE01` (system date, `CDRD`),
  `COACCT01` (account inquiry, `CDRA`) — → REST endpoints.

### 3.7 Supporting files

- `app/asm/COBDATFT.asm`, `MVSWAIT.asm` + `app/maclib/*.mac` — date-conversion and wait macros (features absorbed into date utility).
- `app/csd/CRDDEMO*.CSD` — CICS resource definitions (≈ route table).
- `app/ctl/REPROCT.ctl`, `app/app-transaction-type-db2/ctl/*` — IDCAMS/DB2 utility control cards.
- `app/proc/REPROC.prc`, `TRANREPT.prc` — JCL procedures.
- `app/scheduler/CardDemo.controlm`, `CardDemo.ca7` — Control-M/CA7 scheduling of the batch pipeline.
- `samples/` — compile procs (`BUILDBAT`/`BUILDONL`/`BUILDBMS`/`BLDCIDB2`), compile JCL, Micro Focus / UniKix runtime bundles.
- `scripts/` — remote submit/compile/upload helpers and file markers.
- `diagrams/` — UI screenshots and data-model drawio.

## 4. Data model for the modernized app

Entities (all parsed from `app/data/ASCII` at backend startup into SQLite):

`User` (from `DUSRSECJ` instream data) · `Account` · `Card` · `Customer` ·
`CardXref` · `Transaction` (posted) + `DailyTransaction` (pending feed) ·
`TransactionType` · `TransactionCategory` · `DisclosureGroup` ·
`TransactionCategoryBalance` · `PendingAuthorization` (synthesized from the
authorization module's semantics) · `RejectRecord`.

Relationships: `Customer 1—n Xref n—1 Account 1—n Card`; `Card 1—n Transaction`;
`Transaction n—1 Type/Category`; `Account n—1 DisclosureGroup` (via group-id);
`Account 1—n TranCatBal`.

## 5. Feature catalog → modernization mapping

| # | Feature (COBOL/JCL) | Modernized implementation |
|:--|:--------------------|:--------------------------|
| F1 | Signon / logout (COSGN00C, USRSEC) | `POST /api/auth/login` → token; React login screen; admin vs regular role |
| F2 | Main/admin menus (COMEN01C/COADM01C) | React dashboard with role-gated options |
| F3 | Account view (COACTVWC) | `GET /api/accounts/{id}` (+xref join → customer) |
| F4 | Account update (COACTUPC) + validation | `PUT /api/accounts/{id}` with field validators |
| F5 | Card list/view/update (COCRDLIC/SLC/UPC) | `GET /api/cards?acctId`, `GET/PUT /api/cards/{num}` |
| F6 | Transaction list/view/add (COTRN00C/01C/02C) | `GET /api/transactions` (paged, filterable), `GET /{id}`, `POST` (validates card/type/cat, posts) |
| F7 | Transaction report by date range (CORPT00C+TRANREPT/CBTRN03C) | `GET /api/reports/transactions?from&to` — itemized + page/account/grand totals |
| F8 | Bill payment (COBIL00C) | `POST /api/billpay/{acctId}` — posts payment transaction, zeroes balance |
| F9 | User admin (COUSR00C–03C) | `GET/POST/PUT/DELETE /api/admin/users` (admin-only; protects last admin) |
| F10 | Transaction-type maintenance (COTRTLIC/COTRTUPC, Db2 module) | `GET/POST/PUT/DELETE /api/admin/tran-types` and `/tran-categories` |
| F11 | Daily posting (POSTTRAN/CBTRN02C + DALYREJS rejects) | `POST /api/batch/post-daily` — validates feed, posts, returns posted+rejects |
| F12 | Interest calculation (INTCALC/CBACT04C + DISCGRP) | `POST /api/batch/interest` — applies group rates, posts interest txns |
| F13 | Statement generation (CREASTMT/CBSTM03A/B) | `GET /api/statements/{acctId}` — itemized statement (JSON + HTML) |
| F14 | Pending authorizations (IMS/DB2/MQ module: COPAUS0C/S1C/UA0C, CBPAUP0C) | `GET /api/authorizations`, `GET /{id}`, `POST /api/batch/purge-expired` |
| F15 | MQ inquiries (CODATE01/COACCT01) | `GET /api/system/date`, covered by F3 account endpoint |
| F16 | Branch export/import (CBEXPORT/CBIMPORT, CVEXPORT) | `GET /api/batch/export` (typed records), `POST /api/batch/import` |
| F17 | Batch/audit utilities (READACCT etc., PRTCATBL, LISTCAT) | `GET /api/batch/audit/{file}` — record dumps for ops |
| F18 | Date validation utility (CSUTLDTC, COBDATFT) | Backend `utils/dates.py` used across features |
| F19 | Health / readiness (new — required for Cloud Run) | `GET /api/health` |

Out of scope as features (infrastructure-only): CLOSEFIL/OPENFIL, GDG defs,
FTP/TXT2PDF/INTRDR, CSD setup, schedulers, emulator bundles — documented above
but not re-implemented.

## 6. Architecture of the new code

```
modernized/
  backend/    FastAPI app, SQLite store, seed parsers, pytest suite, Dockerfile
  frontend/   React+TS+Vite SPA, Vitest suite, nginx Dockerfile
.github/workflows/ci.yml   lint + tests + docker builds
docs/TECHNICAL_ANALYSIS.md this document
```

The original `app/`, `samples/`, `scripts/`, `diagrams/` trees are untouched.

## 7. Deployment plan

- GitHub Actions CI: ruff/eslint lint, pytest + vitest, docker build of both images.
- On `main`: build images → Artifact Registry (`{region}-docker.pkg.dev/project-52fec649-85c9-414f-911/carddemo`) → two Cloud Run services (`carddemo-backend`, `carddemo-frontend`); frontend gets the backend URL at runtime; smoke-test health + key flows; scan Cloud Run logs.
- Regions chosen per service are recorded in the final report.
