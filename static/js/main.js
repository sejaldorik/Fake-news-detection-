document.addEventListener('DOMContentLoaded', () => {
    // Tab Switching Logic
    const tabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const inputTypeField = document.getElementById('input-type');

    if(tabs.length > 0) {
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                // Remove active classes
                tabs.forEach(t => t.classList.remove('active'));
                tabContents.forEach(c => c.style.display = 'none');
                
                // Add active class
                tab.classList.add('active');
                const target = document.getElementById(tab.dataset.target);
                target.style.display = 'block';
                
                // Set hidden input
                inputTypeField.value = tab.dataset.target.split('-')[0];
            });
        });
    }

    // Form Submission
    const verifyForm = document.getElementById('verify-form');
    if(verifyForm) {
        verifyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btn = document.getElementById('verify-btn');
            const btnText = btn.querySelector('.btn-text');
            const loader = btn.querySelector('.loader');
            const resultPanel = document.getElementById('result-panel');
            
            // UI Loading state
            btn.disabled = true;
            btnText.style.display = 'none';
            loader.style.display = 'inline-block';
            resultPanel.style.display = 'none';
            
            try {
                const formData = new FormData(verifyForm);
                const response = await fetch('/api/predict', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                    }
                });
                
                const data = await response.json();
                
                if(!response.ok) {
                    alert(data.error || 'An error occurred during prediction.');
                    return;
                }
                
                // Process Data
                renderResult(data);
                
            } catch (err) {
                console.error(err);
                alert("Failed to connect to server.");
            } finally {
                btn.disabled = false;
                btnText.style.display = 'inline-block';
                loader.style.display = 'none';
            }
        });
    }

    // Export PDF Logic
    const exportBtn = document.getElementById('export-pdf-btn');
    if(exportBtn) {
        exportBtn.addEventListener('click', () => {
            const element = document.getElementById('export-content');
            
            // Expand the UI for better fitting in PDF before printing
            const origPadding = element.style.padding;
            element.style.padding = '30px';
            element.style.color = '#fff';
            
            const opt = {
                margin:       [0.5, 0.5, 0.5, 0.5],
                filename:     'Verification_Report.pdf',
                image:        { type: 'jpeg', quality: 0.98 },
                html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#0f172a' },
                jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
            };
            
            html2pdf().set(opt).from(element).save().then(() => {
                element.style.padding = origPadding;
            });
        });
    }

    // Load Dashboard Data 
    if(document.getElementById('pieChart') || document.getElementById('history-container')) {
        loadDashboardData();
    }
});

let pieChartInstance = null;
let barChartInstance = null;
let timelineChartInstance = null;
let scatterChartInstance = null;

function renderResult(data) {
    const panel = document.getElementById('result-panel');
    const predTag = document.getElementById('main-prediction');
    const confVal = document.getElementById('confidence-val');
    const wordCloud = document.getElementById('word-cloud');
    
    // Set Timestamp and Snippet for the PDF export
    const tstampObj = new Date();
    document.getElementById('report-timestamp').innerText = "Generated on: " + tstampObj.toLocaleString();
    
    // Snippet and Type
    const inputType = document.getElementById('input-type').value;
    document.getElementById('report-input-type').innerText = inputType;
    let snippet = data.cleaned_text || "Unavailable";
    if (snippet.length > 200) snippet = snippet.substring(0, 200) + '...';
    document.getElementById('report-snippet').innerText = snippet;

    panel.style.display = 'block';
    
    // Set Prediction
    predTag.innerText = data.prediction + " News";
    predTag.className = 'prediction-tag ' + (data.prediction === 'Fake' ? 'pred-fake' : 'pred-true');
    
    // Set Confidence
    const confPct = Math.round(data.confidence * 100);
    confVal.innerText = confPct + "%";
    
    // Set Explainability (LIME words)
    wordCloud.innerHTML = '';
    if(data.explanation && data.explanation.length > 0) {
        data.explanation.forEach(exp => {
            const word = exp[0];
            const weight = exp[1];
            const isFakeIndicator = weight > 0;
            const cls = isFakeIndicator ? 'word-fake' : 'word-true';
            
            const span = document.createElement('span');
            span.className = `word-tag ${cls}`;
            span.innerText = `${word} (${Math.abs(weight).toFixed(2)})`;
            wordCloud.appendChild(span);
        });
    } else {
        wordCloud.innerText = 'Explainability data unavailable.';
    }
}

