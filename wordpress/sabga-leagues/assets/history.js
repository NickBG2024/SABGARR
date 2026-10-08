(function () {
    'use strict';
    document.querySelectorAll('.sabga-history').forEach(function (root) {
        const form = root.querySelector('.sabga-history__report-form');
        const report = root.querySelector('.sabga-history__report');
        const status = root.querySelector('.sabga-history__status');
        let controller, sequence = 0;
        function render(data) {
            report.replaceChildren();
            const note = document.createElement('p');
            note.className = 'sabga-history__note'; note.textContent = data.note; report.appendChild(note);
            if (!data.rows.length) {
                const empty = document.createElement('p'); empty.textContent = 'No records found for this selection.';
                report.appendChild(empty); return;
            }
            const scroll = document.createElement('div');
            scroll.className = 'sabga-history__scroll'; scroll.tabIndex = 0;
            scroll.setAttribute('role', 'region'); scroll.setAttribute('aria-label', 'Historical records table; scroll for more columns');
            const table = document.createElement('table');
            const caption = document.createElement('caption'); caption.textContent = 'Historical records';
            caption.className = 'sabga-history__sr-only'; table.appendChild(caption);
            const head = document.createElement('thead'), header = document.createElement('tr');
            data.columns.forEach(label => { const cell = document.createElement('th'); cell.scope = 'col'; if (['Player','League','Series'].includes(label)) cell.className = 'sabga-history__text'; cell.textContent = label; header.appendChild(cell); });
            head.appendChild(header); table.appendChild(head);
            const body = document.createElement('tbody');
            data.rows.forEach(row => { const tr = document.createElement('tr'); row.forEach((value, i) => {
                const cell = document.createElement(i === 0 ? 'th' : 'td');
                if (i === 0) cell.scope = 'row'; if (['Player','League','Series'].includes(data.columns[i])) cell.className = 'sabga-history__text'; cell.textContent = value; tr.appendChild(cell);
            }); body.appendChild(tr); });
            table.appendChild(body); scroll.appendChild(table); report.appendChild(scroll);
        }
        async function load(updateLink) {
            const current = ++sequence;
            if (controller) controller.abort();
            const request = new AbortController(); controller = request;
            const timeout = setTimeout(() => request.abort(), 12000);
            root.setAttribute('aria-busy', 'true'); status.textContent = 'Loading records…';
            const query = form ? new URLSearchParams(new FormData(form)) : new URLSearchParams(JSON.parse(root.dataset.selection));
            try {
                const endpoint = new URL(root.dataset.endpoint, window.location.href);
                for (const [key, value] of query) {
                    if (key.startsWith('sabga_history_')) endpoint.searchParams.set(key.slice(14), value);
                }
                const response = await fetch(endpoint.toString(), {signal:request.signal, credentials:'same-origin', cache:'no-store'});
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || 'Records could not be loaded.');
                if (current !== sequence) return;
                render(data); status.textContent = 'Records loaded.';
                if (updateLink) {
                    const url = new URL(window.location.href);
                    for (const [key, value] of query) { if (key.startsWith('sabga_history_')) url.searchParams.set(key, value); }
                    window.history.replaceState(null, '', url.toString());
                }
            } catch (error) {
                if (current !== sequence) return;
                report.replaceChildren();
                const message = document.createElement('p'); message.setAttribute('role', 'alert');
                message.textContent = error.name === 'AbortError' ? 'The request timed out. Choose Show standings or Show player to retry.' : error.message;
                report.appendChild(message); status.textContent = 'Records unavailable.';
            } finally {
                clearTimeout(timeout); if (current === sequence) root.setAttribute('aria-busy', 'false');
            }
        }
        if (form) {
            form.addEventListener('submit', event => { event.preventDefault(); load(true); });
            form.querySelector('select').addEventListener('change', () => load(true));
        }
        load(false);
    });
})();
