import os
import subprocess
import shutil

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Velmora Co. Production ERP &middot; Documentation</title>
<style>
    @page {
        size: A4;
        margin: 18mm 16mm;
        @bottom-right {
            content: counter(page);
            font-size: 9pt;
            color: #666;
        }
    }
    *, *:before, *:after {
        box-sizing: border-box;
    }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.55;
        color: #242c17;
        background: #ffffff;
        margin: 0;
        padding: 0;
    }
    .cover {
        padding: 40px 0 30px;
        border-bottom: 3px solid #66754C;
        margin-bottom: 25px;
    }
    .brand-mark {
        font-size: 11pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #66754C;
        margin-bottom: 6px;
    }
    h1 {
        font-size: 24pt;
        font-weight: 800;
        color: #1f2714;
        margin: 0 0 8px 0;
        letter-spacing: -0.5px;
    }
    .subtitle {
        font-size: 12pt;
        color: #555f46;
        margin: 0 0 16px 0;
        font-weight: 500;
    }
    .meta-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        background: #faf7ef;
        border: 1px solid #e4dbc7;
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 15px;
        font-size: 9pt;
    }
    .meta-item b {
        display: block;
        color: #1f2714;
        font-size: 8pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    h2 {
        font-size: 14pt;
        font-weight: 700;
        color: #1f2714;
        border-bottom: 1.5px solid #dcd3bd;
        padding-bottom: 5px;
        margin: 28px 0 12px 0;
        page-break-after: avoid;
    }
    h3 {
        font-size: 11pt;
        font-weight: 700;
        color: #4b5735;
        margin: 18px 0 8px 0;
        page-break-after: avoid;
    }
    p, li {
        color: #2b331f;
        text-align: justify;
    }
    ul, ol {
        margin: 6px 0 12px 20px;
        padding: 0;
    }
    li {
        margin-bottom: 4px;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0 18px 0;
        font-size: 8.5pt;
        page-break-inside: auto;
    }
    tr {
        page-break-inside: avoid;
        page-break-after: auto;
    }
    thead {
        display: table-header-group;
    }
    th {
        background: #f2ede1;
        color: #1f2714;
        font-weight: 700;
        text-align: left;
        padding: 7px 8px;
        border: 1px solid #d5cbb4;
        font-size: 8.5pt;
    }
    td {
        padding: 6px 8px;
        border: 1px solid #e4dbc7;
        vertical-align: top;
    }
    tbody tr:nth-child(even) {
        background: #faf8f3;
    }
    .code-tag {
        font-family: Consolas, Monaco, monospace;
        font-size: 8pt;
        background: #eee8d8;
        padding: 1px 4px;
        border-radius: 3px;
        color: #3f472f;
    }
    .badge {
        display: inline-block;
        padding: 2px 6px;
        font-size: 7.5pt;
        font-weight: 700;
        border-radius: 4px;
        text-transform: uppercase;
    }
    .badge-mgr {
        background: rgba(102, 117, 76, 0.15);
        color: #4b5735;
    }
    .badge-stf {
        background: rgba(196, 137, 39, 0.15);
        color: #7a4f10;
    }
    .page-break {
        page-break-before: always;
    }
    .diagram-card {
        background: #ffffff;
        border: 1px solid #d5cbb4;
        border-radius: 8px;
        padding: 14px;
        margin: 14px 0 20px 0;
        page-break-inside: avoid;
        text-align: center;
    }
    .diagram-caption {
        font-size: 8.5pt;
        color: #667252;
        font-weight: 600;
        margin-top: 8px;
        text-align: center;
    }
    .callout {
        background: #faf7ef;
        border-left: 4px solid #66754C;
        padding: 10px 14px;
        margin: 12px 0;
        border-radius: 0 6px 6px 0;
        font-size: 9.5pt;
    }
    .callout b {
        color: #4b5735;
    }
</style>
</head>
<body>

<div class="cover">
    <div class="brand-mark">Velmora Co. &middot; Manufacturing ERP</div>
    <h1>Production &amp; Manufacturing Module</h1>
    <div class="subtitle">Complete Technical Documentation &amp; Capstone Defense Specification</div>
    <div class="meta-grid">
        <div class="meta-item"><b>Project Team</b>Team 3 (Production)</div>
        <div class="meta-item"><b>Target Industry</b>Furniture &amp; Woodcraft</div>
        <div class="meta-item"><b>Stack</b>Python 3.11, Flask, PostgreSQL</div>
        <div class="meta-item"><b>Release Date</b>October 2026</div>
    </div>
</div>

<h2>1. Module Description</h2>
<p>
The <b>Production &amp; Manufacturing Module</b> is the central workshop engine of the Velmora Co. Enterprise Resource Planning (ERP) platform. In a custom and batch furniture business, our biggest operational challenges are preventing workshop standstills, ensuring raw lumber and hardware are on hand before workers start cutting, and making sure that completed dining chairs or bedframes automatically show up in the inventory warehouse the moment they pass quality inspection.
</p>
<p>
Our module connects every step of the furniture manufacturing process: from cataloging furniture dimensions and setting up 1-unit Bill of Materials (BOM) recipes, to scheduling workshop batches, verifying material availability (MRP), dispatching inventory, tracking carpenter milestone progress with mobile photo proofs, and recording final QA approvals before rolling up direct job costs for Corporate Accounting.
</p>

<div class="callout">
<b>Cross-Departmental Integrations in the Enterprise Database:</b>
<p>Our module operates with dedicated internal role-based access control (Production Manager vs. Workshop Floor Staff), while interfacing directly with two core partner systems in the enterprise database:</p>
<ul>
    <li><b>Team 2 (Inventory &amp; Warehousing):</b> Live bidirectional integration. We read live on-hand raw material quantities (<span class="code-tag">raw_material</span>) to calculate MRP shortage checks. When materials are dispatched to the workshop, our atomic database transactions deduct warehouse stock automatically. When finished furniture batches pass QA inspection, our module automatically credits finished goods stock (<span class="code-tag">finished_goods</span>) and catalog records (<span class="code-tag">item_master</span>) in real time. We also monitor zero-stock items to initiate restock batches.</li>
    <li><b>Team 5 (Finance &amp; Cost Accounting):</b> Outbound job costing integration. We calculate the exact manufacturing cost for each completed batch (actual direct materials consumed, workshop labor hours logged, and standard 15% factory overhead) and publish the audited records to <span class="code-tag">prod_productioncost</span> for general ledger journal entries and inventory COGS valuation.</li>
</ul>
</div>

<h2>2. Objectives</h2>

<h3>2.1 General Objective</h3>
<p>
To build an automated, responsive, and traceable Production &amp; Manufacturing ERP module for Velmora Co. that coordinates workshop floor activities, prevents raw material shortages, verifies assembly quality with photographic proof, and publishes accurate job costs to Corporate Accounting without manual double-entry.
</p>

<h3>2.2 Specific Objectives</h3>
<ol>
    <li><b>Standardize Recipe Formulation:</b> Allow managers to create Bill of Materials (BOM) recipes based on 1 finished unit, which dynamically scales across any batch size (e.g. 10 or 50 chairs).</li>
    <li><b>Prevent Floor Bottlenecks with MRP:</b> Implement Material Requirements Planning that compares batch demand against live warehouse inventory, alerting managers to shortages and locking order release until materials are verified.</li>
    <li><b>Safeguard Inventory with Atomic Transactions:</b> Guarantee that material stock deductions and finished goods additions happen inside single ACID database transactions, preventing negative or desynchronized stock balances.</li>
    <li><b>Enforce Physical Quality Assurance (QA):</b> Implement a 90% workshop gate requiring carpenters to upload client-compressed photos of their workmanship, which supervisors must review before approving stock intake.</li>
    <li><b>Automate Job Cost Accounting:</b> Compute direct material costs from dispatched inventory, record labor hours, apply a standard 15% factory overhead, and export finalized cost sheets to Accounting.</li>
    <li><b>Enforce Enterprise Separation of Duties (SoD):</b> Restrict order creation, recipe edits, material releases, and financial costing to the Production Manager, while allowing floor staff to view assigned batches and log build milestones.</li>
    <li><b>Deliver Low-Latency Cloud Access:</b> Use persistent connection pooling and in-memory caching to eliminate remote SSL handshake delays to our cloud database.</li>
</ol>

<div class="page-break"></div>

<h2>3. Functional Requirements (FR)</h2>
<p>
The functional requirements describe every feature and user action across the 11 sidebar tabs of the Velmora Production ERP.
</p>

<table>
    <thead>
        <tr>
            <th style="width: 12%;">Req ID</th>
            <th style="width: 18%;">System Screen</th>
            <th style="width: 10%;">Role</th>
            <th style="width: 25%;">User Input / Trigger</th>
            <th style="width: 35%;">System Logic &amp; Database State Change</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><b>FR-AUTH-01</b></td>
            <td>Login Screen</td>
            <td><span class="badge badge-mgr">Both</span></td>
            <td>Enters email/username and password.</td>
            <td>Validates credentials against <span class="code-tag">public.users</span>. Verifies user belongs to Department 6 (<span class="code-tag">public.employee</span>). Resolves Position 6 as Manager and Position 2 as Staff.</td>
        </tr>
        <tr>
            <td><b>FR-AUTH-02</b></td>
            <td>Route Guard</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Staff attempts to access Manager route.</td>
            <td>Server decorator <span class="code-tag">@manager_required</span> blocks unauthorized requests, flashes an alert, and redirects to Dashboard.</td>
        </tr>
        <tr>
            <td><b>FR-AUTH-03</b></td>
            <td>Sign Out</td>
            <td><span class="badge badge-mgr">Both</span></td>
            <td>Clicks "Sign Out" in profile footer.</td>
            <td>Destroys auth session keys while preserving flash messages. Sets <span class="code-tag">Cache-Control: no-store</span> to block back-button cache.</td>
        </tr>
        <tr>
            <td><b>FR-DSH-01</b></td>
            <td>Dashboard</td>
            <td><span class="badge badge-mgr">Both</span></td>
            <td>Dashboard load.</td>
            <td>Aggregates active orders, completed batches, weekly activity bar chart, deadline tracking, and stage readiness bars.</td>
        </tr>
        <tr>
            <td><b>FR-DSH-02</b></td>
            <td>Dashboard</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Stockout alert clicked.</td>
            <td>Queries zero-stock items in <span class="code-tag">finished_goods</span> and links directly to order creation pre-filled with the stockout item.</td>
        </tr>
        <tr>
            <td><b>FR-DSH-03</b></td>
            <td>Dashboard</td>
            <td><span class="badge badge-mgr">Both</span></td>
            <td>Activity Timeline view.</td>
            <td>Pulls the latest 4 live operational milestones (order creations, material dispatches, milestone advances, QC completions) using workshop terminology.</td>
        </tr>
        <tr>
            <td><b>FR-PRD-01</b></td>
            <td>Product Master</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Add/Edit Furniture Modal.</td>
            <td>Validates product dimensions and positive selling price; inserts or updates record in <span class="code-tag">prod_furniture</span>. (Staff has read-only view).</td>
        </tr>
        <tr>
            <td><b>FR-BOM-01</b></td>
            <td>Bill of Materials</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Create Recipe Modal.</td>
            <td>Initializes a 1-unit basis recipe header in <span class="code-tag">prod_bom</span> linked to a specific furniture blueprint.</td>
        </tr>
        <tr>
            <td><b>FR-BOM-02</b></td>
            <td>Bill of Materials</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Add/Delete Material Item.</td>
            <td>Inserts or removes line items in <span class="code-tag">prod_bomitem</span> with required quantities and units of measure. Recalculates unit standard cost.</td>
        </tr>
        <tr>
            <td><b>FR-BOM-03</b></td>
            <td>Bill of Materials</td>
            <td><span class="badge badge-stf">Staff</span></td>
            <td>Staff views recipe list.</td>
            <td>System renders physical quantities and components but masks standard material unit costs and profit margins.</td>
        </tr>
        <tr>
            <td><b>FR-ORD-01</b></td>
            <td>Production Order</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Create Order Modal.</td>
            <td>Verifies BOM exists for product. Inserts batch order in <span class="code-tag">prod_productionorder</span> with status <span class="code-tag">Draft</span>.</td>
        </tr>
        <tr>
            <td><b>FR-ORD-02</b></td>
            <td>Production Order</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Warehouse Stockouts Restock Link.</td>
            <td>Pre-populates selected zero-stock furniture model and automatically configures batch purpose as <span class="code-tag">Warehouse Restock</span>.</td>
        </tr>
        <tr>
            <td><b>FR-PLN-01</b></td>
            <td>Production Planning</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Edit Plan Modal.</td>
            <td>Sets planned start date, due date, and assigns a Department 6 craftsman. Dropdown displays active batch count per craftsman to prevent overloading.</td>
        </tr>
        <tr>
            <td><b>FR-PLN-02</b></td>
            <td>Production Planning</td>
            <td><span class="badge badge-mgr">Both</span></td>
            <td>Planning View load.</td>
            <td>Evaluates batch health: <span class="code-tag">Needs Plan</span> (no dates), <span class="code-tag">On Schedule</span>, <span class="code-tag">Overdue</span>, or <span class="code-tag">Completed</span>.</td>
        </tr>
        <tr>
            <td><b>FR-MRP-01</b></td>
            <td>Material Requirement</td>
            <td><span class="badge badge-mgr">Both</span></td>
            <td>Requirement View load.</td>
            <td>Multiplies BOM item quantity by planned batch quantity. Compares against live stock in <span class="code-tag">raw_material</span> and flags shortages.</td>
        </tr>
        <tr>
            <td><b>FR-MRP-02</b></td>
            <td>Material Requirement</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Clicks "Release to Floor".</td>
            <td>Validates 100% material availability. Updates order status from <span class="code-tag">Draft</span> to <span class="code-tag">Released</span>.</td>
        </tr>
        <tr>
            <td><b>FR-ISS-01</b></td>
            <td>Material Issuance</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Clicks "Approve Dispatch".</td>
            <td>Atomic transaction: subtracts raw materials from <span class="code-tag">raw_material</span>, logs dispatch in <span class="code-tag">prod_materialissuance</span>, seeds monitoring at 0%, sets status to <span class="code-tag">In Progress</span>.</td>
        </tr>
        <tr>
            <td><b>FR-MON-01</b></td>
            <td>Production Monitoring</td>
            <td><span class="badge badge-mgr">Both</span></td>
            <td>Update Progress Modal.</td>
            <td>Updates progress milestone (25% Cutting, 50% Joinery, 75% Sanding, 90% Ready for QA) and logs operator notes in <span class="code-tag">prod_productionmonitoring</span>.</td>
        </tr>
        <tr>
            <td><b>FR-MON-02</b></td>
            <td>Production Monitoring</td>
            <td><span class="badge badge-mgr">Both</span></td>
            <td>Uploads stage photo.</td>
            <td>Compresses photo client-side via HTML5 Canvas (max 1280px, 82% quality). Uploads to Supabase CDN bucket and saves URL in <span class="code-tag">prod_attachments</span>.</td>
        </tr>
        <tr>
            <td><b>FR-QA-01</b></td>
            <td>Finished Goods</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Order reaches 90% build.</td>
            <td>Order surfaces in QA queue. Manager inspects full-resolution photos in image lightbox viewer before approving.</td>
        </tr>
        <tr>
            <td><b>FR-QA-02</b></td>
            <td>Finished Goods</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Selects "Passed".</td>
            <td>Atomic transaction: logs pass in <span class="code-tag">prod_productionoutput</span>, sets progress to 100%, sets order to <span class="code-tag">Completed</span>, and upserts batch quantity into Team 2 <span class="code-tag">finished_goods</span>.</td>
        </tr>
        <tr>
            <td><b>FR-QA-03</b></td>
            <td>Finished Goods</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Selects "Rework Required".</td>
            <td>Logs rework reason, rolls back progress to 50% (Joinery &amp; Assembly), increments rework counter, and sends batch back to workshop.</td>
        </tr>
        <tr>
            <td><b>FR-CST-01</b></td>
            <td>Production Costing</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Record Cost Modal.</td>
            <td>Rolls up direct material cost from issuances, calculates labor cost (hours &times; rate), adds 15% overhead, and commits cost sheet to <span class="code-tag">prod_productioncost</span> for Team 5.</td>
        </tr>
        <tr>
            <td><b>FR-REP-01</b></td>
            <td>Production Reports</td>
            <td><span class="badge badge-mgr">Manager</span></td>
            <td>Reports Tab load.</td>
            <td>Renders factory yield KPIs, order performance ledger, material variance analysis, and paginated transaction audit trail (Who, What, When).</td>
        </tr>
    </tbody>
</table>

<div class="page-break"></div>

<h2>4. Non-Functional Requirements (NFR)</h2>

<h3>4.1 Performance &amp; Cloud Database Speed</h3>
<ul>
    <li><b>Connection Socket Pooling:</b> Because our PostgreSQL database is hosted on a Supabase cloud instance in Australia, opening a new SSL connection on every web request takes 2.5 to 3.5 seconds. We implemented <span class="code-tag">psycopg2.pool.ThreadedConnectionPool</span>, cutting connection checkout time to under 1 millisecond.</li>
    <li><b>In-Memory Catalog Caching:</b> Catalog tables that rarely change during a session (like furniture blueprints and raw material lists) are cached in memory in <span class="code-tag">cache.py</span> with automatic invalidation whenever items are updated.</li>
    <li><b>N+1 Query Elimination:</b> In Material Requirements, component lookups are done against an in-memory dictionary rather than executing repetitive SQL queries inside loops.</li>
</ul>

<h3>4.2 Security &amp; Internal Controls</h3>
<ul>
    <li><b>Password Security:</b> User passwords are encrypted using bcrypt/PBKDF2 hashes. No plain text passwords exist in the database or server logs.</li>
    <li><b>Server-Side Route Protection:</b> Modifying actions are protected with <span class="code-tag">@manager_required</span> decorators on the backend, ensuring that even if a staff member attempts to send direct POST requests to create orders or change recipes, the server halts the attempt.</li>
    <li><b>Confidential Margin Masking:</b> Unit purchase costs, total BOM recipe costs, and profit markups are completely hidden from floor staff templates to protect company margins.</li>
    <li><b>Session &amp; History Protection:</b> When users log out, the server clears session keys and responds with <span class="code-tag">Cache-Control: no-store</span> to stop browsers from showing cached data when clicking the back button.</li>
</ul>

<h3>4.3 Data Integrity &amp; Transaction Safety</h3>
<ul>
    <li><b>ACID Multi-Table Transactions:</b> Complex workflows—like dispatching materials (which updates inventory, inserts issuance logs, initializes monitoring, and changes order status)—are wrapped inside a single atomic transaction. If any part fails, the entire transaction rolls back cleanly.</li>
    <li><b>Zero Negative Stock Guarantee:</b> Inventory update queries enforce <span class="code-tag">AND stock_quantity >= %s</span>, raising an immediate error if stock is insufficient rather than allowing inventory to go negative.</li>
</ul>

<h3>4.4 Mobile Usability &amp; Responsiveness</h3>
<ul>
    <li><b>Responsive Layout (&le; 768px):</b> Built with mobile CSS media queries so supervisors and carpenters can use tablets or phones in the workshop. The top bar collapses into a clean hamburger menu and data tables support smooth touch horizontal scrolling.</li>
    <li><b>Poka-Yoke Safeguards:</b> Crucial actions like order cancellations, QA rejections, and inventory issuances require deliberate modal confirmation to avoid accidental clicks.</li>
</ul>

<div class="page-break"></div>

<h2>5. Use Case Diagram</h2>
<p>
The use case diagram illustrates the roles and actions available to the <b>Production Manager</b> and <b>Production Staff</b>, as well as automatic integrations with partner department systems.
</p>

<div class="diagram-card">
    <svg width="680" height="380" viewBox="0 0 680 380" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="680" height="380" rx="8" fill="#faf8f3" stroke="#dcd3bd" stroke-width="1.5"/>
        
        <!-- System Boundary -->
        <rect x="170" y="20" width="340" height="340" rx="8" fill="#ffffff" stroke="#66754C" stroke-width="1.5" stroke-dasharray="4 4"/>
        <text x="185" y="42" font-size="11" font-weight="700" fill="#4b5735">Velmora Production ERP System</text>
        
        <!-- Manager Actor -->
        <circle cx="70" cy="90" r="16" fill="#66754C"/>
        <path d="M50 130 C50 110, 90 110, 90 130" stroke="#66754C" stroke-width="3" fill="none"/>
        <text x="70" y="148" font-size="10" font-weight="700" fill="#1f2714" text-anchor="middle">Production</text>
        <text x="70" y="160" font-size="10" font-weight="700" fill="#1f2714" text-anchor="middle">Manager</text>
        
        <!-- Staff Actor -->
        <circle cx="70" cy="260" r="16" fill="#c48927"/>
        <path d="M50 300 C50 280, 90 280, 90 300" stroke="#c48927" stroke-width="3" fill="none"/>
        <text x="70" y="318" font-size="10" font-weight="700" fill="#1f2714" text-anchor="middle">Production</text>
        <text x="70" y="330" font-size="10" font-weight="700" fill="#1f2714" text-anchor="middle">Staff</text>

        <!-- External Actors -->
        <rect x="525" y="95" width="135" height="48" rx="6" fill="#e9e4d4" stroke="#8E9B6D"/>
        <text x="592" y="117" font-size="9.5" font-weight="700" fill="#2b331f" text-anchor="middle">Team 2: Inventory</text>
        <text x="592" y="131" font-size="8" fill="#667252" text-anchor="middle">&amp; Warehousing</text>

        <rect x="525" y="270" width="135" height="48" rx="6" fill="#e9e4d4" stroke="#8E9B6D"/>
        <text x="592" y="292" font-size="9.5" font-weight="700" fill="#2b331f" text-anchor="middle">Team 5: Finance</text>
        <text x="592" y="306" font-size="8" fill="#667252" text-anchor="middle">&amp; Cost Accounting</text>
        
        <!-- Use Cases -->
        <g id="usecases" font-size="9" font-weight="600" fill="#1f2714">
            <rect x="195" y="55" width="130" height="26" rx="13" fill="#f4efe2" stroke="#66754C"/>
            <text x="260" y="72" text-anchor="middle">Manage BOM Recipes</text>

            <rect x="195" y="92" width="130" height="26" rx="13" fill="#f4efe2" stroke="#66754C"/>
            <text x="260" y="109" text-anchor="middle">Create Orders (Restock/Plan)</text>

            <rect x="195" y="129" width="130" height="26" rx="13" fill="#f4efe2" stroke="#66754C"/>
            <text x="260" y="146" text-anchor="middle">Schedule &amp; Assign Staff</text>

            <rect x="195" y="166" width="130" height="26" rx="13" fill="#f4efe2" stroke="#66754C"/>
            <text x="260" y="183" text-anchor="middle">Check MRP &amp; Release</text>

            <rect x="195" y="203" width="130" height="26" rx="13" fill="#f4efe2" stroke="#66754C"/>
            <text x="260" y="220" text-anchor="middle">Dispatch Raw Materials</text>

            <rect x="355" y="220" width="135" height="26" rx="13" fill="#fef1db" stroke="#c48927"/>
            <text x="422" y="237" text-anchor="middle">Update Build Milestones</text>

            <rect x="355" y="258" width="135" height="26" rx="13" fill="#fef1db" stroke="#c48927"/>
            <text x="422" y="275" text-anchor="middle">Upload Photo Proofs</text>

            <rect x="195" y="278" width="130" height="26" rx="13" fill="#f4efe2" stroke="#66754C"/>
            <text x="260" y="295" text-anchor="middle">Inspect Quality (QA)</text>

            <rect x="195" y="315" width="130" height="26" rx="13" fill="#f4efe2" stroke="#66754C"/>
            <text x="260" y="332" text-anchor="middle">Calculate Job Costs</text>
        </g>
        
        <!-- Connections Manager -->
        <line x1="90" y1="110" x2="195" y2="68" stroke="#66754C" stroke-width="1.2"/>
        <line x1="90" y1="110" x2="195" y2="105" stroke="#66754C" stroke-width="1.2"/>
        <line x1="90" y1="110" x2="195" y2="142" stroke="#66754C" stroke-width="1.2"/>
        <line x1="90" y1="110" x2="195" y2="179" stroke="#66754C" stroke-width="1.2"/>
        <line x1="90" y1="110" x2="195" y2="216" stroke="#66754C" stroke-width="1.2"/>
        <line x1="90" y1="110" x2="195" y2="291" stroke="#66754C" stroke-width="1.2"/>
        <line x1="90" y1="110" x2="195" y2="328" stroke="#66754C" stroke-width="1.2"/>

        <!-- Connections Staff -->
        <line x1="90" y1="280" x2="355" y2="233" stroke="#c48927" stroke-width="1.2"/>
        <line x1="90" y1="280" x2="355" y2="271" stroke="#c48927" stroke-width="1.2"/>

        <!-- External Links -->
        <line x1="325" y1="105" x2="525" y2="108" stroke="#8E9B6D" stroke-width="1.2" stroke-dasharray="3 3"/>
        <line x1="325" y1="179" x2="525" y2="118" stroke="#8E9B6D" stroke-width="1.2" stroke-dasharray="3 3"/>
        <line x1="325" y1="216" x2="525" y2="128" stroke="#8E9B6D" stroke-width="1.2" stroke-dasharray="3 3"/>
        <line x1="325" y1="291" x2="525" y2="136" stroke="#8E9B6D" stroke-width="1.2" stroke-dasharray="3 3"/>
        <line x1="325" y1="328" x2="525" y2="294" stroke="#8E9B6D" stroke-width="1.2" stroke-dasharray="3 3"/>
    </svg>
    <div class="diagram-caption">Figure 1: Use Case Diagram for Velmora Co. Production ERP Module</div>
</div>

<div class="page-break"></div>

<h2>6. System Operational Flowchart</h2>
<p>
This flowchart illustrates the step-by-step lifecycle of an order from initialization, through feasibility testing and physical workshop milestones, up to final QA transfer and job costing.
</p>

<div class="diagram-card">
    <svg width="680" height="620" viewBox="0 0 680 620" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="680" height="620" rx="8" fill="#faf8f3" stroke="#dcd3bd" stroke-width="1.5"/>
        
        <!-- Step 1 -->
        <rect x="230" y="20" width="220" height="38" rx="19" fill="#66754C"/>
        <text x="340" y="44" font-size="10" font-weight="700" fill="#ffffff" text-anchor="middle">1. Order Created (Restock / Scheduled)</text>
        <line x1="340" y1="58" x2="340" y2="80" stroke="#4b5735" stroke-width="2" marker-end="url(#arrow)"/>
        
        <!-- Step 2 -->
        <rect x="220" y="80" width="240" height="38" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <text x="340" y="96" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">2. Planning &amp; Scheduling</text>
        <text x="340" y="110" font-size="8" fill="#667252" text-anchor="middle">Set Start/Due Date &bull; Assign Workshop Craftsman</text>
        <line x1="340" y1="118" x2="340" y2="140" stroke="#4b5735" stroke-width="2"/>
        
        <!-- Step 3 Decision -->
        <polygon points="340,140 450,175 340,210 230,175" fill="#f4efe2" stroke="#66754C" stroke-width="1.5"/>
        <text x="340" y="172" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">3. MRP Check: Stock Available?</text>
        <text x="340" y="184" font-size="8" fill="#667252" text-anchor="middle">BOM Item Qty &times; Batch Size &le; On-Hand</text>
        
        <!-- Shortage Branch -->
        <line x1="450" y1="175" x2="550" y2="175" stroke="#9a4a3a" stroke-width="1.5"/>
        <line x1="550" y1="175" x2="550" y2="99" stroke="#9a4a3a" stroke-width="1.5"/>
        <line x1="550" y1="99" x2="460" y2="99" stroke="#9a4a3a" stroke-width="1.5"/>
        <rect x="465" y="155" width="80" height="18" rx="3" fill="#fbebe8"/>
        <text x="505" y="167" font-size="8" font-weight="700" fill="#9a4a3a" text-anchor="middle">No (Shortage)</text>

        <!-- Pass Branch -->
        <line x1="340" y1="210" x2="340" y2="235" stroke="#4b5735" stroke-width="2"/>
        <text x="355" y="225" font-size="8.5" font-weight="700" fill="#4b5735">Yes (Released)</text>

        <!-- Step 4 -->
        <rect x="220" y="235" width="240" height="38" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <text x="340" y="251" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">4. Material Issuance Dispatch</text>
        <text x="340" y="265" font-size="8" fill="#667252" text-anchor="middle">Atomic Deduction in raw_material &bull; Set In Progress</text>
        <line x1="340" y1="273" x2="340" y2="295" stroke="#4b5735" stroke-width="2"/>

        <!-- Step 5 -->
        <rect x="200" y="295" width="280" height="42" rx="6" fill="#ffffff" stroke="#c48927" stroke-width="1.5"/>
        <text x="340" y="311" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">5. Workshop Floor Assembly</text>
        <text x="340" y="327" font-size="8" fill="#7a4f10" text-anchor="middle">25% Cutting &rarr; 50% Joinery &rarr; 75% Sanding &rarr; 90% Ready for QA</text>
        <line x1="340" y1="337" x2="340" y2="360" stroke="#4b5735" stroke-width="2"/>

        <!-- Step 6 -->
        <rect x="220" y="360" width="240" height="38" rx="6" fill="#ffffff" stroke="#c48927" stroke-width="1.5"/>
        <text x="340" y="376" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">6. Mobile Photo Proof Upload</text>
        <text x="340" y="390" font-size="8" fill="#7a4f10" text-anchor="middle">Canvas Compressed &bull; Uploaded to Supabase CDN</text>
        <line x1="340" y1="398" x2="340" y2="420" stroke="#4b5735" stroke-width="2"/>

        <!-- Step 7 Decision -->
        <polygon points="340,420 440,455 340,490 240,455" fill="#f4efe2" stroke="#66754C" stroke-width="1.5"/>
        <text x="340" y="452" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">7. QA Inspection Decision</text>
        <text x="340" y="464" font-size="8" fill="#667252" text-anchor="middle">Lightbox Review by Manager</text>

        <!-- Rework Branch -->
        <line x1="240" y1="455" x2="140" y2="455" stroke="#c48927" stroke-width="1.5"/>
        <line x1="140" y1="455" x2="140" y2="316" stroke="#c48927" stroke-width="1.5"/>
        <line x1="140" y1="316" x2="200" y2="316" stroke="#c48927" stroke-width="1.5"/>
        <text x="175" y="445" font-size="8" font-weight="700" fill="#c48927" text-anchor="middle">Rework (Rollback to 50%)</text>

        <!-- Passed Branch -->
        <line x1="340" y1="490" x2="340" y2="515" stroke="#4b5735" stroke-width="2"/>
        <text x="355" y="505" font-size="8.5" font-weight="700" fill="#4b5735">Passed</text>

        <!-- Step 8 -->
        <rect x="210" y="515" width="260" height="38" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <text x="340" y="531" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">8. Finished Goods Stock Intake &amp; Costing</text>
        <text x="340" y="545" font-size="8" fill="#667252" text-anchor="middle">Atomic Upsert to finished_goods &bull; Publish Job Cost to Team 5</text>
        <line x1="340" y1="553" x2="340" y2="575" stroke="#4b5735" stroke-width="2"/>

        <!-- Completed End -->
        <rect x="230" y="575" width="220" height="32" rx="16" fill="#4b5735"/>
        <text x="340" y="595" font-size="9.5" font-weight="700" fill="#ffffff" text-anchor="middle">Finished Goods in Warehouse</text>
    </svg>
    <div class="diagram-caption">Figure 2: Operational Manufacturing Lifecycle Flowchart</div>
</div>

<div class="page-break"></div>

<h2>7. Entity-Relationship Diagram (ERD)</h2>
<p>
The ERD shows how our internal <span class="code-tag">prod_</span> tables connect with shared enterprise tables (Inventory &amp; Warehousing and Finance).
</p>

<div class="diagram-card">
    <svg width="680" height="480" viewBox="0 0 680 480" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="680" height="480" rx="8" fill="#faf8f3" stroke="#dcd3bd" stroke-width="1.5"/>
        
        <!-- Table: prod_furniture -->
        <rect x="30" y="30" width="160" height="90" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="30" y="30" width="160" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="110" y="46" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_furniture</text>
        <text x="38" y="68" font-size="8" fill="#2b331f">PK furniture_id (SERIAL)</text>
        <text x="38" y="80" font-size="8" fill="#2b331f">furniture_name (VARCHAR)</text>
        <text x="38" y="92" font-size="8" fill="#2b331f">category (VARCHAR)</text>
        <text x="38" y="104" font-size="8" fill="#2b331f">selling_price (NUMERIC)</text>

        <!-- Table: prod_bom -->
        <rect x="260" y="30" width="150" height="65" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="260" y="30" width="150" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="335" y="46" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_bom</text>
        <text x="268" y="68" font-size="8" fill="#2b331f">PK bom_id (SERIAL)</text>
        <text x="268" y="82" font-size="8" fill="#2b331f">FK furniture_id (INT, UK)</text>

        <!-- Table: prod_bomitem -->
        <rect x="480" y="30" width="170" height="90" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="480" y="30" width="170" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="565" y="46" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_bomitem</text>
        <text x="488" y="68" font-size="8" fill="#2b331f">PK bom_item_id (SERIAL)</text>
        <text x="488" y="80" font-size="8" fill="#2b331f">FK bom_id (INT)</text>
        <text x="488" y="92" font-size="8" fill="#2b331f">FK material_id (INT)</text>
        <text x="488" y="104" font-size="8" fill="#2b331f">quantity_required (NUM)</text>

        <!-- Table: prod_productionorder -->
        <rect x="30" y="170" width="170" height="135" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="30" y="170" width="170" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="115" y="186" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_productionorder</text>
        <text x="38" y="208" font-size="8" fill="#2b331f">PK order_id (SERIAL)</text>
        <text x="38" y="220" font-size="8" fill="#2b331f">FK furniture_id (INT)</text>
        <text x="38" y="232" font-size="8" fill="#2b331f">planned_quantity (INT)</text>
        <text x="38" y="244" font-size="8" fill="#2b331f">status (VARCHAR)</text>
        <text x="38" y="256" font-size="8" fill="#2b331f">planned_start_date (DATE)</text>
        <text x="38" y="268" font-size="8" fill="#2b331f">due_date (DATE)</text>
        <text x="38" y="280" font-size="8" fill="#2b331f">FK assigned_to (INT)</text>
        <text x="38" y="292" font-size="8" fill="#2b331f">purpose (VARCHAR)</text>

        <!-- Table: prod_materialissuance -->
        <rect x="250" y="170" width="170" height="95" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="250" y="170" width="170" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="335" y="186" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_materialissuance</text>
        <text x="258" y="208" font-size="8" fill="#2b331f">PK issuance_id (SERIAL)</text>
        <text x="258" y="220" font-size="8" fill="#2b331f">FK order_id (INT)</text>
        <text x="258" y="232" font-size="8" fill="#2b331f">FK material_id (INT)</text>
        <text x="258" y="244" font-size="8" fill="#2b331f">quantity_issued (NUMERIC)</text>
        <text x="258" y="256" font-size="8" fill="#2b331f">issue_date (DATE)</text>

        <!-- Table: prod_productionmonitoring -->
        <rect x="470" y="170" width="180" height="105" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="470" y="170" width="180" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="560" y="186" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_productionmonitoring</text>
        <text x="478" y="208" font-size="8" fill="#2b331f">PK monitoring_id (SERIAL)</text>
        <text x="478" y="220" font-size="8" fill="#2b331f">FK order_id (INT, UK)</text>
        <text x="478" y="232" font-size="8" fill="#2b331f">progress (NUMERIC)</text>
        <text x="478" y="244" font-size="8" fill="#2b331f">rework_count (INT)</text>
        <text x="478" y="256" font-size="8" fill="#2b331f">current_stage (VARCHAR)</text>
        <text x="478" y="268" font-size="8" fill="#2b331f">start_date / completion_date</text>

        <!-- Table: prod_productionoutput -->
        <rect x="30" y="350" width="170" height="100" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="30" y="350" width="170" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="115" y="366" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_productionoutput</text>
        <text x="38" y="388" font-size="8" fill="#2b331f">PK output_id (SERIAL)</text>
        <text x="38" y="400" font-size="8" fill="#2b331f">FK order_id (INT)</text>
        <text x="38" y="412" font-size="8" fill="#2b331f">quantity (INT)</text>
        <text x="38" y="424" font-size="8" fill="#2b331f">quality_status (VARCHAR)</text>
        <text x="38" y="436" font-size="8" fill="#2b331f">inspection_date (DATE)</text>

        <!-- Table: prod_attachments -->
        <rect x="470" y="350" width="180" height="80" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="470" y="350" width="180" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="560" y="366" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_attachments</text>
        <text x="478" y="388" font-size="8" fill="#2b331f">PK attachment_id (SERIAL)</text>
        <text x="478" y="400" font-size="8" fill="#2b331f">FK monitoring_id (INT)</text>
        <text x="478" y="412" font-size="8" fill="#2b331f">file_url (TEXT)</text>
        <text x="478" y="424" font-size="8" fill="#2b331f">created_at (TIMESTAMP)</text>

        <!-- Table: prod_productioncost -->
        <rect x="250" y="350" width="170" height="100" rx="6" fill="#ffffff" stroke="#66754C" stroke-width="1.5"/>
        <rect x="250" y="350" width="170" height="24" rx="6 6 0 0" fill="#f2ede1"/>
        <text x="335" y="366" font-size="9.5" font-weight="700" fill="#1f2714" text-anchor="middle">prod_productioncost</text>
        <text x="258" y="388" font-size="8" fill="#2b331f">PK cost_id (SERIAL)</text>
        <text x="258" y="400" font-size="8" fill="#2b331f">FK order_id (INT, UK)</text>
        <text x="258" y="412" font-size="8" fill="#2b331f">material_cost (NUMERIC)</text>
        <text x="258" y="424" font-size="8" fill="#2b331f">labor_cost (NUMERIC)</text>
        <text x="258" y="436" font-size="8" fill="#2b331f">overhead_cost &bull; total_cost</text>

        <!-- Relationships -->
        <line x1="190" y1="62" x2="260" y2="62" stroke="#66754C" stroke-width="1.5"/>
        <line x1="410" y1="62" x2="480" y2="62" stroke="#66754C" stroke-width="1.5"/>
        <line x1="115" y1="120" x2="115" y2="170" stroke="#66754C" stroke-width="1.5"/>
        <line x1="200" y1="217" x2="250" y2="217" stroke="#66754C" stroke-width="1.5"/>
        <line x1="200" y1="235" x2="470" y2="235" stroke="#66754C" stroke-width="1.5"/>
        <line x1="115" y1="305" x2="115" y2="350" stroke="#66754C" stroke-width="1.5"/>
        <line x1="150" y1="305" x2="250" y2="390" stroke="#66754C" stroke-width="1.5"/>
        <line x1="560" y1="275" x2="560" y2="350" stroke="#66754C" stroke-width="1.5"/>
    </svg>
    <div class="diagram-caption">Figure 3: Relational Schema Architecture (ERD)</div>
</div>

<div class="page-break"></div>

<h2>8. Comprehensive Data Dictionary</h2>
<p>
This data dictionary details the tables, columns, constraints, and real-world purposes of each database entity managed by the Production module.
</p>

<h3>8.1 <span class="code-tag">public.prod_furniture</span> (Product Blueprint Catalog)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">furniture_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique furniture blueprint identifier.</td></tr>
        <tr><td><span class="code-tag">furniture_name</span></td><td>VARCHAR(150)</td><td>NO</td><td>NOT NULL</td><td>Commercial product name (e.g., Dining Chair, Oak Study Desk).</td></tr>
        <tr><td><span class="code-tag">category</span></td><td>VARCHAR(50)</td><td>NO</td><td>NOT NULL</td><td>Product category: Seating, Tables, Storage, Beds, or Custom.</td></tr>
        <tr><td><span class="code-tag">dimensions</span></td><td>VARCHAR(100)</td><td>YES</td><td>-</td><td>Standard workshop dimensions (Length &times; Width &times; Height in cm).</td></tr>
        <tr><td><span class="code-tag">selling_price</span></td><td>NUMERIC(10,2)</td><td>NO</td><td>CHECK &ge; 0.00</td><td>Standard retail selling price recommended in catalog.</td></tr>
        <tr><td><span class="code-tag">image_url</span></td><td>TEXT</td><td>YES</td><td>-</td><td>Public web link to product photography preview.</td></tr>
    </tbody>
</table>

<h3>8.2 <span class="code-tag">public.prod_bom</span> (Recipe Header)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">bom_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique recipe header identifier.</td></tr>
        <tr><td><span class="code-tag">furniture_id</span></td><td>INT</td><td>NO</td><td>UNIQUE, FK &rarr; prod_furniture</td><td>Enforces exactly 1 active master recipe per furniture model.</td></tr>
    </tbody>
</table>

<h3>8.3 <span class="code-tag">public.prod_bomitem</span> (Recipe Ingredients)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">bom_item_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique line item ingredient identifier.</td></tr>
        <tr><td><span class="code-tag">bom_id</span></td><td>INT</td><td>NO</td><td>FK &rarr; prod_bom (CASCADE)</td><td>Parent manufacturing recipe reference.</td></tr>
        <tr><td><span class="code-tag">material_id</span></td><td>INT</td><td>NO</td><td>FK &rarr; raw_material</td><td>Raw material from Team 2 inventory (e.g. mahogany lumber, wood screws).</td></tr>
        <tr><td><span class="code-tag">quantity_required</span></td><td>NUMERIC(10,2)</td><td>NO</td><td>CHECK &gt; 0.00</td><td>Exact amount of material needed to build 1 finished unit.</td></tr>
        <tr><td><span class="code-tag">unit_of_measure</span></td><td>VARCHAR(30)</td><td>YES</td><td>-</td><td>Unit of measure (e.g. board ft, pcs, liters, meters).</td></tr>
    </tbody>
</table>

<h3>8.4 <span class="code-tag">public.prod_productionorder</span> (Batch Authorization)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">order_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique production order tracking number (#PO-1, #PO-2).</td></tr>
        <tr><td><span class="code-tag">furniture_id</span></td><td>INT</td><td>NO</td><td>FK &rarr; prod_furniture</td><td>Furniture model authorized for production.</td></tr>
        <tr><td><span class="code-tag">planned_quantity</span></td><td>INT</td><td>NO</td><td>CHECK &gt; 0</td><td>Number of units scheduled to be produced in this batch.</td></tr>
        <tr><td><span class="code-tag">status</span></td><td>VARCHAR(30)</td><td>NO</td><td>DEFAULT 'Draft'</td><td>Lifecycle stage: Draft, Released, In Progress, Completed, Cancelled.</td></tr>
        <tr><td><span class="code-tag">order_date</span></td><td>DATE</td><td>NO</td><td>DEFAULT CURRENT_DATE</td><td>Date when the order was registered.</td></tr>
        <tr><td><span class="code-tag">planned_start_date</span></td><td>DATE</td><td>YES</td><td>-</td><td>Scheduled start date on workshop calendar.</td></tr>
        <tr><td><span class="code-tag">due_date</span></td><td>DATE</td><td>YES</td><td>-</td><td>Target deadline for completion and workshop delivery.</td></tr>
        <tr><td><span class="code-tag">purpose</span></td><td>VARCHAR(50)</td><td>NO</td><td>DEFAULT 'Warehouse Restock'</td><td>Manufacturing purpose: 'Warehouse Restock' (inventory replenishment) or 'Scheduled Batch' (planned production run).</td></tr>
        <tr><td><span class="code-tag">assigned_to</span></td><td>INT</td><td>YES</td><td>FK &rarr; employee</td><td>Craftsman in Department 6 responsible for leading assembly.</td></tr>
    </tbody>
</table>

<div class="page-break"></div>

<h3>8.5 <span class="code-tag">public.prod_materialissuance</span> (Inventory Dispatch Audit)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">issuance_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique dispatch voucher identifier (#IS-1, #IS-2).</td></tr>
        <tr><td><span class="code-tag">order_id</span></td><td>INT</td><td>NO</td><td>FK &rarr; prod_productionorder</td><td>Order receiving the dispatched raw materials.</td></tr>
        <tr><td><span class="code-tag">material_id</span></td><td>INT</td><td>NO</td><td>FK &rarr; raw_material</td><td>Raw material deducted from inventory stock.</td></tr>
        <tr><td><span class="code-tag">quantity_issued</span></td><td>NUMERIC(10,2)</td><td>NO</td><td>CHECK &gt; 0.00</td><td>Quantity of material delivered to the workshop floor.</td></tr>
        <tr><td><span class="code-tag">issue_date</span></td><td>DATE</td><td>NO</td><td>DEFAULT CURRENT_DATE</td><td>Date when material transfer occurred.</td></tr>
        <tr><td><span class="code-tag">recorded_by</span></td><td>VARCHAR(100)</td><td>NO</td><td>-</td><td>Name of the manager who approved warehouse dispatch.</td></tr>
    </tbody>
</table>

<h3>8.6 <span class="code-tag">public.prod_productionmonitoring</span> (Shop-Floor Milestones)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">monitoring_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique workshop monitoring record identifier.</td></tr>
        <tr><td><span class="code-tag">order_id</span></td><td>INT</td><td>NO</td><td>UNIQUE, FK &rarr; prod_productionorder</td><td>1-to-1 link to active production order.</td></tr>
        <tr><td><span class="code-tag">progress</span></td><td>NUMERIC(5,2)</td><td>NO</td><td>CHECK 0.0 &le; x &le; 100.0</td><td>Current assembly milestone: 25%, 50%, 75%, 90%, 100%.</td></tr>
        <tr><td><span class="code-tag">rework_count</span></td><td>INT</td><td>NO</td><td>DEFAULT 0</td><td>Number of times defects were sent back for workshop touch-up.</td></tr>
        <tr><td><span class="code-tag">current_stage</span></td><td>VARCHAR(100)</td><td>YES</td><td>-</td><td>Workstation label (Cutting &amp; Sizing, Joinery, Sanding, QA).</td></tr>
        <tr><td><span class="code-tag">operator_notes</span></td><td>TEXT</td><td>YES</td><td>-</td><td>Floor remarks logged by carpenters.</td></tr>
        <tr><td><span class="code-tag">start_date</span></td><td>DATE</td><td>YES</td><td>DEFAULT CURRENT_DATE</td><td>Date when physical work commenced.</td></tr>
        <tr><td><span class="code-tag">completion_date</span></td><td>DATE</td><td>YES</td><td>-</td><td>Date when batch cleared 100% and passed QA inspection.</td></tr>
    </tbody>
</table>

<h3>8.7 <span class="code-tag">public.prod_attachments</span> (Cloud Photo Proofs)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">attachment_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique photo proof identifier.</td></tr>
        <tr><td><span class="code-tag">monitoring_id</span></td><td>INT</td><td>NO</td><td>FK &rarr; prod_productionmonitoring</td><td>Monitoring entry substantiated by the photo.</td></tr>
        <tr><td><span class="code-tag">file_url</span></td><td>TEXT</td><td>NO</td><td>NOT NULL</td><td>Public CDN link to photo stored in Supabase Storage.</td></tr>
        <tr><td><span class="code-tag">file_name</span></td><td>VARCHAR(255)</td><td>YES</td><td>-</td><td>Original device file name.</td></tr>
        <tr><td><span class="code-tag">created_at</span></td><td>TIMESTAMP</td><td>NO</td><td>DEFAULT CURRENT_TIMESTAMP</td><td>Date and time when the photo was uploaded.</td></tr>
    </tbody>
</table>

<h3>8.8 <span class="code-tag">public.prod_productionoutput</span> (QA Inspection Log)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">output_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique quality inspection report identifier (#QA-1).</td></tr>
        <tr><td><span class="code-tag">order_id</span></td><td>INT</td><td>NO</td><td>FK &rarr; prod_productionorder</td><td>Order evaluated by Quality Inspector.</td></tr>
        <tr><td><span class="code-tag">quantity</span></td><td>INT</td><td>NO</td><td>CHECK &ge; 0</td><td>Number of finished units inspected.</td></tr>
        <tr><td><span class="code-tag">quality_status</span></td><td>VARCHAR(30)</td><td>NO</td><td>NOT NULL</td><td>Inspection decision: Passed, Rework Required, or Scrapped.</td></tr>
        <tr><td><span class="code-tag">inspection_date</span></td><td>DATE</td><td>NO</td><td>DEFAULT CURRENT_DATE</td><td>Date when inspection took place.</td></tr>
        <tr><td><span class="code-tag">recorded_by</span></td><td>VARCHAR(100)</td><td>NO</td><td>-</td><td>Name of the Quality Inspector.</td></tr>
        <tr><td><span class="code-tag">reason</span></td><td>TEXT</td><td>YES</td><td>-</td><td>Remarks, defect description, or sign-off approval notes.</td></tr>
    </tbody>
</table>

<h3>8.9 <span class="code-tag">public.prod_productioncost</span> (Job Manufacturing Cost Sheet)</h3>
<table>
    <thead>
        <tr><th>Column Name</th><th>Type</th><th>Null?</th><th>Constraint</th><th>Description / Real-World Purpose</th></tr>
    </thead>
    <tbody>
        <tr><td><span class="code-tag">cost_id</span></td><td>SERIAL</td><td>NO</td><td>PRIMARY KEY</td><td>Unique job cost sheet reference (#CST-1).</td></tr>
        <tr><td><span class="code-tag">order_id</span></td><td>INT</td><td>NO</td><td>UNIQUE, FK &rarr; prod_productionorder</td><td>1-to-1 link ensuring strict job costing integrity.</td></tr>
        <tr><td><span class="code-tag">material_cost</span></td><td>NUMERIC(12,2)</td><td>NO</td><td>CHECK &ge; 0.00</td><td>Actual direct material expense calculated from issuances.</td></tr>
        <tr><td><span class="code-tag">labor_cost</span></td><td>NUMERIC(12,2)</td><td>NO</td><td>CHECK &ge; 0.00</td><td>Direct workshop carpentry labor allocated to the batch.</td></tr>
        <tr><td><span class="code-tag">overhead_cost</span></td><td>NUMERIC(12,2)</td><td>NO</td><td>CHECK &ge; 0.00</td><td>Standard 15% factory overhead (0.15 &times; (Material + Labor)).</td></tr>
        <tr><td><span class="code-tag">total_cost</span></td><td>NUMERIC(12,2)</td><td>NO</td><td>CHECK &ge; 0.00</td><td>Total manufacturing investment (Material + Labor + Overhead).</td></tr>
        <tr><td><span class="code-tag">cost_date</span></td><td>DATE</td><td>NO</td><td>DEFAULT CURRENT_DATE</td><td>Date when the cost sheet was calculated and finalized.</td></tr>
    </tbody>
</table>

</body>
</html>
"""

html_path = r"D:\Files\Documents\MyWorks\production-FMS\velmora_doc.html"
pdf_path = r"D:\Files\Documents\MyWorks\production-FMS\Velmora_Production_ERP_Documentation.pdf"
artifact_pdf = r"C:\Users\Serendipity\.gemini\antigravity\brain\0322aa40-508d-42e7-9cb2-ccc81b783e13\Velmora_Production_ERP_Documentation.pdf"

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(chrome_exe):
    chrome_exe = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

cmd = [
    chrome_exe,
    "--headless=new",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={pdf_path}",
    f"file:///{html_path.replace(os.sep, '/')}"
]

res = subprocess.run(cmd, capture_output=True, text=True)
if os.path.exists(pdf_path):
    shutil.copy2(pdf_path, artifact_pdf)
    print("PDF generated successfully:", os.path.getsize(pdf_path), "bytes")
else:
    print("Error generating PDF:", res.stderr)