async function loadDashboardData() {
    try {
        const res = await fetch('/api/dashboard_data');
        if(!res.ok) return;
        const data = await res.json();
        
        // Update Stats if elements exist
        const stTotal = document.getElementById('stat-total');
        if(stTotal) stTotal.innerText = data.stats.total;
        
        const stFake = document.getElementById('stat-fake');
        if(stFake) stFake.innerText = data.stats.fake;
        
        // Render History
        const hc = document.getElementById('history-container');
        if(hc) {
            hc.innerHTML = '';
            data.history.forEach(h => {
                const div = document.createElement('div');
                div.className = 'history-item';
                div.innerHTML = `
                    <div>
                        <p><strong>${h.input_type.toUpperCase()}</strong>: ${h.snippet.substring(0, 50)}...</p>
                        <small style="color:var(--text-muted)">${h.timestamp}</small>
                    </div>
                    <div style="color: ${h.prediction === 'Fake' ? 'var(--danger)' : 'var(--success)'}; font-weight:bold;">
                        ${h.prediction} (${Math.round(h.confidence*100)}%)
                    </div>
                `;
                hc.appendChild(div);
            });
        }
        
        // Render Charts logic
        if(document.getElementById('pieChart')) {
            renderCharts(data.stats, data.timeline, data.history);
        }
        
    } catch(err) {
        console.error("Dashboard data load error:", err);
    }
}

function renderCharts(stats, timeline, historyData) {
    if(stats.total === 0) return; // avoid drawing empty charts

    /************** 1. Bar Chart (Fake vs True Count) **************/
    const barCtx = document.getElementById('barChart').getContext('2d');
    if(barChartInstance) barChartInstance.destroy();
    
    barChartInstance = new Chart(barCtx, {
        type: 'bar',
        data: {
            labels: ['Fake', 'True'],
            datasets: [{
                label: 'Total Detection Count',
                data: [stats.fake, stats.true],
                backgroundColor: ['rgba(239, 68, 68, 0.7)', 'rgba(16, 185, 129, 0.7)'],
                borderColor: ['#ef4444', '#10b981'],
                borderWidth: 1
            }]
        },
        options: {
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 } },
                x: { ticks: { color: '#94a3b8' } }
            }
        }
    });

    /************** 2. Pie Chart (% Distribution) **************/
    const pieCtx = document.getElementById('pieChart').getContext('2d');
    if(pieChartInstance) pieChartInstance.destroy();
    
    const total = stats.fake + stats.true;
    const fakePct = total > 0 ? ((stats.fake / total) * 100).toFixed(1) : 0;
    const truePct = total > 0 ? ((stats.true / total) * 100).toFixed(1) : 0;
    
    pieChartInstance = new Chart(pieCtx, {
        type: 'pie',
        data: {
            labels: [`Fake (${fakePct}%)`, `True (${truePct}%)`],
            datasets: [{
                data: [stats.fake, stats.true],
                backgroundColor: ['#ef4444', '#10b981'],
                borderWidth: 0
            }]
        },
        options: {
            plugins: {
                legend: { labels: { color: '#f8fafc' } }
            }
        }
    });

    /************** 3. Confidence Score Visualization (Scatter/Line) **************/
    // Will chart the last 15 elements chronologically for confidence
    const confCtx = document.getElementById('scatterChart').getContext('2d');
    if(scatterChartInstance) scatterChartInstance.destroy();
    
    // Reverse to go oldest to newest for visual flow
    let histRev = [...historyData].reverse();
    // take last 20
    if (histRev.length > 20) histRev = histRev.slice(-20);
    
    const confLabels = histRev.map((_, i) => `Check ${i+1}`);
    const confValuesFake = histRev.map(h => h.prediction === 'Fake' ? Math.round(h.confidence*100) : null);
    const confValuesTrue = histRev.map(h => h.prediction === 'True' ? Math.round(h.confidence*100) : null);

    scatterChartInstance = new Chart(confCtx, {
        type: 'line',
        data: {
            labels: confLabels,
            datasets: [
                {
                    label: 'Fake Confidence %',
                    data: confValuesFake,
                    borderColor: '#ef4444',
                    backgroundColor: '#ef4444',
                    showLine: false,
                    pointRadius: 6
                },
                {
                    label: 'True Confidence %',
                    data: confValuesTrue,
                    borderColor: '#10b981',
                    backgroundColor: '#10b981',
                    showLine: false,
                    pointRadius: 6
                }
            ]
        },
        options: {
            plugins: { legend: { labels: { color: '#f8fafc' } } },
            scales: {
                y: { min: 40, max: 100, ticks: { color: '#94a3b8' } },
                x: { ticks: { color: '#94a3b8' } }
            }
        }
    });

    /************** 4. Trend Analysis Line Chart **************/
    const lineCtx = document.getElementById('timelineChart').getContext('2d');
    if(timelineChartInstance) timelineChartInstance.destroy();
    
    const dates = Object.keys(timeline).sort();
    const fakeData = dates.map(d => timeline[d]['Fake'] || 0);
    const trueData = dates.map(d => timeline[d]['True'] || 0);

    timelineChartInstance = new Chart(lineCtx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Fake Count',
                    data: fakeData,
                    borderColor: '#ef4444',
                    tension: 0.1
                },
                {
                    label: 'True Count',
                    data: trueData,
                    borderColor: '#10b981',
                    tension: 0.1
                }
            ]
        },
        options: {
            plugins: { legend: { labels: { color: '#f8fafc' } } },
            scales: {
                x: { ticks: { color: '#94a3b8' } },
                y: { beginAtZero: true, ticks: { color: '#94a3b8', stepSize: 1 } }
            }
        }
    });
}
