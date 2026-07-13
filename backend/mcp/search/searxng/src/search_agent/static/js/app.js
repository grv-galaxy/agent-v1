const input = document.getElementById('query-input');
const btn = document.getElementById('search-btn');
const waterfall = document.getElementById('waterfall-container');
const results = document.getElementById('results-container');
const synthesisOutput = document.getElementById('synthesis-output');
const enginesInfo = document.getElementById('engines-info');
const citationMarkers = document.getElementById('citation-markers');

let ws = null;

function connectWebSocket(onOpenCallback = null) {
    if (ws) {
        ws.close();
    }
    // Assumes server runs on same host/port
    ws = new WebSocket(`ws://${window.location.host}/ws/query`);
    
    ws.onopen = () => {
        if (onOpenCallback) onOpenCallback();
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleStageEvent(data);
    };
    
    ws.onclose = () => {
        console.log("WebSocket closed");
    };
}

function resetUI() {
    waterfall.classList.remove('hidden');
    results.classList.add('hidden');
    synthesisOutput.innerHTML = '';
    citationMarkers.innerHTML = '';
    enginesInfo.innerHTML = '';
    
    document.querySelectorAll('.stage').forEach(el => {
        el.classList.remove('active', 'done');
        el.querySelector('.ms').textContent = '';
    });
}

function handleStageEvent(data) {
    if (data.error) {
        synthesisOutput.innerHTML = `<span style="color:var(--warning)">Error: ${data.error}</span>`;
        results.classList.remove('hidden');
        return;
    }

    const stage = data.stage;
    
    if (stage === 'classify' || stage === 'route' || stage === 'searxng' || stage === 'rank') {
        const el = document.getElementById(`stage-${stage}`);
        if (el) {
            el.classList.add('done');
            el.querySelector('.ms').textContent = `${data.elapsed_ms}ms`;
        }
        
        if (stage === 'searxng') {
            const used = data.engines_used.join(', ');
            const skipped = data.engines_skipped.length > 0 ? ` (Circuit broken: ${data.engines_skipped.join(', ')})` : '';
            enginesInfo.textContent = `Engines used: ${used}${skipped}`;
        }
    }
    else if (stage === 'synthesis_token') {
        results.classList.remove('hidden');
        document.getElementById('stage-synthesis').classList.add('active');
        synthesisOutput.innerHTML += data.text.replace(/\n/g, '<br>');
    }
    else if (stage === 'citation_check') {
        data.results.forEach(res => {
            const badge = document.createElement('div');
            badge.className = 'citation-badge';
            
            const icon = res.passed ? '<span class="citation-pass">✓</span>' : '<span class="citation-fail">⚠</span>';
            const status = res.passed ? 'Verified' : 'Hallucinated';
            
            badge.innerHTML = `[${res.citation_number}] ${icon} ${status}`;
            citationMarkers.appendChild(badge);
        });
    }
    else if (stage === 'done') {
        const synthEl = document.getElementById('stage-synthesis');
        synthEl.classList.remove('active');
        synthEl.classList.add('done');
        
        // We don't get exact synthesis elapsed directly sent per token, but we know it's done.
        synthEl.querySelector('.ms').textContent = `Total: ${data.total_elapsed_ms}ms`;
    }
}

function doSearch() {
    const q = input.value.trim();
    if (!q) return;
    
    resetUI();
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        connectWebSocket(() => {
            ws.send(JSON.stringify({ query: q }));
        });
    } else {
        ws.send(JSON.stringify({ query: q }));
    }
}

btn.addEventListener('click', doSearch);
input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') doSearch();
});

// Init connection
connectWebSocket();
