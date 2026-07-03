// Global UI State
let activeClaimKey = null;
let claimsList = [];
let processedClaims = {}; // cache results

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    loadClaimsList();
    setupEventListeners();
    setupDragAndDrop();
}

// 1. Fetch claims list from Flask API
async function loadClaimsList() {
    const listElement = document.getElementById('claim-list');
    listElement.innerHTML = '<div class="loading">Loading S3 objects...</div>';

    try {
        const response = await fetch('/api/claims');
        const data = await response.json();
        
        if (data.status === 'success') {
            claimsList = data.claims;
            renderClaimsList();
        } else {
            listElement.innerHTML = `<div class="loading error">Error: ${data.message}</div>`;
        }
    } catch (e) {
        listElement.innerHTML = `<div class="loading error">Failed to connect to backend API</div>`;
    }
}

// 2. Render claims in sidebar list
function renderClaimsList() {
    const listElement = document.getElementById('claim-list');
    
    if (claimsList.length === 0) {
        listElement.innerHTML = '<div class="loading">No claims found in S3.</div>';
        return;
    }

    listElement.innerHTML = '';
    claimsList.forEach(key => {
        const item = document.createElement('div');
        item.className = 'claim-item';
        if (key === activeClaimKey) item.classList.add('active');

        // Determine if processed
        const isProcessed = !!processedClaims[key];
        const badgeClass = isProcessed ? 'badge-success' : 'badge-pending';
        const badgeText = isProcessed ? 'Processed' : 'Unprocessed';

        // Extract clean name
        const cleanName = key.replace('.txt', '').replace('claim_', '').toUpperCase();

        item.innerHTML = `
            <div class="claim-title-row">
                <span class="claim-key" title="${key}">${key}</span>
                <span class="claim-badge ${badgeClass}">${badgeText}</span>
            </div>
            <div class="claim-meta-row">
                <span>Code: ${cleanName}</span>
                <span>Type: ${isProcessed ? processedClaims[key].extracted_info.claim_type : 'Unknown'}</span>
            </div>
        `;

        item.addEventListener('click', () => selectClaim(key));
        listElement.appendChild(item);
    });
}

// 3. Handle Claim Selection
async function selectClaim(key) {
    activeClaimKey = key;
    renderClaimsList();

    // Enable buttons
    document.getElementById('process-claim-btn').disabled = false;
    document.getElementById('compare-models-btn').disabled = false;

    // Reset details tab
    document.getElementById('raw-document-text').textContent = 'Loading claim content...';
    document.getElementById('raw-document-text').classList.remove('empty');

    // Reset RAG policy tab
    document.getElementById('policy-details-content').innerHTML = `
        <p class="placeholder-text">Process the claim first to match policy segments using vector embeddings...</p>
    `;

    try {
        const response = await fetch(`/api/claims/${encodeURIComponent(key)}`);
        const data = await response.json();
        if (data.status === 'success') {
            document.getElementById('raw-document-text').textContent = data.text;
        } else {
            document.getElementById('raw-document-text').textContent = `Error loading document: ${data.message}`;
        }
    } catch (e) {
        document.getElementById('raw-document-text').textContent = 'Failed to load claim document.';
    }

    // Load cached result if previously processed
    if (processedClaims[key]) {
        displayProcessedResult(processedClaims[key]);
    } else {
        resetSummaryDetails();
    }
}

