document.addEventListener("DOMContentLoaded", () => {
    // --- Tabs Logic ---
    const tabSearch = document.getElementById("tab-search");
    const tabHistory = document.getElementById("tab-history");
    const tabDashboard = document.getElementById("tab-dashboard");
    const viewSearch = document.getElementById("view-search");
    const viewHistory = document.getElementById("view-history");
    const viewDashboard = document.getElementById("view-dashboard");
    const historyList = document.getElementById("history-list");

    tabSearch.addEventListener("click", () => {
        tabSearch.classList.add("active");
        tabHistory.classList.remove("active");
        tabDashboard.classList.remove("active");
        viewSearch.style.display = "block";
        viewHistory.style.display = "none";
        viewDashboard.style.display = "none";
    });

    tabHistory.addEventListener("click", () => {
        tabHistory.classList.add("active");
        tabSearch.classList.remove("active");
        tabDashboard.classList.remove("active");
        viewSearch.style.display = "none";
        viewHistory.style.display = "block";
        viewDashboard.style.display = "none";
        fetchHistory();
    });

    tabDashboard.addEventListener("click", () => {
        tabDashboard.classList.add("active");
        tabSearch.classList.remove("active");
        tabHistory.classList.remove("active");
        viewSearch.style.display = "none";
        viewHistory.style.display = "none";
        viewDashboard.style.display = "block";
        fetchDashboardData();
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
        
        const sourcesContainer = document.getElementById("sources-container");
        if (sourcesContainer) {
            sourcesContainer.innerHTML = "";
            sourcesContainer.style.display = "none";
        }
        
        const telemetryDashboard = document.getElementById("telemetry-dashboard");
        if (telemetryDashboard) {
            telemetryDashboard.style.display = "none";
        }

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
            const isDeepResearch = document.getElementById("deep-search-checkbox")?.checked || false;
            ws.send(JSON.stringify({ query: query, deep_research: isDeepResearch }));
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
            case "sources_final":
                renderSourcesSection(data.sources);
                break;
            case "telemetry_dump":
                renderTelemetryDashboard(data.tool_contributions, data.llm_calls);
                break;
            case "diagnostic_trace":
                if (typeof renderDiagnosticTrace === "function") {
                    renderDiagnosticTrace(data.trace);
                }
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
        const onClickAttr = `onclick="window.highlightSourceCard(${n})"`;
        
        if (html.includes(`[${n}]`)) {
            answerText.innerHTML = html.replace(regex, `<span class="${className}" title="${title}" ${onClickAttr}>${n}</span>`);
        } else {
            const pills = answerText.querySelectorAll('.citation-pill');
            pills.forEach(pill => {
                if (pill.innerText === String(n)) {
                    pill.className = className;
                    pill.title = title;
                    pill.setAttribute("onclick", `window.highlightSourceCard(${n})`);
                }
            });
        }
    }

    function renderSourcesSection(sources) {
        const container = document.getElementById("sources-container");
        if (!container) return;
        
        if (!sources || sources.length === 0) {
            container.innerHTML = `<h3 class="sources-header">Sources</h3><div style="color: var(--text-muted); font-size: 13px; padding: 12px 0;">No verified sources found.</div>`;
            container.style.display = "flex";
            return;
        }

        let gridHtml = `<div class="sources-grid">`;
        
        sources.forEach(src => {
            const checkClass = src.citation_check_passed ? "verified" : "failed";
            const checkIcon = src.citation_check_passed ? "✓" : "⚠";
            const faviconUrl = src.favicon || `https://www.google.com/s2/favicons?domain=${src.domain}&sz=64`;
            
            gridHtml += `
                <a href="${src.url}" target="_blank" class="source-card" id="source-card-${src.citation_n}">
                    <div class="source-card-header">
                        <span class="source-card-badge">${src.citation_n}</span>
                        <img src="${faviconUrl}" alt="${src.domain} favicon" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiI+PHJlY3Qgd2lkdGg9IjE2IiBoZWlnaHQ9IjE2IiBmaWxsPSIjMmEyYTM1Ii8+PC9zdmc+'" />
                        <span class="source-card-domain">${src.domain}</span>
                    </div>
                    <div class="source-card-title">${src.title}</div>
                    <div class="source-card-footer">
                        <span>${src.published_date}</span>
                        <div class="source-card-check ${checkClass}" title="${src.citation_check_passed ? 'Citation Verified' : 'Citation Flagged'}">${checkIcon}</div>
                    </div>
                </a>
            `;
        });
        
        gridHtml += `</div>`;
        
        container.innerHTML = `
            <h3 class="sources-header">Sources</h3>
            ${gridHtml}
        `;
        container.style.display = "flex";
    }

    function renderTelemetryDashboard(tools, llms) {
        const dashboard = document.getElementById("telemetry-dashboard");
        if (!dashboard) return;
        
        const funnelContainer = document.getElementById("funnel-container");
        const llmContainer = document.getElementById("llm-panel-container");
        
        funnelContainer.innerHTML = "";
        llmContainer.innerHTML = "";
        
        // Render Tools
        (tools || []).forEach(tool => {
            const row = document.createElement("div");
            row.className = "funnel-row";
            
            const stages = [
                { name: "Called", filled: tool.called, class: "success" },
                { name: "Returned", filled: tool.returned_results, class: "success" },
                { name: "Top 8", filled: tool.survived_biencoder, class: "success" },
                { name: "Top 3", filled: tool.survived_crossencoder, class: "success" },
                { name: "Cited", filled: tool.cited_in_answer, class: tool.citation_check_passed ? "success" : "error" }
            ];
            
            let html = `<div class="funnel-source" title="${tool.source_id}">${tool.source_id}</div><div class="funnel-track">`;
            
            for (let i = 0; i < stages.length; i++) {
                const s = stages[i];
                const nodeClass = s.filled ? `filled ${s.class}` : "";
                html += `<div class="funnel-node ${nodeClass}" title="${s.name}"></div>`;
                
                if (i < stages.length - 1) {
                    const nextS = stages[i+1];
                    const lineClass = nextS.filled ? `filled ${s.class}` : "";
                    html += `<div class="funnel-line ${lineClass}"></div>`;
                }
            }
            
            html += `</div>`;
            
            let statusText = "Did not return";
            if (tool.circuit_breaker_state === "tripped") statusText = "Circuit breaker tripped";
            else if (tool.citation_check_passed) statusText = "Cited & verified";
            else if (tool.cited_in_answer) statusText = "Cited but check failed";
            else if (tool.survived_crossencoder) statusText = "Stopped at cross-encoder";
            else if (tool.survived_biencoder) statusText = "Stopped at bi-encoder";
            else if (tool.returned_results) statusText = "Stopped at returned results";
            
            html += `<div class="funnel-status">${statusText}</div>`;
            row.innerHTML = html;
            
            row.onclick = function() {
                if (typeof window.openToolTraceModal === "function") {
                    window.openToolTraceModal(tool, statusText);
                }
            };
            
            funnelContainer.appendChild(row);
        });
        
        // Render LLMs
        (llms || []).forEach(call => {
            const row = document.createElement("div");
            row.className = "llm-row";
            
            row.innerHTML = `
                <div class="llm-summary" onclick="this.parentElement.classList.toggle('expanded')">
                    <div class="llm-step">${call.step}</div>
                    <div class="llm-model">${call.model}</div>
                    <div class="llm-tokens">${call.input_tokens} in / ${call.output_tokens} out</div>
                    <div class="llm-latency">${call.elapsed_ms}ms</div>
                    <div class="llm-cost">$${(call.cost_usd || 0).toFixed(4)}</div>
                </div>
                <div class="llm-details">
                    <div class="llm-details-section">
                        <strong>System Prompt</strong>
                        <div>${escapeHtml(call.system_prompt_text)}</div>
                    </div>
                    <div class="llm-details-section">
                        <strong>User Prompt</strong>
                        <div>${escapeHtml(call.prompt_text)}</div>
                    </div>
                    <div class="llm-details-section">
                        <strong>Response</strong>
                        <div>${escapeHtml(call.response_text)}</div>
                    </div>
                </div>
            `;
            llmContainer.appendChild(row);
        });
        
        dashboard.style.display = "block";
    }

    function escapeHtml(unsafe) {
        if (!unsafe) return "";
        return String(unsafe)
             .replace(/&/g, "&amp;")
             .replace(/</g, "&lt;")
             .replace(/>/g, "&gt;")
             .replace(/"/g, "&quot;")
             .replace(/'/g, "&#039;");
    }

    // --- Dashboard Logic ---
    const dashTimeRange = document.getElementById("dash-time-range");
    const dashCategory = document.getElementById("dash-category");
    const toolLeaderboardBody = document.querySelector("#tool-leaderboard tbody");
    const llmCostTableBody = document.querySelector("#llm-cost-table tbody");

    dashTimeRange.addEventListener("change", fetchDashboardData);
    dashCategory.addEventListener("change", fetchDashboardData);

    async function fetchDashboardData() {
        const days = dashTimeRange.value;
        const category = dashCategory.value;

        toolLeaderboardBody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 20px;">Loading tool leaderboard...</td></tr>`;
        llmCostTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 20px;">Loading LLM costs...</td></tr>`;

        try {
            const [toolRes, llmRes] = await Promise.all([
                fetch(`/api/dashboard/tool-contribution?days=${days}&category=${category}`),
                fetch(`/api/dashboard/llm-calls?days=${days}&category=${category}`)
            ]);

            const toolData = await toolRes.json();
            const llmData = await llmRes.json();

            renderToolLeaderboard(toolData.data || []);
            renderLLMCostTable(llmData.data || []);

        } catch (e) {
            console.error("Failed to fetch dashboard data", e);
            toolLeaderboardBody.innerHTML = `<tr><td colspan="10" style="color: var(--error); text-align: center;">Error loading data.</td></tr>`;
            llmCostTableBody.innerHTML = `<tr><td colspan="7" style="color: var(--error); text-align: center;">Error loading data.</td></tr>`;
        }
    }

    function renderToolLeaderboard(data) {
        toolLeaderboardBody.innerHTML = "";
        
        if (data.length === 0) {
            toolLeaderboardBody.innerHTML = `<tr><td colspan="10" style="text-align: center; padding: 20px; color: var(--text-muted);">No data for this period.</td></tr>`;
            return;
        }

        data.forEach(row => {
            const tr = document.createElement("tr");
            
            let tierClass = "tier-unreliable";
            let tierLabel = "⚫ UNRELIABLE";
            if (row.tier === "Core") {
                tierClass = "tier-core";
                tierLabel = "🟢 CORE";
            } else if (row.tier === "Situational") {
                tierClass = "tier-situational";
                tierLabel = "🟡 SITUATIONAL";
            } else if (row.tier === "Show Piece") {
                tierClass = "tier-showpiece";
                tierLabel = "🔴 SHOW PIECE";
            }

            tr.innerHTML = `
                <td style="font-weight: 500;">${row.source_id}</td>
                <td><span class="tier-badge ${tierClass}">${tierLabel}</span></td>
                <td>${row.calls}</td>
                <td>${Math.round(row.avg_latency)}ms</td>
                <td>${Math.round(row.return_rate * 100)}%</td>
                <td>${Math.round(row.top8_rate * 100)}%</td>
                <td>${Math.round(row.top3_rate * 100)}%</td>
                <td><strong style="color: var(--accent);">${Math.round(row.cited_rate * 100)}%</strong></td>
                <td>${Math.round(row.citation_pass_rate * 100)}%</td>
                <td style="${row.breaker_trips > 0 ? 'color: var(--error);' : ''}">${row.breaker_trips}</td>
            `;
            toolLeaderboardBody.appendChild(tr);
        });
    }

    function renderLLMCostTable(data) {
        llmCostTableBody.innerHTML = "";

        if (data.length === 0) {
            llmCostTableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 20px; color: var(--text-muted);">No data for this period.</td></tr>`;
            return;
        }

        data.forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td style="font-weight: 500;">${row.step}</td>
                <td>${row.calls}</td>
                <td>${Math.round(row.avg_input_tokens)}</td>
                <td>${Math.round(row.avg_output_tokens)}</td>
                <td>${Math.round(row.avg_latency)}ms</td>
                <td style="color: #4ade80;">$${(row.total_cost || 0).toFixed(4)}</td>
                <td>$${(row.avg_cost_per_call || 0).toFixed(4)}</td>
            `;
            llmCostTableBody.appendChild(tr);
        });
    }

});

// Global function so it can be called from onclick handlers in the HTML string
window.highlightSourceCard = function(n) {
    const card = document.getElementById(`source-card-${n}`);
    if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Remove the class if it already exists to restart animation
        card.classList.remove('highlight-pulse');
        // Trigger reflow
        void card.offsetWidth;
        // Add the class
        card.classList.add('highlight-pulse');
        
        // Remove it after the animation completes (1.5s)
        setTimeout(() => {
            if (card) {
                card.classList.remove('highlight-pulse');
            }
        }, 1500);
    }
};

window.openToolTraceModal = function(tool, statusText) {
    const modal = document.getElementById('tool-trace-modal');
    if (!modal) return;
    
    document.getElementById('modal-tool-name').textContent = tool.source_id;
    document.getElementById('modal-status').textContent = statusText;
    
    document.getElementById('modal-bi-rank').textContent = tool.bi_rank || '-';
    document.getElementById('modal-bi-score').textContent = tool.bi_score !== undefined ? tool.bi_score : '-';
    
    document.getElementById('modal-cross-rank').textContent = tool.cross_rank || '-';
    document.getElementById('modal-cross-score').textContent = tool.cross_score !== undefined ? tool.cross_score : '-';
    
    const rawCode = document.getElementById('modal-raw-content');
    if (tool.raw_content) {
        rawCode.textContent = tool.raw_content;
    } else {
        rawCode.textContent = 'No data returned.';
    }
    
    modal.style.display = 'block';
};

document.addEventListener('DOMContentLoaded', () => {
    const traceModal = document.getElementById('tool-trace-modal');
    const traceModalClose = document.getElementById('modal-close');
    if (traceModalClose) {
        traceModalClose.onclick = function() {
            if(traceModal) traceModal.style.display = 'none';
        };
    }
    window.addEventListener('click', function(event) {
        if (event.target == traceModal) {
            traceModal.style.display = 'none';
        }
    });
});
