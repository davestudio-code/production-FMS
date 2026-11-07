import os
import subprocess
import shutil

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Velmora Production-FMS &middot; Full Source Code Explanation</title>
<style>
    @page {
        size: A4;
        margin: 16mm 14mm 18mm 14mm;
        @bottom-right {
            content: "Page " counter(page);
            font-size: 8pt;
            color: #6a737d;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        @bottom-left {
            content: "Velmora Co. Production-FMS &middot; Technical Architecture & Function Reference";
            font-size: 8pt;
            color: #6a737d;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
    }
    *, *:before, *:after { box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-size: 9.5pt;
        line-height: 1.5;
        color: #1e2417;
        background: #ffffff;
        margin: 0;
        padding: 0;
    }
    .cover {
        padding: 35px 0 25px;
        border-bottom: 3px solid #526638;
        margin-bottom: 24px;
        page-break-after: avoid;
    }
    .brand-eyebrow {
        font-size: 10pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #526638;
        margin-bottom: 6px;
    }
    h1 {
        font-size: 22pt;
        font-weight: 800;
        color: #161e10;
        margin: 0 0 8px 0;
        letter-spacing: -0.5px;
    }
    .lead {
        font-size: 11pt;
        color: #4b583e;
        margin: 0 0 16px 0;
        line-height: 1.4;
    }
    .meta-box {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        background: #fbf9f4;
        border: 1px solid #e2dac9;
        border-radius: 6px;
        padding: 10px 14px;
        font-size: 8.5pt;
    }
    .meta-box b {
        display: block;
        color: #526638;
        font-size: 7.5pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    h2 {
        font-size: 13.5pt;
        font-weight: 700;
        color: #161e10;
        border-bottom: 1.5px solid #dcd3bd;
        padding-bottom: 4px;
        margin: 24px 0 12px 0;
        page-break-after: avoid;
    }
    h3 {
        font-size: 10.5pt;
        font-weight: 700;
        color: #2e3a1f;
        margin: 16px 0 6px 0;
        page-break-after: avoid;
    }
    p { margin: 0 0 8px 0; }
    .file-card {
        background: #ffffff;
        border: 1px solid #dcd3bd;
        border-left: 4px solid #526638;
        border-radius: 4px;
        padding: 10px 12px;
        margin-bottom: 14px;
        page-break-inside: avoid;
    }
    .file-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        border-bottom: 1px dashed #e2dac9;
        padding-bottom: 5px;
        margin-bottom: 8px;
    }
    .file-name {
        font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 10.5pt;
        font-weight: 700;
        color: #161e10;
    }
    .file-role {
        font-size: 8.5pt;
        font-weight: 600;
        color: #7d6b49;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .fn-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 8.5pt;
        margin-top: 6px;
    }
    .fn-table th {
        background: #f4efe2;
        color: #2e3a1f;
        font-weight: 700;
        text-align: left;
        padding: 5px 8px;
        border: 1px solid #dcd3bd;
    }
    .fn-table td {
        padding: 5px 8px;
        border: 1px solid #e7dfce;
        vertical-align: top;
    }
    .fn-name {
        font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
        font-weight: 700;
        color: #204018;
        font-size: 8pt;
    }
    .fn-sig {
        font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
        color: #66754c;
        font-size: 7.5pt;
        display: block;
        margin-top: 1px;
    }
    .tag {
        display: inline-block;
        padding: 1px 5px;
        border-radius: 3px;
        font-size: 7pt;
        font-weight: 700;
        text-transform: uppercase;
        margin-right: 4px;
    }
    .tag-func { background: #e8f0dc; color: #3b5025; }
    .tag-method { background: #e0ecf8; color: #1e3a5f; }
    .tag-class { background: #fbebd8; color: #7a4612; }
    .tag-route { background: #f5e2df; color: #7a2b20; }
    .callout {
        background: #faf7ef;
        border-left: 3px solid #8e622a;
        padding: 8px 12px;
        margin: 10px 0;
        font-size: 8.5pt;
        color: #4a3e29;
    }
    .callout b { color: #2e3a1f; }
    .diagram-box {
        background: #fbf9f4;
        border: 1px solid #dcd3bd;
        border-radius: 6px;
        padding: 12px;
        margin: 12px 0;
        font-family: SFMono-Regular, Consolas, monospace;
        font-size: 8pt;
        line-height: 1.4;
        color: #2e3a1f;
    }
    .page-break { page-break-after: always; }
</style>
</head>
<body>

<div class="cover">
    <div class="brand-eyebrow">Velmora Co. Enterprise Suite &middot; Team 3 Engineering</div>
    <h1>Velmora Production-FMS Architecture Reference</h1>
    <div class="lead">Complete Function-by-Function Source Code &amp; Business Logic Manual for Developers</div>
    <div class="meta-box">
        <div class="meta-item"><b>Target Stack</b>Python 3.11 / Flask / PostgreSQL</div>
        <div class="meta-item"><b>Database</b>Supabase / psycopg2 Pool</div>
        <div class="meta-item"><b>Module Scope</b>Production &amp; Manufacturing (FMS)</div>
        <div class="meta-item"><b>Documentation Status</b>Production-Verified (001-005 Schema)</div>
    </div>
</div>

<h2>1. Executive Architecture Overview</h2>
<p>
    The Velmora Production-FMS module automates the entire manufacturing workflow for bespoke furniture production. It enforces a strict, unidirectional 6-stage lifecycle that prevents material waste, maintains live inventory synchronization, tracks workshop craftsmanship, and accurately accounts for direct manufacturing costs.
</p>

<div class="diagram-box">
[1. Product Master &amp; BOM]  &rarr;  Defines furniture specifications and raw material recipes (with waste factor).
           &darr;
[2. Production Planning]    &rarr;  Schedules target start/due dates and binds the batch to workshop craftsmen.
           &darr;
[3. Material Readiness]     &rarr;  Compares required components with warehouse stock; prevents releases on shortage.
           &darr;
[4. Material Issuance]      &rarr;  Deducts physical inventory from prod_material and auto-initializes workshop tracking at 0%.
           &darr;
[5. Workshop Monitoring]    &rarr;  Workers progress batches through 0% &rarr; 25% &rarr; 50% &rarr; 75% &rarr; 90% with proof photos.
           &darr;
[6. Quality Inspection]     &rarr;  Passed units credit to Finished Goods. Defective units trigger Rework (75% rollback, max 2).
           &darr;
[7. Job Costing &amp; Reports]  &rarr;  Aggregates actual material cost + direct carpentry labor. Overhead managed by Sales.
</div>

<h2>2. Application Core &amp; Database Layer</h2>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">app.py</span>
        <span class="file-role">Application Factory &amp; Root Entry Point</span>
    </div>
    <p style="font-size: 8.5pt;">Initializes the Flask application, registers the production Blueprint under <code>/production</code>, and enforces request-level database cleanup.</p>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Function / Handler</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">root</span></td>
                <td><span class="fn-sig">root() &rarr; Response</span></td>
                <td>Catches incoming requests to the domain root (<code>/</code>) and immediately issues an HTTP 302 redirect to the production home route (<code>/production/</code>).</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">closeRequestContextDb</span></td>
                <td><span class="fn-sig">closeRequestContextDb(error=None)</span></td>
                <td>Decorated with <code>@app.teardown_appcontext</code>. Guarantees that any database connection attached to Flask's <code>g.dbConnection</code> during request handling is safely returned to the pool, automatically rolling back uncommitted transactions if an unhandled exception occurred.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/db.py</span>
        <span class="file-role">PostgreSQL Threaded Connection Pool &amp; Transactions</span>
    </div>
    <p style="font-size: 8.5pt;">Manages persistent SSL connections to Supabase PostgreSQL using <code>psycopg2.pool.ThreadedConnectionPool</code> and provides transaction context managers.</p>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Function</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">getPool</span></td>
                <td><span class="fn-sig">getPool() &rarr; ThreadedConnectionPool</span></td>
                <td>Initializes a thread-safe singleton connection pool (min 1, max 10 connections) configured with <code>RealDictCursor</code> so query results can be indexed like Python dictionaries. Enforces <code>sslmode=require</code> for Supabase cloud security.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">checkoutConnection</span></td>
                <td><span class="fn-sig">checkoutConnection() &rarr; connection</span></td>
                <td>Pulls an active socket connection from the pool. If a connection was closed by the remote server during idle periods, safely purges it and checks out a fresh connection.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">releaseConnection</span></td>
                <td><span class="fn-sig">releaseConnection(conn, error=False)</span></td>
                <td>Returns a connection back to the pool. If <code>error=True</code>, issues a rollback to ensure no partial state leaks into future requests; otherwise commits and returns.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">openTransaction</span></td>
                <td><span class="fn-sig">openTransaction(externalConnection=None)</span></td>
                <td>Context manager (<code>with openTransaction() as conn:</code>). Enables connection reuse across multiple domain models inside a single web request using Flask's <code>g.dbConnection</code>. Handles automatic commit on block completion and rollback on exception.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/cache.py</span>
        <span class="file-role">Request &amp; In-Memory Data Caching</span>
    </div>
    <p style="font-size: 8.5pt;">Provides light in-memory caching to eliminate redundant database roundtrips for semi-static reference data.</p>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Function</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">getCached / setCached</span></td>
                <td><span class="fn-sig">getCached(key), setCached(key, val)</span></td>
                <td>Retrieves or stores timestamped cached query objects in memory.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">invalidateKeys / clearAllCache</span></td>
                <td><span class="fn-sig">invalidateKeys(), clearAllCache()</span></td>
                <td>Invalidates specific cache namespaces (e.g., when new furniture is created) or flushes the cache entirely.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="page-break"></div>

<h2>3. Security &amp; Enterprise Authentication Layer</h2>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/security.py</span>
        <span class="file-role">Brute-Force Rate Limiting &amp; 24-Hour IP Ban</span>
    </div>
    <p style="font-size: 8.5pt;">Protects the login route from credential stuffing without altering any Supabase SQL schemas. Persists state thread-safely in <code>instance/login_ratelimit.json</code>.</p>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Function</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">get_client_ip</span></td>
                <td><span class="fn-sig">get_client_ip() &rarr; str</span></td>
                <td>Extracts the client's actual remote IP address, inspecting <code>X-Forwarded-For</code> (first proxy IP) before falling back to <code>remote_addr</code>.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">check_ip_security</span></td>
                <td><span class="fn-sig">check_ip_security(ip) &rarr; (bool, str, int)</span></td>
                <td>Evaluates whether the client IP is blocked. Returns <code>(is_allowed, reason, seconds_remaining)</code>. Blocks users if under an active 60s cooldown or 24-hour ban.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">record_failed_login</span></td>
                <td><span class="fn-sig">record_failed_login(ip) &rarr; (bool, str, int)</span></td>
                <td>Increments the failed login count for an IP. Reaching 5 failures triggers a 60-second block; accumulating 3 consecutive blocks escalates to a 24-hour IP ban.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">record_successful_login</span></td>
                <td><span class="fn-sig">record_successful_login(ip)</span></td>
                <td>Resets failed login attempt counts upon valid authentication, leaving legitimate users unencumbered.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/auth.py</span>
        <span class="file-role">Supabase Auth, Auto-Provisioning &amp; Role Access Control</span>
    </div>
    <p style="font-size: 8.5pt;">Manages employee role validation, Supabase <code>auth.users</code> bcrypt authentication, auto-provisioning, profile editing, and cooldown password resets.</p>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Function</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">is_authorized_production_employee</span></td>
                <td><span class="fn-sig">(dept_id, pos_id, is_active=True) &rarr; bool</span></td>
                <td>Validates that an employee belongs to Department 6 (Production) and Position 6 (Manager) or 2 (Production Staff) with an active status.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">authenticate_credentials</span></td>
                <td><span class="fn-sig">authenticate_credentials(email, pwd) &rarr; (dict, str)</span></td>
                <td>Authenticates email/password using <code>extensions.crypt(%s, a.encrypted_password)</code>. Features an <b>Auto-Provisioning Engine</b>: if an active employee exists in <code>public.employee</code> but has no login account yet, entering initial password <code>velmora123</code> automatically creates their <code>auth.users</code> record, hashes the password, and links permissions.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">_sync_employee_auth_links</span></td>
                <td><span class="fn-sig">(cur, emp_id, auth_uid, pos_id) &rarr; str</span></td>
                <td>Ensures consistent foreign key links across <code>public.employee_auth</code>, <code>public.users</code>, and <code>public.employee_module_access</code> (setting access level to <code>manager</code> or <code>staff</code>).</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">sync_and_verify_session</span></td>
                <td><span class="fn-sig">sync_and_verify_session() &rarr; bool</span></td>
                <td>Runs on every page request to verify that the logged-in employee remains active in the database, automatically kicking deactivated accounts.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">update_employee_profile</span></td>
                <td><span class="fn-sig">(emp_id, first_name, last_name, phone) &rarr; (bool, str)</span></td>
                <td>Updates employee name and phone number in <code>public.employee</code>, validating name lengths and phone formatting.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">change_employee_password</span></td>
                <td><span class="fn-sig">(emp_id, cur_pwd, new_pwd) &rarr; (bool, str)</span></td>
                <td>Validates current password, enforces minimum 8 characters with letters/numbers, checks a 30-day cooldown period, and updates the bcrypt hash in <code>auth.users</code>.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">login_required / manager_required</span></td>
                <td><span class="fn-sig">decorator(view_func) &rarr; view_func</span></td>
                <td>Flask route decorators. <code>login_required</code> ensures valid session; <code>manager_required</code> restricts executive operations (approvals, costing, releases) to Managers (pos 6).</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/integration.py</span>
        <span class="file-role">Cross-Module Integration Handlers</span>
    </div>
    <p style="font-size: 8.5pt;">Connects the Production module with Team 2 Inventory and Team 1 Finance.</p>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Function</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">get_material_stock / deduct_material_stock</span></td>
                <td><span class="fn-sig">(materialID, qty, conn)</span></td>
                <td>Queries or deducts raw material quantities from <code>prod_material</code>, safeguarding against negative balances.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">add_finished_goods_stock</span></td>
                <td><span class="fn-sig">(furnitureID, qty, conn)</span></td>
                <td>Credits passed production units to the finished goods inventory upon QA inspection completion.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">get_warehouse_stockouts</span></td>
                <td><span class="fn-sig">get_warehouse_stockouts(conn) &rarr; list</span></td>
                <td>Scans warehouse stock for items below reorder thresholds and alerts production managers.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="page-break"></div>

<h2>4. Domain Models &amp; Business Logic</h2>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/models/furniture.py</span>
        <span class="file-role">Finished Goods &amp; Product Master Catalog</span>
    </div>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Class &amp; Methods</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">Furniture</span></td>
                <td><span class="fn-sig">Furniture(data_dict)</span></td>
                <td>Data entity wrapping catalog products (<code>furniture_id</code>, <code>furniture_name</code>, <code>furniture_type</code>, <code>selling_price</code>).</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">getAll</span></td>
                <td><span class="fn-sig">getAll(searchQuery, category, conn)</span></td>
                <td>Returns all catalog items with their computed BOM cost and category filters.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">getByID / existsByName</span></td>
                <td><span class="fn-sig">getByID(id, conn), existsByName(name, excludeID, conn)</span></td>
                <td>Retrieves product by ID and prevents duplicate naming across the catalog.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">addFurniture / updateFurniture</span></td>
                <td><span class="fn-sig">(name, type, price, conn)</span></td>
                <td>Creates or modifies furniture catalog entries with transaction safety.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">canDelete / deleteFurniture</span></td>
                <td><span class="fn-sig">canDelete(id, conn) &rarr; (bool, str)</span></td>
                <td>Enforces referential integrity: blocks deletion if furniture has active BOM items, orders, or output history.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/models/billofmaterials.py &amp; bomitem.py</span>
        <span class="file-role">Engineering Bill of Materials &amp; Component Costing</span>
    </div>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Class &amp; Methods</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">BillOfMaterials</span></td>
                <td><span class="fn-sig">BillOfMaterials(data_dict)</span></td>
                <td>BOM header entity linking a furniture piece to its raw material component recipe.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">getByFurnitureID</span></td>
                <td><span class="fn-sig">(furnitureID, autoCreate=True, conn)</span></td>
                <td>Fetches the active BOM header for a furniture piece, auto-creating a Version 1 record if none exists.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">getItems / addMaterial / removeMaterial</span></td>
                <td><span class="fn-sig">(materialID, qtyRequired, conn)</span></td>
                <td>Manages BOM line items (adding raw materials with required quantities, removing components).</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">calculateRequirements</span></td>
                <td><span class="fn-sig">(plannedQuantity, conn) &rarr; list</span></td>
                <td>Multiplies BOM required quantities by planned batch units to forecast material requirements.</td>
            </tr>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">BOMItem</span></td>
                <td><span class="fn-sig">calculateQuantity(plannedQuantity)</span></td>
                <td>Line-item entity representing a required material, unit cost, and standard scrap allowance.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/models/material.py &amp; materialissuance.py</span>
        <span class="file-role">Raw Materials &amp; Floor Stock Issuance</span>
    </div>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Class &amp; Methods</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">Material</span></td>
                <td><span class="fn-sig">getAll(conn), getByID(id, conn)</span></td>
                <td>Entity wrapping <code>prod_material</code>, returning stock levels, unit costs, and categories (Lumber, Hardware, Finishing).</td>
            </tr>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">MaterialIssuance</span></td>
                <td><span class="fn-sig">recordIssuance(orderID, matID, qty, user, conn)</span></td>
                <td>Creates an official warehouse dispatch record in <code>prod_materialissuance</code> when materials leave inventory for the floor.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">getAll / getByOrderID</span></td>
                <td><span class="fn-sig">getByOrderID(orderID, conn) &rarr; list</span></td>
                <td>Returns all historical material dispatch logs for audit reports and actual cost calculations.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/models/productionorder.py</span>
        <span class="file-role">Production Orders, Scheduling &amp; Lifecycle State Machine</span>
    </div>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Class &amp; Methods</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">ProductionOrder</span></td>
                <td><span class="fn-sig">ProductionOrder(data_dict)</span></td>
                <td>Master work order entity (<code>status: Draft, Released, In Progress, Completed, Cancelled</code>).</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">scheduleHealth</span></td>
                <td><span class="fn-sig">scheduleHealth &rarr; str</span></td>
                <td>Calculates real-time schedule status: <code>Overdue</code> (past due date), <code>Due Soon</code> (due within 3 days), or <code>On Track</code>.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">createOrder</span></td>
                <td><span class="fn-sig">(furnitureID, qty, start, due, purpose, conn)</span></td>
                <td>Inserts a new Draft production batch work order into <code>prod_productionorder</code>.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">updateStatus</span></td>
                <td><span class="fn-sig">(orderID, newStatus, conn)</span></td>
                <td>Advances order through lifecycle transitions (e.g. Draft &rarr; Released &rarr; In Progress).</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">updateSchedule</span></td>
                <td><span class="fn-sig">(orderID, start, due, assignedTo, updateAssignment, conn)</span></td>
                <td>Updates production calendar timeline dates and assigns a craftsman employee from the staff roster.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">canDelete / deleteOrder</span></td>
                <td><span class="fn-sig">canDelete(orderID, conn) &rarr; (bool, str)</span></td>
                <td>Restricts deletion: only Draft orders with zero material dispatches can be safely deleted.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="page-break"></div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/models/monitoring.py &amp; workflow.py</span>
        <span class="file-role">Workshop Floor Assembly Stages &amp; Staff Workflow</span>
    </div>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Class &amp; Methods</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">ProductionMonitoring</span></td>
                <td><span class="fn-sig">updateProgress(monitoringID, progressVal, conn)</span></td>
                <td>Advances workshop assembly stages: <code>0% (Not Started) &rarr; 25% (Cutting) &rarr; 50% (Joinery) &rarr; 75% (Finishing) &rarr; 90% (Ready for QA)</code>.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">updateProgressAndRework</span></td>
                <td><span class="fn-sig">(monitoringID, progressVal, reworkCount, conn)</span></td>
                <td>Rolls back progress to 75% when QA fails with Rework status, incrementing the rework counter (max 2).</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">isValidActiveProdStaff</span></td>
                <td><span class="fn-sig">(employeeID, conn) &rarr; bool</span></td>
                <td>Verifies that a selected craftsman is an active employee in Department 6, Position 2.</td>
            </tr>
            <tr>
                <td><span class="tag tag-func">func</span><span class="fn-name">getProductionStaffRoster</span></td>
                <td><span class="fn-sig">getProductionStaffRoster(conn) &rarr; list</span></td>
                <td>Returns all workshop staff with their active order count, allowing managers to balance workload.</td>
            </tr>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">ProductionAttachment</span></td>
                <td><span class="fn-sig">createAttachment(orderID, stage, note, url, user, conn)</span></td>
                <td>Logs image proofs and completion notes for each completed assembly stage.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/models/productionoutput.py</span>
        <span class="file-role">Quality Assurance (QA) Inspection &amp; Defect Handling</span>
    </div>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Class &amp; Methods</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">ProductionOutput</span></td>
                <td><span class="fn-sig">recordOutput(...)</span></td>
                <td>Records official inspection results: <code>Passed</code> (credits finished goods, marks order 100% Completed), <code>Rework</code> (returns to 75%), or <code>Failed</code> (scrapped units).</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">getOrderInspectionSummary</span></td>
                <td><span class="fn-sig">(orderID, conn) &rarr; dict</span></td>
                <td>Aggregates cumulative passed vs scrapped units for an order to calculate yield rates.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/models/productioncost.py</span>
        <span class="file-role">Job Order Costing (Actual Materials + Direct Labor)</span>
    </div>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Class &amp; Methods</th><th style="width: 25%;">Signature</th><th>Description &amp; Engineering Purpose</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-class">class</span><span class="fn-name">ProductionCost</span></td>
                <td><span class="fn-sig">ProductionCost(data_dict)</span></td>
                <td>Cost sheet entity wrapping <code>prod_productioncost</code>. Tracks material cost, direct labor, and finished unit costs.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">calculateActualMaterialCost</span></td>
                <td><span class="fn-sig">(orderID, conn) &rarr; Decimal</span></td>
                <td>Sums the exact monetary value of raw materials issued from inventory: <code>&sum;(quantity_issued &times; unit_cost)</code>.</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">calculateCostPerGoodUnit</span></td>
                <td><span class="fn-sig">(orderID, totalCost, conn) &rarr; Decimal</span></td>
                <td>Divides total batch cost by passed QA units: <code>total_cost / passed_units</code> (Finished Unit Cost).</td>
            </tr>
            <tr>
                <td><span class="tag tag-method">method</span><span class="fn-name">saveCost</span></td>
                <td><span class="fn-sig">(orderID, materialCost, laborCost, overheadCost=0.00, conn)</span></td>
                <td>Inserts or updates the batch cost sheet. Enforces <code>overhead_cost = 0.00</code>, ensuring overhead is handled by Sales.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="page-break"></div>

<h2>5. HTTP Controller &amp; Route Endpoints (routes.py)</h2>

<div class="file-card">
    <div class="file-header">
        <span class="file-name">production/routes.py</span>
        <span class="file-role">HTTP Request Endpoints &amp; Presentation Logic</span>
    </div>
    <table class="fn-table">
        <thead>
            <tr><th style="width: 32%;">Endpoint &amp; Methods</th><th style="width: 22%;">URL Pattern</th><th>Description &amp; Controller Actions</th></tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">login / logout</span></td>
                <td><span class="fn-sig">/login, /logout</span></td>
                <td>Handles session login, invokes <code>check_ip_security</code> and <code>record_failed_login</code>, clears session cookies upon sign out.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">updateAccountProfile</span></td>
                <td><span class="fn-sig">/account/update-profile</span></td>
                <td>POST endpoint updating name and phone number for the authenticated operator.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">changeAccountPassword</span></td>
                <td><span class="fn-sig">/account/change-password</span></td>
                <td>POST endpoint validating current password and updating the bcrypt hash with a 30-day cooldown.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">index</span></td>
                <td><span class="fn-sig">/ (GET)</span></td>
                <td>Master Executive Dashboard: renders active work order counts, stockout warnings, and 4-week production output bar charts.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">furnitureList / addFurniture / edit / delete</span></td>
                <td><span class="fn-sig">/furniture, /furniture/*</span></td>
                <td>Product Master catalog controller: manages furniture designs, categories, and target prices.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">materialList</span></td>
                <td><span class="fn-sig">/materials (GET)</span></td>
                <td>Raw materials inventory viewer: displays stock on hand, units, categories, and low-stock alerts.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">bomList / addBomItem / removeBomItem</span></td>
                <td><span class="fn-sig">/bom, /bom/add-item</span></td>
                <td>Engineering BOM editor: dynamically calculates unit material costs and updates catalog baseline costs.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">orderList / orderDetail / createOrder / delete</span></td>
                <td><span class="fn-sig">/orders, /orders/&lt;id&gt;</span></td>
                <td>Work Order controller: tracks order registry, planned batch quantities, BOM readiness, and deletion safeguards.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">planningList / updateOrderSchedule</span></td>
                <td><span class="fn-sig">/planning</span></td>
                <td>Production Planning board: updates start dates, due dates, and binds orders to workshop craftsmen.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">requirementList / releaseOrder</span></td>
                <td><span class="fn-sig">/requirement</span></td>
                <td>Material readiness checker: validates component stock and advances orders from Draft to Released.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">issuanceList / issueOrderMaterials</span></td>
                <td><span class="fn-sig">/issuance</span></td>
                <td>Warehouse dispatch: deducts stock from inventory, advances order to In Progress, and auto-starts monitoring.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">monitoringList / updateMonitoringProgress</span></td>
                <td><span class="fn-sig">/monitoring</span></td>
                <td>Workshop floor tracker: workers update assembly stages (0% &rarr; 90%) and upload completion photo proofs.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">finishedGoodsList / recordInspection</span></td>
                <td><span class="fn-sig">/finished-goods</span></td>
                <td>Quality Inspection station: records Passed units (100% Complete), Rework (75% rollback), or Scrapped.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">costingList / saveOrderCost</span></td>
                <td><span class="fn-sig">/costing</span></td>
                <td>Production Costing sheet: logs actual direct labor, calculates finished unit cost, and saves cost sheets.</td>
            </tr>
            <tr>
                <td><span class="tag tag-route">route</span><span class="fn-name">reportView</span></td>
                <td><span class="fn-sig">/reports (GET)</span></td>
                <td>Executive Reports: batch cost summary, raw material consumption logs, and printable executive sign-off sheets.</td>
            </tr>
        </tbody>
    </table>
</div>

<div class="callout">
    <b>Developer Summary:</b> Every database mutation in this application runs inside an atomic transaction managed by <code>db.openTransaction()</code>. If any server error or database disconnection occurs during execution, PostgreSQL safely rolls back all operations, guaranteeing zero corrupted or orphaned records.
</div>

</body>
</html>
"""

html_path = r"D:\Files\Documents\MyWorks\production-FMS\velmora_code_explanation.html"
pdf_path = r"D:\Files\Documents\MyWorks\production-FMS\Velmora_Production_ERP_Code_Explanation.pdf"
artifact_pdf = r"C:\Users\Serendipity\.gemini\antigravity\brain\0322aa40-508d-42e7-9cb2-ccc81b783e13\Velmora_Production_ERP_Code_Explanation.pdf"

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
    print("SUCCESS: PDF generated and copied to artifact directory!")
    print("File size:", os.path.getsize(pdf_path), "bytes")
else:
    print("ERROR generating PDF:", res.stderr)

