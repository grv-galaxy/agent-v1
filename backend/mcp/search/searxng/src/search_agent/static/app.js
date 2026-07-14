document.addEventListener("DOMContentLoaded", () => {
    // --- Tabs Logic ---
    const tabSearch = document.getElementById("tab-search");
    const tabHistory = document.getElementById("tab-history");
    const viewSearch = document.getElementById("view-search");
    const viewHistory = document.getElementById("view-history");
    const historyList = document.getElementById("history-list");

    tabSearch.addEventListener("click", () => {
        tabSearch.classList.add("active");
        tabHistory.classList.remove("active");
        viewSearch.style.display = "block";
        viewHistory.style.display = "none";
    });

    tabHistory.addEventListener("click", () => {
        tabHistory.classList.add("active");
        tabSearch.classList.remove("active");
        viewSearch.style.display = "none";
        viewHistory.style.display = "block";
        fetchHistory();
    });

    async function fetchHistory() {
        historyList.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 20px;">Loading history...</div>`;
        try {
            const res = await fetch("/api/history");
            const data = await res.json();
            if (data.error) {
                historyList.innerHTML = `<div style="color: var(--error);">${data.error}</div>`;
                return;
            }
            renderHistory(data.history || []);
        } catch (e) {
            historyList.innerHTML = `<div style="color: var(--error);">Failed to fetch history</div>`;
        }
    }

    function renderHistory(history) {
        historyList.innerHTML = "";
        if (history.length === 0) {
            historyList.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 20px;">No searches yet.</div>`;
            return;
        }

        history.forEach(item => {
            const card = document.createElement("div");
            card.className = "history-card";
            
            const sourcesHtml = item.engines_used.map(s => `<span class="history-source-chip">${s}</span>`).join("");
            const passRate = item.citation_pass_rate !== null ? Math.round(item.citation_pass_rate * 100) : 0;
            const passColor = passRate > 50 ? 'var(--success)' : (passRate > 0 ? 'var(--warning)' : 'var(--error)');
            
            const dateStr = new Date(item.timestamp).toLocaleString();
            
            card.innerHTML = `
                <div class="history-header">
                    <h3 class="history-query">${item.query}</h3>
                    <div class="history-meta">
                        <span>${dateStr}</span>
                        <span>${item.latency_total_ms}ms total</span>
                        <span style="color: ${passColor};">${passRate}% cites valid</span>
                    </div>
                </div>
                <div class="history-sources">
                    ${sourcesHtml}
                </div>
                ${item.final_answer ? `<div class="history-answer">${item.final_answer.replace(/\n/g, '<br>')}</div>` : ''}
            `;
            historyList.appendChild(card);
        });
    }

    // --- Search WebSocket Logic ---
    const searchInput = document.getElementById("search-input");
    const traceContainer = document.getElementById("trace-container");
    const synthesisContainer = document.getElementById("synthesis-container");
    const answerText = document.getElementById("answer-text");
    
    let ws = null;
    let groupMap = {}; 
    let currentStageRow = null;
    let stageTimers = {};   // stageId -> { intervalId, startMs }
    let chipTimers = {};    // source_id -> { intervalId, startMs }
    let queryStartMs = null;

    searchInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && searchInput.value.trim() !== "") {
            startSearch(searchInput.value.trim());
        }
    });

    function startSearch(query) {
        traceContainer.innerHTML = "";
        answerText.innerHTML = "";
        synthesisContainer.style.display = "none";
        groupMap = {};
        currentStageRow = null;
        stageTimers = {};
        chipTimers = {};
        queryStartMs = Date.now();

        // Remove old summary bar if any
        const old = document.getElementById("query-summary-bar");
        if (old) old.remove();

        if (ws) {
            ws.close();
        }
        
        ws = new WebSocket(`ws://${window.location.host}/ws/query`);
        
        ws.onopen = () => {
            ws.send(JSON.stringify({ query: query }));
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleEvent(data);
        };

        ws.onerror = (error) => {
            console.error("WebSocket Error:", error);
        };
    }

    function handleEvent(data) {
        switch (data.type) {
            case "stage_start":
                currentStageRow = createStageRow(data.stage, data.label);
                break;
            case "stage_done":
                if (currentStageRow) {
                    updateStageRow(currentStageRow, data.stage, data.elapsed_ms);
                }
                break;
            case "source_start":
            case "page_visit_start":
                handleSourceStart(data);
                break;
            case "source_done":
            case "source_error":
            case "page_visit_done":
                handleSourceEnd(data);
                break;
            case "synthesis_token":
                if (synthesisContainer.style.display === "none") {
                    synthesisContainer.style.display = "block";
                }
                answerText.innerHTML += data.text.replace(/\n/g, '<br>');
                break;
            case "citation_check":
                updateCitationPill(data.n, data.passed);
                break;
            case "done": {
                const totalMs = data.total_elapsed_ms;
                const totalSec = (totalMs / 1000).toFixed(2);
                // Clear any remaining timers
                Object.values(stageTimers).forEach(t => clearInterval(t.intervalId));
                Object.values(chipTimers).forEach(t => clearInterval(t.intervalId));
                // Render summary bar
                const bar = document.createElement("div");
                bar.id = "query-summary-bar";
                bar.className = "query-summary-bar";
                bar.innerHTML = `<span class="summary-icon">⚡</span> Completed in <strong>${totalSec}s</strong>`;
                traceContainer.appendChild(bar);
                ws.close();
                break;
            }
        }
    }

    function createStageRow(stageId, label) {
        // Stop any previous active stage timer
        Object.entries(stageTimers).forEach(([id, t]) => {
            clearInterval(t.intervalId);
        });

        const row = document.createElement("div");
        row.className = "stage-row active";
        row.id = `stage-${stageId}`;
        
        row.innerHTML = `
            <div class="stage-left">
                <div class="stage-icon"></div>
                <div class="stage-label">${label}</div>
            </div>
            <div class="stage-time" id="stagetime-${stageId}">0ms</div>
        `;
        traceContainer.appendChild(row);

        // Start live timer
        const startMs = Date.now();
        const timeEl = row.querySelector(`#stagetime-${stageId}`);
        const intervalId = setInterval(() => {
            timeEl.innerText = `${Date.now() - startMs}ms`;
        }, 50);
        stageTimers[stageId] = { intervalId, startMs };

        return row;
    }

    function updateStageRow(row, stageId, elapsedMs) {
        // Stop the live timer
        if (stageTimers[stageId]) {
            clearInterval(stageTimers[stageId].intervalId);
        }
        row.classList.remove("active");
        row.classList.add("done");
        // Format nicely
        const label = elapsedMs >= 1000
            ? `${(elapsedMs / 1000).toFixed(2)}s`
            : `${elapsedMs}ms`;
        row.querySelector(".stage-time").innerText = label;
    }

    function handleSourceStart(data) {
        if (data.type === "page_visit_start") {
            const card = document.createElement("div");
            card.className = "page-visit-card";
            card.id = `chip-${data.source_id}`;
            
            card.innerHTML = `
                <div class="page-visit-left">
                    <span class="page-visit-icon">📖</span>
                    <span>${data.label || 'Reading article...'} (${data.domain || 'website'})</span>
                </div>
                <div class="wave-loader" id="status-${data.source_id}">
                    <span></span><span></span><span></span><span></span>
                </div>
            `;
            traceContainer.appendChild(card);
            return;
        }

        const groupId = data.group_id || `single-${data.source_id}`;
        
        if (!groupMap[groupId]) {
            const groupEl = document.createElement("div");
            groupEl.className = "source-group";
            groupEl.id = `group-${groupId}`;
            
            const summaryEl = document.createElement("div");
            summaryEl.className = "source-group-summary";
            summaryEl.id = `summary-${groupId}`;
            summaryEl.onclick = () => {
                groupEl.classList.toggle("collapsed");
            };
            
            traceContainer.appendChild(groupEl);
            traceContainer.appendChild(summaryEl);
            
            groupMap[groupId] = {
                total: 0,
                done: 0,
                groupEl: groupEl,
                summaryEl: summaryEl
            };
        }
        
        groupMap[groupId].total += 1;
        
        const chip = document.createElement("div");
        chip.className = "source-chip active";
        chip.id = `chip-${data.source_id}`;
        
        let faviconUrl = "data:,";
        if (data.domain) {
            faviconUrl = `https://www.google.com/s2/favicons?domain=${data.domain}&sz=64`;
        }
        
        chip.innerHTML = `
            <img class="favicon" src="${faviconUrl}" alt="" onerror="this.style.display='none'">
            <span class="chip-label">${data.label}</span>
            <div class="status-indicator" id="status-${data.source_id}">
                <div class="spinner"></div>
            </div>
            <span class="chip-elapsed" id="chiptime-${data.source_id}">0ms</span>
        `;
        
        // Start a live timer for this chip
        const startMs = Date.now();
        const timeEl = chip.querySelector(`#chiptime-${data.source_id}`);
        const intervalId = setInterval(() => {
            timeEl.innerText = `${Date.now() - startMs}ms`;
        }, 100);
        chipTimers[data.source_id] = { intervalId, startMs };
        
        groupMap[groupId].groupEl.appendChild(chip);
    }

    function handleSourceEnd(data) {
        const chip = document.getElementById(`chip-${data.source_id}`);
        const statusInd = document.getElementById(`status-${data.source_id}`);
        if (!chip || !statusInd) return;

        // Stop chip timer and show final time
        let elapsedLabel = "";
        if (chipTimers[data.source_id]) {
            clearInterval(chipTimers[data.source_id].intervalId);
            const elapsed = Date.now() - chipTimers[data.source_id].startMs;
            elapsedLabel = elapsed >= 1000 ? `${(elapsed/1000).toFixed(1)}s` : `${elapsed}ms`;
            const timeEl = document.getElementById(`chiptime-${data.source_id}`);
            if (timeEl) timeEl.innerText = elapsedLabel;
        }

        if (chip.classList.contains("page-visit-card")) {
            statusInd.className = "";
            if (data.status === "success" || data.type === "page_visit_done") {
                statusInd.innerHTML = `<span style="color: #4ade80;">✓</span>`;
            } else {
                statusInd.innerHTML = `<span style="color: #ef4444;">✕</span>`;
            }
            return;
        }

        chip.classList.remove("active");
        
        if (data.status === "success") {
            chip.classList.add("done");
            statusInd.innerHTML = `<span class="icon-success">✓</span>`;
        } else {
            chip.classList.add("error");
            statusInd.innerHTML = `<span class="icon-error">✕</span>`;
        }

        for (const [groupId, groupData] of Object.entries(groupMap)) {
            if (groupData.groupEl.contains(chip)) {
                groupData.done += 1;
                if (groupData.done === groupData.total) {
                    setTimeout(() => {
                        groupData.groupEl.classList.add("collapsed");
                        groupData.summaryEl.innerText = `Searched ${groupData.total} sources`;
                    }, 500); 
                }
                break;
            }
        }
    }

    function updateCitationPill(n, passed) {
        const html = answerText.innerHTML;
        const regex = new RegExp(`\\[${n}\\]`, 'g');
        
        const className = passed ? "citation-pill verified" : "citation-pill failed";
        const title = passed ? "Verified Citation" : "Failed Citation Check";
        
        if (html.includes(`[${n}]`)) {
            answerText.innerHTML = html.replace(regex, `<span class="${className}" title="${title}">${n}</span>`);
        } else {
            const pills = answerText.querySelectorAll('.citation-pill');
            pills.forEach(pill => {
                if (pill.innerText === String(n)) {
                    pill.className = className;
                    pill.title = title;
                }
            });
        }
    }
});