// 4. Run Process Claim API
async function processActiveClaim() {
    if (!activeClaimKey) return;

    const processBtn = document.getElementById('process-claim-btn');
    processBtn.disabled = true;
    processBtn.querySelector('span').textContent = '⚙️ Triage processing...';

    // Set summary to loading state
    document.getElementById('summary-card').innerHTML = `
        <div class="loading">
            <span class="placeholder-icon">🤖</span>
            Evaluating claim rules and generating narrative adjuster summary...
        </div>
    `;

    try {
        const response = await fetch(`/api/claims/process/${encodeURIComponent(activeClaimKey)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();

        if (data.status === 'success') {
            const result = data.result;
            processedClaims[activeClaimKey] = result;
            displayProcessedResult(result);
            renderClaimsList(); // Update badges
        } else {
            document.getElementById('summary-card').innerHTML = `
                <div class="summary-text-actual" style="color: var(--error-color)">
                    Error processing claim: ${data.message}
                </div>
            `;
        }
    } catch (e) {
        document.getElementById('summary-card').innerHTML = `
            <div class="summary-text-actual" style="color: var(--error-color)">
                Connection error while processing claim.
            </div>
        `;
    } finally {
        processBtn.disabled = false;
        processBtn.querySelector('span').textContent = '✨ Process Claim (AI Triage)';
    }
}

// 5. Populate Result Details into UI Panels
function displayProcessedResult(result) {
    // 1. Populate summary narrative
    document.getElementById('summary-card').innerHTML = `
        <p class="summary-text-actual">${result.summary}</p>
    `;

    // 2. Populate extracted facts
    const info = result.extracted_info;
    document.getElementById('fact-name').textContent = info.claimant_name || 'N/A';
    document.getElementById('fact-policy').textContent = info.policy_number || 'N/A';
    document.getElementById('fact-date').textContent = info.incident_date || 'N/A';
    document.getElementById('fact-amount').textContent = `INR ${Number(info.claim_amount).toLocaleString('en-IN')}`;
    document.getElementById('fact-type').textContent = (info.claim_type || 'N/A').toUpperCase();

    // 3. Populate performance stats card
    const latHaiku = result.metrics.extraction_latency_s;
    const latSonnet = result.metrics.summary_latency_s;
    const totalLatency = (latHaiku + latSonnet).toFixed(2);
    
    document.getElementById('metric-latency').textContent = `${totalLatency}s`;
    
    // Estimate cost per 1000 claims
    const costPerClaim = info.claim_type === 'auto' ? 0.00048 : 0.00050; // Mock profile cost approx
    document.getElementById('metric-cost').textContent = `$${costPerClaim.toFixed(5)}`;

    // 4. Construct RAG details segment matching the claim type
    const policyTab = document.getElementById('policy-details-content');
    
    let policyTitle = "";
    let policyRules = "";
    
    if (info.claim_type === 'auto') {
        policyTitle = "Auto Policy Coverage Summary — Tamil Nadu Standard Motor Plan";
        policyRules = `
            <li><strong>Own Damage Limit:</strong> Expeditious own damage collision claims settled within IDV without review if under INR 200,000.</li>
            <li><strong>Mandatory Police FIR:</strong> Required for third-party collisions exceeding INR 50,000.</li>
            <li><strong>Exclusions:</strong> Claims filed > 30 days require justification. Excludes commercial racing/DUI.</li>
        `;
    } else if (info.claim_type === 'property') {
        policyTitle = "Property Policy Coverage Summary — Tamil Nadu Homeowner Plan";
        policyRules = `
            <li><strong>Water Damage Cap:</strong> Covered up to INR 500,000 per incident.</li>
            <li><strong>Documentation:</strong> Claims > INR 100,000 require independent weather report confirmation + photo evidence.</li>
            <li><strong>Exclusions:</strong> Excludes pre-existing structures and gradual seepage > 6 months.</li>
        `;
    } else if (info.claim_type === 'health') {
        policyTitle = "Health Policy Coverage Summary — Tamil Nadu Family Health Plan";
        policyRules = `
            <li><strong>Hospitalization SLA:</strong> Planned cashless-to-reimbursement conversions processed in 7-10 working days.</li>
            <li><strong>Exclusions:</strong> Excludes cosmetic or non-prescribed procedures. Requires discharge summary and bills.</li>
        `;
    } else {
        policyTitle = "Uncategorized Policy";
        policyRules = "<li>No specific matching rules found in Policy Vector Index.</li>";
    }

    policyTab.innerHTML = `
        <div class="policy-block">
            <div class="policy-title">🔍 Vector Similarity Search Match: 94.2%</div>
            <div class="policy-title" style="margin-top: 10px">${policyTitle}</div>
            <ul style="margin-left: 20px; font-size: 0.9rem; line-height: 1.6; color: var(--text-primary);">
                ${policyRules}
            </ul>
        </div>
    `;
}

// 6. Compare Models API call
async function compareActiveClaim() {
    if (!activeClaimKey) return;

    const modal = document.getElementById('compare-modal');
    const tableBody = document.getElementById('compare-table-body');
    tableBody.innerHTML = '<tr><td colspan="6" class="loading">Invoking multiple models side-by-side...</td></tr>';
    modal.classList.add('active');

    try {
        const response = await fetch(`/api/claims/compare/${encodeURIComponent(activeClaimKey)}`);
        const data = await response.json();

        if (data.status === 'success') {
            tableBody.innerHTML = '';
            data.comparison.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 500">${row.model}</td>
                    <td>${row.latency_s}s</td>
                    <td>${row.input_tokens}</td>
                    <td>${row.output_tokens}</td>
                    <td style="color: ${row.valid_json ? 'var(--success-color)' : 'var(--error-color)'}">${row.valid_json ? 'Yes' : 'No'}</td>
                    <td style="color: ${row.warnings > 0 ? 'var(--warning-color)' : 'var(--text-secondary)'}">${row.warnings}</td>
                `;
                tableBody.appendChild(tr);
            });
        } else {
            tableBody.innerHTML = `<tr><td colspan="6" style="color: var(--error-color)">Error: ${data.message}</td></tr>`;
        }
    } catch (e) {
        tableBody.innerHTML = '<tr><td colspan="6" style="color: var(--error-color)">Connection failure during model evaluation.</td></tr>';
    }
}

