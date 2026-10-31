document.addEventListener("DOMContentLoaded", function () {

    const API_BASE = "http://127.0.0.1:8000/api";

    const historyList = document.getElementById("historyList");
    const refreshButton = document.getElementById("refreshHistoryButton");
    const searchInput = document.getElementById("historySearch");
    const methodFilter = document.getElementById("historyMethodFilter");
    const historyCount = document.getElementById("historyCount");

    const historyDetails = document.getElementById("historyDetails");
    const detailMessage = document.getElementById("historyDetailMessage");
    const detailContent = document.getElementById("historyDetailContent");

    let allHistory = [];

    function getValue(record, keys, fallback = "--") {
        for (const key of keys) {
            if (record[key] !== undefined && record[key] !== null) {
                return record[key];
            }
        }
        return fallback;
    }

    function showMessage(message) {
        historyList.replaceChildren();

        const row = document.createElement("tr");
        const cell = document.createElement("td");

        cell.colSpan = 7;
        cell.className = "history-empty";
        cell.textContent = message;

        row.appendChild(cell);
        historyList.appendChild(row);
    }

    function formatDate(value) {
        if (!value) return "--";

        const date = new Date(value);

        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        return date.toLocaleString();
    }

    function createCell(value) {
        const cell = document.createElement("td");
        cell.textContent = String(value);
        return cell;
    }

    function renderHistory(records) {
        historyList.replaceChildren();

        if (!records.length) {
            showMessage("No matching API history records found.");
            return;
        }

        records.forEach(function (record) {

            const row = document.createElement("tr");

            const endpoint = getValue(record, ["url", "endpoint"]);
            const method = getValue(record, ["method"]);
            const status = getValue(record, ["status_code"]);
            const time = getValue(record, ["response_time_ms"]);
            const score = getValue(record, ["health_score"]);
            const date = getValue(record, ["created_at", "timestamp"]);

            row.appendChild(createCell(endpoint));
            row.appendChild(createCell(method));
            row.appendChild(createCell(status));
            row.appendChild(createCell(time === "--" ? "--" : `${time} ms`));
            row.appendChild(createCell(score === "--" ? "--" : `${score}/100`));
            row.appendChild(createCell(formatDate(date)));

            const actionCell = document.createElement("td");
            const viewButton = document.createElement("button");

            viewButton.type = "button";
            viewButton.className = "history-view-button";
            viewButton.textContent = "View";

            viewButton.addEventListener("click", function () {
                const recordId = getValue(record, ["id"], null);

                if (recordId !== null) {
                    loadDetails(recordId);
                }
            });

            actionCell.appendChild(viewButton);
            row.appendChild(actionCell);

            historyList.appendChild(row);
        });
    }

    function applyFilters() {
        const searchTerm = searchInput.value.trim().toLowerCase();
        const selectedMethod = methodFilter.value;

        const filtered = allHistory.filter(function (record) {

            const url = String(getValue(record, ["url", "endpoint"], ""));
            const method = String(getValue(record, ["method"], "")).toUpperCase();

            const matchesSearch =
                url.toLowerCase().includes(searchTerm) ||
                method.toLowerCase().includes(searchTerm);

            const matchesMethod =
                selectedMethod === "ALL" || method === selectedMethod;

            return matchesSearch && matchesMethod;
        });

        historyCount.textContent =
            `${filtered.length} of ${allHistory.length} request(s)`;

        renderHistory(filtered);
    }

    async function loadHistory() {
        refreshButton.disabled = true;
        refreshButton.textContent = "Loading...";

        historyCount.textContent = "Loading saved requests...";
        showMessage("Loading history...");

        try {
            const response = await fetch(`${API_BASE}/history`);

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const result = await response.json();

            if (Array.isArray(result)) {
                allHistory = result;
            } else {
                allHistory =
                    result.history ||
                    result.records ||
                    result.items ||
                    [];
            }

            if (!Array.isArray(allHistory)) {
                allHistory = [];
            }

            applyFilters();

        } catch (error) {
            showMessage(
                "Unable to load API history. Check whether the backend is running."
            );

            historyCount.textContent = "History could not be loaded.";
            console.error("History loading error:", error);

        } finally {
            refreshButton.disabled = false;
            refreshButton.textContent = "↻ Refresh History";
        }
    }

    function addDetailRow(container, label, value) {
        const item = document.createElement("div");
        item.className = "history-detail-item";

        const heading = document.createElement("strong");
        heading.textContent = label;

        const content = document.createElement("span");
        content.textContent =
            value === undefined || value === null
                ? "--"
                : typeof value === "object"
                    ? JSON.stringify(value, null, 2)
                    : String(value);

        item.appendChild(heading);
        item.appendChild(content);
        container.appendChild(item);
    }

    async function loadDetails(id) {
        historyDetails.hidden = false;
        detailMessage.textContent = "Loading request details...";
        detailContent.replaceChildren();

        historyDetails.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

        try {
            const response = await fetch(`${API_BASE}/history/${id}`);

            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }

            const result = await response.json();

            const record =
                result.history ||
                result.record ||
                result;

            detailMessage.textContent = "Saved request information";

            addDetailRow(detailContent, "Endpoint", record.url);
            addDetailRow(detailContent, "Method", record.method);
            addDetailRow(detailContent, "HTTP Status", record.status_code);
            addDetailRow(detailContent, "Response Time", record.response_time_ms);
            addDetailRow(detailContent, "API Health", record.health);
            addDetailRow(detailContent, "Health Score", record.health_score);
            addDetailRow(detailContent, "JSON Valid", record.json_valid);
            addDetailRow(detailContent, "Critical Issues / Issues", record.issues);
            addDetailRow(detailContent, "Suggestions", record.suggestions);
            addDetailRow(detailContent, "AI Diagnosis", record.ai_diagnosis);
            addDetailRow(detailContent, "Created At", formatDate(record.created_at));

        } catch (error) {
            detailMessage.textContent =
                "Unable to load the selected request details.";

            console.error("History detail error:", error);
        }
    }

    refreshButton.addEventListener("click", loadHistory);
    searchInput.addEventListener("input", applyFilters);
    methodFilter.addEventListener("change", applyFilters);

    loadHistory();
});