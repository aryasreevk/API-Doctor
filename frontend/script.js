
document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // CONFIGURATION
    // ==========================================

    const API_BASE = "http://127.0.0.1:8000/api";

    let currentResponse = "";
    let currentCodeFix = "";
    let latestAnalysis = null;

    window.apiDoctorResponseHeaders = {};

    // Restore the latest API analysis when opening Control Center
    try {
        latestAnalysis = JSON.parse(
            sessionStorage.getItem("apiDoctorLatestAnalysis") || "null"
        );

        window.apiDoctorResponseHeaders = JSON.parse(
            sessionStorage.getItem("apiDoctorLatestHeaders") || "{}"
        );
    } catch (error) {
        latestAnalysis = null;
        window.apiDoctorResponseHeaders = {};
    }

    const $ = (id) => document.getElementById(id);

    // ==========================================
    // COMMON HELPERS
    // ==========================================

    function setText(id, value) {
        const element = $(id);
        if (element) element.textContent = value;
    }

    function addText(parent, tag, value, className) {
        const element = document.createElement(tag);
        element.textContent = value;

        if (className) {
            element.className = className;
        }

        parent.appendChild(element);
        return element;
    }

    function displayList(id, items, emptyMessage) {
        const element = $(id);
        if (!element) return;

        element.replaceChildren();

        if (!Array.isArray(items) || items.length === 0) {
            element.textContent = emptyMessage;
            return;
        }

        const list = document.createElement("ul");

        items.forEach(function (item) {
            addText(list, "li", String(item));
        });

        element.appendChild(list);
    }

    async function apiFetch(path, options = {}) {
        const response = await fetch(API_BASE + path, options);

        let data;

        try {
            data = await response.json();
        } catch {
            throw new Error("The server returned an invalid response.");
        }

        if (!response.ok) {
            throw new Error(
                data.detail || "Request failed: " + response.status
            );
        }

        return data;
    }

    // ==========================================
    // AUTHENTICATION FIELD VISIBILITY
    // ==========================================

    const authTypeSelect = $("authType");
    const authFields = $("authFields");

    const authKeyInput = $("authKey");
    const authSecretInput = $("authSecret");
    const authHeaderNameInput = $("authHeaderName");

    function updateAuthFields() {
        if (!authTypeSelect || !authFields) return;

        const type = authTypeSelect.value;

        authFields.hidden = type === "none";

        if (authKeyInput) {
            authKeyInput.hidden = type === "none";

            authKeyInput.placeholder =
                type === "basic"
                    ? "Username"
                    : type === "bearer"
                        ? "Enter Bearer Token"
                        : "Enter API key";
        }

        if (authSecretInput) {
            authSecretInput.hidden =
                type !== "basic" && type !== "apiKey";

            authSecretInput.placeholder =
                type === "basic" ? "Password" : "API key value";
        }

        if (authHeaderNameInput) {
            authHeaderNameInput.hidden = type !== "apiKey";
        }
    }

    if (authTypeSelect && authFields) {
        authTypeSelect.addEventListener("change", updateAuthFields);
        updateAuthFields();
    }

    // ==========================================
    // DATE FORMAT
    // ==========================================

    function formatDate(value) {
        if (!value) return "--";

        const date = new Date(value);

        return Number.isNaN(date.getTime())
            ? String(value)
            : date.toLocaleString();
    }

    // ==========================================
    // 1. API RESPONSE DISPLAY
    // ==========================================

    function renderAIDiagnosis(value) {
        const element = $("aiDiagnosis");
        if (!element) return;

        element.replaceChildren();

        if (!value) {
            element.textContent = "AI diagnosis unavailable.";
            return;
        }

        String(value).split(/\r?\n/).forEach(function (line) {
            line = line.trim();

            if (!line) return;

            if (/^#{1,3}\s/.test(line)) {
                addText(
                    element,
                    "h4",
                    line.replace(/^#{1,3}\s*/, "")
                );
            } else if (/^[-*]\s/.test(line)) {
                let list = element.lastElementChild;

                if (!list || list.tagName !== "UL") {
                    list = document.createElement("ul");
                    element.appendChild(list);
                }

                addText(
                    list,
                    "li",
                    line.replace(/^[-*]\s*/, "").replaceAll("**", "")
                );
            } else {
                addText(
                    element,
                    "p",
                    line.replaceAll("**", "")
                );
            }
        });
    }

    function displayResults(result) {
        const data = result.data || {};
        const analysis = result.analysis || {};

        latestAnalysis = analysis;

        window.apiDoctorResponseHeaders = data.headers || {};

        try {
            sessionStorage.setItem(
                "apiDoctorLatestAnalysis",
                JSON.stringify(latestAnalysis)
            );

            sessionStorage.setItem(
                "apiDoctorLatestHeaders",
                JSON.stringify(window.apiDoctorResponseHeaders)
            );
        } catch (error) {
            console.warn("Unable to preserve latest API analysis.");
        }

        setText(
            "statusCode",
            analysis.status_code ?? data.status_code ?? "--"
        );

        setText(
            "responseTime",
            (data.response_time_ms ?? analysis.response_time_ms ?? "--") +
            (
                data.response_time_ms !== undefined ||
                analysis.response_time_ms !== undefined
                    ? " ms"
                    : ""
            )
        );

        setText("apiHealth", analysis.health || "--");

        setText(
            "healthScore",
            analysis.health_score !== undefined
                ? analysis.health_score + " / 100"
                : "--"
        );

        displayList(
            "criticalIssues",
            analysis.critical_issues || analysis.issues,
            "No critical issues detected."
        );

        displayList(
            "warnings",
            analysis.warnings,
            "No warnings detected."
        );

        displayList(
            "recommendations",
            analysis.recommendations || analysis.suggestions,
            "No recommendations available."
        );

        renderAIDiagnosis(result.ai_diagnosis);

        const body = data.body;

        if (typeof body === "string") {
            try {
                currentResponse = JSON.stringify(
                    JSON.parse(body),
                    null,
                    4
                );
            } catch {
                currentResponse = body;
            }
        } else if (body !== undefined && body !== null) {
            currentResponse = JSON.stringify(body, null, 4);
        } else {
            currentResponse = "No response body available.";
        }

        setText("response", currentResponse);
        setText("copyMessage", "");

        loadAnalytics();
    }

    // ==========================================
    // 2. API TESTER
    // ==========================================

    const apiForm = $("apiForm");

    if (apiForm) {
        apiForm.addEventListener("submit", async function (event) {
            event.preventDefault();

            const method = $("method").value;
            const url = $("url").value.trim();

            if (!url) {
                setText("response", "Please enter an API endpoint.");
                return;
            }

            let headers = {};
            let jsonBody = null;

            try {
                headers = $("headers").value.trim()
                    ? JSON.parse($("headers").value)
                    : {};

                if (
                    !headers ||
                    Array.isArray(headers) ||
                    typeof headers !== "object"
                ) {
                    throw new Error("Headers must be a JSON object.");
                }

                jsonBody = $("body").value.trim()
                    ? JSON.parse($("body").value)
                    : null;

                if (
                    jsonBody !== null &&
                    (Array.isArray(jsonBody) ||
                        typeof jsonBody !== "object")
                ) {
                    throw new Error(
                        "Request body must be a JSON object."
                    );
                }

            } catch (error) {
                setText("response", "Invalid JSON: " + error.message);
                return;
            }

            // Authentication
            const authType = $("authType")?.value || "none";
            const authKey = $("authKey")?.value || "";
            const authSecret = $("authSecret")?.value || "";
            const authHeaderName =
                $("authHeaderName")?.value.trim() || "x-api-key";

            if (authType === "bearer" && authKey.trim()) {
                headers.Authorization = "Bearer " + authKey.trim();

            } else if (authType === "apiKey" && authSecret.trim()) {
                headers[authHeaderName] = authSecret.trim();

            } else if (authType === "basic") {
                if (!authKey || !authSecret) {
                    setText(
                        "response",
                        "Enter the username and password for Basic Auth."
                    );
                    return;
                }

                headers.Authorization =
                    "Basic " + btoa(authKey + ":" + authSecret);
            }

            const requestData = {
                url,
                method,
                headers,
                params: {},
                json_body: jsonBody
            };

            const button = $("testButton");

            if (button) {
                button.disabled = true;
                button.textContent = "Sending Request...";
            }

            setText("response", "Testing API. Please wait...");
            currentResponse = "";

            try {
                const result = await apiFetch("/test", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(requestData)
                });

                // Preserve a reusable request for Control Center.
                // Authentication secrets are deliberately excluded.
                const collectionRequest = {
                    ...requestData,
                    headers: { ...(requestData.headers || {}) }
                };

                Object.keys(collectionRequest.headers).forEach(function (key) {
                    const normalizedKey = key.toLowerCase();

                    if (
                        normalizedKey === "authorization" ||
                        normalizedKey === "proxy-authorization" ||
                        normalizedKey === "x-api-key" ||
                        normalizedKey === authHeaderName.toLowerCase()
                    ) {
                        delete collectionRequest.headers[key];
                    }
                });

                try {
                    sessionStorage.setItem(
                        "apiDoctorLastRequest",
                        JSON.stringify(collectionRequest)
                    );
                } catch (storageError) {
                    console.warn(
                        "Unable to save the latest request:",
                        storageError
                    );
                }

                displayResults(result);

            } catch (error) {
                currentResponse = "Error: " + error.message;
                setText("response", currentResponse);

            } finally {
                if (button) {
                    button.disabled = false;
                    button.textContent = "Send Request →";
                }
            }
        });
    }

    // ==========================================
    // 3. COPY RESPONSE
    // ==========================================

    if ($("copyResponse")) {
        $("copyResponse").addEventListener("click", async function () {
            if (!currentResponse) {
                setText("copyMessage", "No response available.");
                return;
            }

            try {
                await navigator.clipboard.writeText(currentResponse);
                setText("copyMessage", "Response copied successfully!");
            } catch {
                setText("copyMessage", "Unable to copy response.");
            }
        });
    }

    // ==========================================
    // 4. JSON COMPARATOR
    // ==========================================

    if ($("compareButton")) {
        $("compareButton").addEventListener("click", async function () {
            const summary = $("comparisonSummary");
            const details = $("comparisonDetails");

            details.replaceChildren();

            let responseA;
            let responseB;

            try {
                responseA = JSON.parse($("responseA").value);
                responseB = JSON.parse($("responseB").value);

                if (
                    !responseA ||
                    !responseB ||
                    Array.isArray(responseA) ||
                    Array.isArray(responseB) ||
                    typeof responseA !== "object" ||
                    typeof responseB !== "object"
                ) {
                    throw new Error("Both inputs must be JSON objects.");
                }

            } catch (error) {
                summary.textContent = "Invalid input: " + error.message;
                return;
            }

            const button = $("compareButton");
            button.disabled = true;
            button.textContent = "Comparing...";

            try {
                const result = await apiFetch("/compare", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        response_a: responseA,
                        response_b: responseB
                    })
                });

                summary.textContent = "Comparison completed successfully.";

                addText(
                    details,
                    "pre",
                    JSON.stringify(result.comparison, null, 4)
                );

            } catch (error) {
                summary.textContent = error.message;

            } finally {
                button.disabled = false;
                button.textContent = "Compare Responses";
            }
        });
    }

    // ==========================================
    // 5. AI CODE FIX
    // ==========================================

    if ($("generateFixButton")) {
        $("generateFixButton").addEventListener(
            "click",
            async function () {

                if (!latestAnalysis) {
                    setText(
                        "fixMessage",
                        "Test an API first to generate a code fix."
                    );
                    return;
                }

                const button = $("generateFixButton");
                button.disabled = true;
                button.textContent = "Generating...";

                setText("fixMessage", "Generating AI code fix...");
                setText("generatedCode", "");

                try {
                    const result = await apiFetch("/generate-fix", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({
                            analysis: latestAnalysis,
                            language: $("programmingLanguage").value
                        })
                    });

                    currentCodeFix = result.code_fix || "";

                    setText(
                        "generatedCode",
                        typeof currentCodeFix === "string"
                            ? currentCodeFix
                            : JSON.stringify(currentCodeFix, null, 4)
                    );

                    setText(
                        "fixMessage",
                        "AI code fix generated successfully."
                    );

                } catch (error) {
                    currentCodeFix = "";
                    setText("fixMessage", error.message);
                    setText("generatedCode", "No code fix generated.");

                } finally {
                    button.disabled = false;
                    button.textContent = "Generate AI Code Fix";
                }
            }
        );
    }

    if ($("copyFixButton")) {
        $("copyFixButton").addEventListener("click", async function () {
            if (!currentCodeFix) {
                setText("fixCopyMessage", "No generated code available.");
                return;
            }

            try {
                await navigator.clipboard.writeText(
                    typeof currentCodeFix === "string"
                        ? currentCodeFix
                        : JSON.stringify(currentCodeFix, null, 4)
                );

                setText("fixCopyMessage", "Code copied successfully!");

            } catch {
                setText("fixCopyMessage", "Unable to copy code.");
            }
        });
    }

    // ==========================================
    // 6. API HISTORY
    // ==========================================

    async function loadHistory() {
        if (!$("historyList")) return;

        const list = $("historyList");
        list.replaceChildren();

        try {
            const result = await apiFetch("/history");
            const records = result.history || [];

            if (!records.length) {
                const row = document.createElement("tr");
                const cell = addText(
                    row,
                    "td",
                    "No API history available."
                );

                cell.colSpan = 7;
                list.appendChild(row);
                return;
            }

            records.forEach(function (record) {
                const row = document.createElement("tr");

                [
                    record.url,
                    record.method,
                    record.status_code,
                    record.response_time_ms !== null
                        ? record.response_time_ms + " ms"
                        : "--",
                    record.health_score,
                    formatDate(record.created_at)
                ].forEach(function (value) {
                    addText(row, "td", value ?? "--");
                });

                const actionCell = document.createElement("td");
                const viewButton = addText(
                    actionCell,
                    "button",
                    "View"
                );

                viewButton.type = "button";

                viewButton.addEventListener("click", function () {
                    loadHistoryDetails(record.id);
                });

                row.appendChild(actionCell);
                list.appendChild(row);
            });

        } catch (error) {
            const row = document.createElement("tr");
            const cell = addText(row, "td", error.message);

            cell.colSpan = 7;
            list.appendChild(row);
        }
    }

    async function loadHistoryDetails(id) {
        const content = $("historyDetailContent");
        if (!content) return;

        content.replaceChildren();
        setText("historyDetailMessage", "Loading request details...");

        if ($("historyDetails")) {
            $("historyDetails").hidden = false;
        }

        try {
            const result = await apiFetch(
                "/history/" + encodeURIComponent(id)
            );

            const record = result.history || result;

            const fields = {
                "Endpoint": record.url,
                "Method": record.method,
                "Status Code": record.status_code,
                "Response Time": record.response_time_ms,
                "API Health": record.health,
                "Health Score": record.health_score,
                "JSON Valid": record.json_valid,
                "Issues": record.issues,
                "Suggestions": record.suggestions,
                "AI Diagnosis": record.ai_diagnosis,
                "Created At": formatDate(record.created_at)
            };

            Object.entries(fields).forEach(function ([label, value]) {
                const block = document.createElement("div");

                addText(block, "h4", label);

                addText(
                    block,
                    "p",
                    value && typeof value === "object"
                        ? JSON.stringify(value, null, 2)
                        : value ?? "--"
                );

                content.appendChild(block);
            });

            setText("historyDetailMessage", "Request details");

        } catch (error) {
            setText("historyDetailMessage", error.message);
        }
    }

    if ($("refreshHistoryButton")) {
        $("refreshHistoryButton").addEventListener(
            "click",
            loadHistory
        );
    }

    loadHistory();

    // ==========================================
    // 7. SIDEBAR NAVIGATION
    // ==========================================

    const navItems = document.querySelectorAll(
        ".sidebar-nav .nav-item[href^='#']"
    );

    const sections = [
        "api-tester",
        "dashboard",
        "comparator",
        "code-fix"
    ].map($).filter(Boolean);

    function setActiveNavigation(id) {
        navItems.forEach(function (item) {
            item.classList.toggle(
                "active",
                item.getAttribute("href") === "#" + id
            );
        });
    }

    navItems.forEach(function (item) {
        item.addEventListener("click", function (event) {
            const id = item.getAttribute("href").substring(1);
            const section = $(id);

            if (!section) return;

            event.preventDefault();

            setActiveNavigation(id);

            const top =
                section.getBoundingClientRect().top +
                window.scrollY - 85;

            window.scrollTo({
                top: Math.max(0, top),
                behavior: "smooth"
            });

            history.replaceState(null, "", "#" + id);
        });
    });

    let navigationFrame = null;

    function updateNavigation() {
        if (navigationFrame !== null) {
            cancelAnimationFrame(navigationFrame);
        }

        navigationFrame = requestAnimationFrame(function () {
            let activeSection = sections[0];

            sections.forEach(function (section) {
                if (section.getBoundingClientRect().top <= 170) {
                    activeSection = section;
                }
            });

            const atBottom =
                window.innerHeight + window.scrollY >=
                document.documentElement.scrollHeight - 5;

            if (atBottom && sections.length) {
                activeSection = sections[sections.length - 1];
            }

            if (activeSection) {
                setActiveNavigation(activeSection.id);
            }

            navigationFrame = null;
        });
    }

    window.addEventListener("scroll", updateNavigation, {
        passive: true
    });

    window.addEventListener("resize", updateNavigation);
    updateNavigation();

    // ==========================================
    // 8. DASHBOARD ANALYTICS
    // ==========================================

    async function loadAnalytics() {
        if (!$("analyticsTotal") && !$("responseTimeChart")) return;

        try {
            const data = await apiFetch("/analytics");

            setText("analyticsTotal", data.total_requests ?? 0);
            setText("analyticsSuccess", data.successful_requests ?? 0);
            setText("analyticsFailed", data.failed_requests ?? 0);
            setText("analyticsRate", (data.success_rate ?? 0) + "%");

            setText(
                "analyticsTime",
                (data.average_response_time_ms ?? 0) + " ms"
            );

            setText(
                "analyticsHealth",
                (data.average_health_score ?? 0) + " / 100"
            );

            setText("analyticsSlow", data.slow_requests ?? 0);

            renderResponseTimeChart(data.recent || []);

        } catch (error) {
            console.error("Analytics error:", error);
            setText("analyticsTotal", "Unavailable");
        }
    }

    function renderResponseTimeChart(records) {
        const chart = $("responseTimeChart");
        if (!chart) return;

        chart.replaceChildren();

        const items = records
            .filter(item => item.response_time_ms !== null)
            .slice()
            .reverse();

        if (!items.length) {
            addText(
                chart,
                "p",
                "Run API tests to build a response-time trend.",
                "feature-note"
            );
            return;
        }

        const maxTime = Math.max(
            1,
            ...items.map(item => Number(item.response_time_ms))
        );

        items.forEach(function (item, index) {
            const wrapper = document.createElement("div");
            wrapper.className = "response-bar-wrap";

            const bar = document.createElement("div");
            bar.className = "response-bar";

            bar.style.height =
                Math.max(
                    5,
                    Number(item.response_time_ms) / maxTime * 100
                ) + "%";

            bar.title =
                item.method + " " + item.url +
                " — " + item.response_time_ms + " ms";

            addText(
                wrapper,
                "span",
                Math.round(Number(item.response_time_ms)) + " ms"
            );

            wrapper.appendChild(bar);
            chart.appendChild(wrapper);
        });
    }

    if ($("refreshAnalyticsButton")) {
        $("refreshAnalyticsButton").addEventListener(
            "click",
            loadAnalytics
        );
    }

    // ==========================================
    // 9. SAVED REQUEST COLLECTIONS
    // ==========================================

    async function loadCollections() {
        const list = $("collectionsList");
        if (!list) return;

        list.replaceChildren();

        try {
            const result = await apiFetch("/collections");
            const items = result.collections || [];

            if (!items.length) {
                addText(
                    list,
                    "p",
                    "No saved requests yet.",
                    "feature-note"
                );
                return;
            }

            items.forEach(function (item) {
                const row = document.createElement("div");
                row.className = "collection-item";

                addText(row, "div", item.name, "collection-title");

                addText(
                    row,
                    "small",
                    item.method + " · " + item.url,
                    "collection-meta"
                );

                const actions = document.createElement("div");
                actions.className = "collection-item-actions";

                const loadButton = addText(actions, "button", "Load");
                loadButton.type = "button";

                loadButton.addEventListener("click", function () {
                    const requestToLoad = {
                        url: item.url,
                        method: item.method,
                        headers: item.headers || {},
                        params: item.params || {},
                        json_body: item.json_body ?? null
                    };

                    try {
                        sessionStorage.setItem(
                            "apiDoctorLastRequest",
                            JSON.stringify(requestToLoad)
                        );
                    } catch (error) {
                        console.warn("Unable to transfer saved request.", error);
                    }

                    setText(
                        "collectionMessage",
                        "Request ready. Open API Tester to use it."
                    );
                });

                const deleteButton = addText(
                    actions,
                    "button",
                    "Delete"
                );

                deleteButton.type = "button";
                deleteButton.className = "secondary-button";

                deleteButton.addEventListener("click", async function () {
                    if (!confirm("Delete this saved request?")) return;

                    try {
                        await apiFetch(
                            "/collections/" + item.id,
                            { method: "DELETE" }
                        );

                        await loadCollections();

                    } catch (error) {
                        setText("collectionMessage", error.message);
                    }
                });

                row.appendChild(actions);
                list.appendChild(row);
            });

        } catch (error) {
            addText(list, "p", error.message, "feature-note");
        }
    }

    // Save the latest API Tester request from Control Center
    if ($("saveCollectionButton")) {
        const saveButton = $("saveCollectionButton");
        const savedRequestText = sessionStorage.getItem(
            "apiDoctorLastRequest"
        );

        if (!savedRequestText) {
            setText(
                "collectionMessage",
                "Test an API on the API Tester page before saving it."
            );

            saveButton.disabled = true;
        } else {
            saveButton.disabled = false;
        }

        saveButton.addEventListener("click", async function () {
            const nameInput = $("collectionName");
            const name = nameInput ? nameInput.value.trim() : "";

            if (!name) {
                setText(
                    "collectionMessage",
                    "Please enter a collection name."
                );
                return;
            }

            let requestData;

            try {
                const storedRequest = sessionStorage.getItem(
                    "apiDoctorLastRequest"
                );

                if (!storedRequest) {
                    throw new Error(
                        "No recent API request found. Test an API first."
                    );
                }

                requestData = JSON.parse(storedRequest);

                if (!requestData.url || !requestData.method) {
                    throw new Error("The saved request is incomplete.");
                }

            } catch (error) {
                setText("collectionMessage", error.message);
                return;
            }

            saveButton.disabled = true;
            saveButton.textContent = "Saving...";

            try {
                await apiFetch("/collections", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        name: name,
                        url: requestData.url,
                        method: requestData.method,
                        headers: requestData.headers || {},
                        params: requestData.params || {},
                        json_body: requestData.json_body ?? null
                    })
                });

                setText(
                    "collectionMessage",
                    "Request saved successfully!"
                );

                if (nameInput) nameInput.value = "";

                await loadCollections();

            } catch (error) {
                setText(
                    "collectionMessage",
                    "Unable to save request: " + error.message
                );

            } finally {
                saveButton.disabled = false;
                saveButton.textContent = "Save Current Request";
            }
        });
    }

    // ==========================================
    // 10. API TEST AUTOMATION
    // ==========================================

    if ($("runCollectionsButton")) {
        $("runCollectionsButton").addEventListener(
            "click",
            async function () {

                const button = $("runCollectionsButton");
                button.disabled = true;

                setText(
                    "automationMessage",
                    "Loading saved requests..."
                );

                try {
                    const result = await apiFetch("/collections");
                    const items = result.collections || [];

                    if (!items.length) {
                        setText(
                            "automationMessage",
                            "Save at least one request first."
                        );
                        return;
                    }

                    let passed = 0;
                    let failed = 0;

                    for (let index = 0; index < items.length; index++) {
                        const item = items[index];

                        setText(
                            "automationMessage",
                            "Running " + (index + 1) +
                            " of " + items.length + ": " + item.name
                        );

                        try {
                            await apiFetch("/test", {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json"
                                },
                                body: JSON.stringify({
                                    url: item.url,
                                    method: item.method,
                                    headers: item.headers || {},
                                    params: item.params || {},
                                    json_body: item.json_body
                                })
                            });

                            passed++;

                        } catch {
                            failed++;
                        }
                    }

                    setText(
                        "automationMessage",
                        "Automation completed. Successful: " +
                        passed + " | Failed: " + failed
                    );

                    await loadAnalytics();
                    await loadHistory();

                } catch (error) {
                    setText(
                        "automationMessage",
                        "Automation failed: " + error.message
                    );

                } finally {
                    button.disabled = false;
                }
            }
        );
    }

    // ==========================================
    // 11. REPORT EXPORT
    // ==========================================

    async function getHistoryForExport() {
        const result = await apiFetch("/history?limit=100");
        return result.history || [];
    }

    function downloadFile(filename, content, mimeType) {
        const blob = new Blob(
            [content],
            { type: mimeType }
        );

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = url;
        link.download = filename;

        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(url);
    }

    if ($("exportJsonButton")) {
        $("exportJsonButton").addEventListener(
            "click",
            async function () {
                try {
                    const records = await getHistoryForExport();

                    downloadFile(
                        "api-doctor-report.json",
                        JSON.stringify(records, null, 4),
                        "application/json"
                    );

                } catch (error) {
                    alert("JSON export failed: " + error.message);
                }
            }
        );
    }

    if ($("exportCsvButton")) {
        $("exportCsvButton").addEventListener(
            "click",
            async function () {
                try {
                    const records = await getHistoryForExport();

                    const columns = [
                        "id",
                        "url",
                        "method",
                        "status_code",
                        "response_time_ms",
                        "health",
                        "health_score",
                        "json_valid",
                        "issues",
                        "suggestions",
                        "ai_diagnosis",
                        "created_at"
                    ];

                    function quote(value) {
                        const text = value && typeof value === "object"
                            ? JSON.stringify(value)
                            : String(value ?? "");

                        return '"' + text.replace(/"/g, '""') + '"';
                    }

                    const rows = [
                        columns.join(","),
                        ...records.map(record =>
                            columns.map(key => quote(record[key])).join(",")
                        )
                    ];

                    downloadFile(
                        "api-doctor-report.csv",
                        rows.join("\r\n"),
                        "text/csv;charset=utf-8"
                    );

                } catch (error) {
                    alert("CSV export failed: " + error.message);
                }
            }
        );
    }

    // ==========================================
    // 12. SECURITY HEADER REVIEW
    // ==========================================

    if ($("securityReviewButton")) {
        $("securityReviewButton").addEventListener(
            "click",
            function () {

                const results = $("securityReviewResults");
                if (!results) return;

                results.replaceChildren();

                if (!latestAnalysis) {
                    results.textContent =
                        "Test an API first, then run the security review.";
                    return;
                }

                const headers = {};

                Object.entries(
                    window.apiDoctorResponseHeaders || {}
                ).forEach(function ([key, value]) {
                    headers[key.toLowerCase()] = value;
                });

                const checks = [
                    [
                        "Strict-Transport-Security",
                        "strict-transport-security",
                        "Recommended for HTTPS endpoints."
                    ],
                    [
                        "Content-Security-Policy",
                        "content-security-policy",
                        "Helps restrict content sources."
                    ],
                    [
                        "X-Content-Type-Options",
                        "x-content-type-options",
                        "Helps prevent MIME-type sniffing."
                    ],
                    [
                        "X-Frame-Options",
                        "x-frame-options",
                        "Helps reduce clickjacking risks."
                    ],
                    [
                        "Referrer-Policy",
                        "referrer-policy",
                        "Controls referrer information."
                    ],
                    [
                        "Permissions-Policy",
                        "permissions-policy",
                        "Controls selected browser features."
                    ]
                ];

                let missing = 0;

                checks.forEach(function ([label, key, recommendation]) {
                    const exists = Object.prototype.hasOwnProperty.call(
                        headers,
                        key
                    );

                    const row = document.createElement("p");

                    row.textContent = exists
                        ? "✓ " + label + ": Present"
                        : "⚠ " + label + ": Not detected — " + recommendation;

                    results.appendChild(row);

                    if (!exists) missing++;
                });

                addText(
                    results,
                    "strong",
                    missing + " of " + checks.length +
                    " checked security headers were not detected. " +
                    "This is a basic header review, not a full security audit."
                );
            }
        );
    }

    // ==========================================
    // 13. INITIALIZE CONTROL CENTER
    // ==========================================

    loadAnalytics();
    loadCollections();

    console.log("API Doctor loaded successfully.");

});