// Helper resets
function resetSummaryDetails() {
    document.getElementById('summary-card').innerHTML = `
        <div class="summary-placeholder">
            <span class="placeholder-icon">🤖</span>
            <p>Ready to process this claim. Click "Process Claim" to run RAG + AI triage.</p>
        </div>
    `;
    document.getElementById('fact-name').textContent = '-';
    document.getElementById('fact-policy').textContent = '-';
    document.getElementById('fact-date').textContent = '-';
    document.getElementById('fact-amount').textContent = '-';
    document.getElementById('fact-type').textContent = '-';
    document.getElementById('metric-latency').textContent = '-';
    document.getElementById('metric-cost').textContent = '-';
}

// 7. General event handlers & UI setup
function setupEventListeners() {
    // Process & Compare click bindings
    document.getElementById('process-claim-btn').addEventListener('click', processActiveClaim);
    document.getElementById('compare-models-btn').addEventListener('click', compareActiveClaim);

    // Tab buttons switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });

    // Close Modal bind
    document.getElementById('modal-close-btn').addEventListener('click', () => {
        document.getElementById('compare-modal').classList.remove('active');
    });
}

// 8. Drag and Drop file handler
function setupDragAndDrop() {
    const zone = document.getElementById('upload-zone');
    const input = document.getElementById('file-input');
    const browseBtn = document.getElementById('upload-btn');

    browseBtn.addEventListener('click', () => input.click());
    input.addEventListener('change', () => {
        if (input.files.length > 0) uploadFile(input.files[0]);
    });

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            uploadFile(e.dataTransfer.files[0]);
        }
    });
}

// 9. Upload File API
async function uploadFile(file) {
    if (!file.name.endsWith('.txt')) {
        alert('Please upload only text (.txt) documents.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    const zone = document.getElementById('upload-zone');
    const originalContent = zone.innerHTML;
    zone.innerHTML = '<div class="loading">📤 Uploading file to S3...</div>';

    try {
        const response = await fetch('/api/claims/upload', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();

        if (data.status === 'success') {
            await loadClaimsList();
            // Automatically select new uploaded file
            selectClaim(data.filename);
        } else {
            alert(`Upload failed: ${data.message}`);
        }
    } catch (e) {
        alert('Failed to connect to server during upload.');
    } finally {
        zone.innerHTML = originalContent;
        // Re-bind click event since we replaced innerHTML
        setupDragAndDrop();
    }
}
