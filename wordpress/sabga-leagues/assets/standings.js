(function () {
    'use strict';
    const columns = ['position', 'player', 'played', 'points', 'points_percentage',
        'wins', 'pr_wins', 'h2h', 'average_pr', 'losses', 'win_percentage', 'average_luck'];
    const decimal = new Set(['points_percentage', 'win_percentage', 'average_pr', 'average_luck']);
    const percentages = new Set(['points_percentage', 'win_percentage']);

    function cell(key, row) {
        if (key === 'player') return row.name + (row.nickname ? ' (' + row.nickname + ')' : '');
        if (row[key] === null || row[key] === undefined) return '—';
        return decimal.has(key) ? Number(row[key]).toFixed(2) + (percentages.has(key) ? '%' : '') : String(row[key]);
    }

    document.querySelectorAll('.sabga-leagues').forEach(function (root) {
        const select = root.querySelector('select');
        const form = root.querySelector('form');
        const status = root.querySelector('.sabga-leagues__status');
        const error = root.querySelector('.sabga-leagues__error');
        const table = root.querySelector('table');
        let sequence = 0;
        let controller;
        // Public payload is always revalidated through the endpoint. This also
        // prevents a page-cache copy from staying stale after a result update.
        function render(data) {
            const summary = data.summary;
            root.querySelector('[data-metric="progress"]').textContent = summary ? summary.completed + ' / ' + summary.total : '—';
            root.querySelector('[data-metric="outstanding"]').textContent = summary ? summary.outstanding : '—';
            root.querySelector('[data-metric="average_pr"]').textContent = summary && summary.average_pr !== null ? Number(summary.average_pr).toFixed(2) : '—';
            root.querySelector('[data-metric="deadline"]').textContent = data.deadline || '—';
            root.querySelector('.sabga-leagues__summary-warning').hidden = !!summary;
            const body = document.createElement('tbody');
            data.standings.forEach(function (row) {
                const tr = document.createElement('tr');
                columns.forEach(function (key) {
                    const el = document.createElement(key === 'player' ? 'th' : 'td');
                    if (key === 'player') el.scope = 'row';
                    el.textContent = cell(key, row);
                    tr.appendChild(el);
                });
                body.appendChild(tr);
            });
            table.querySelector('tbody').replaceWith(body);
            table.querySelector('caption').textContent = 'Standings for ' + data.group;
            root.querySelector('.sabga-leagues__group').textContent = data.group;
            root.querySelector('.sabga-leagues__demo').hidden = data.mode !== 'demo';
            root.querySelector('.sabga-leagues__empty').hidden = data.standings.length !== 0;
            root.querySelector('.sabga-leagues__warning').hidden = !data.standings.some(row => !row.stats_available);
            const timestamp = new Date(data.fetched_at);
            root.querySelector('.sabga-leagues__timestamp').textContent =
                'Standings fetched ' + timestamp.toLocaleString() +
                (data.mode === 'live' ? ' · Website cache: up to ' + data.cache_seconds + ' seconds' : ' · Demo data');
        }

        async function load(updateLink) {
            const current = ++sequence;
            if (controller) controller.abort();
            const requestController = new AbortController();
            controller = requestController;
            const timeout = setTimeout(() => requestController.abort(), 12000);
            root.setAttribute('aria-busy', 'true');
            error.hidden = true;
            status.textContent = 'Loading ' + select.options[select.selectedIndex].text + '…';
            try {
                const endpoint = new URL(root.dataset.endpoint, window.location.href);
                endpoint.searchParams.set('group', select.value);
                const response = await fetch(endpoint.toString(), {signal: requestController.signal, cache: 'no-store', credentials: 'same-origin'});
                const data = await response.json();
                if (!response.ok) throw new Error(data.message || 'Standings could not be loaded.');
                if (current !== sequence) return;
                render(data);
                status.textContent = data.group + ' loaded.';
                if (updateLink) {
                    const url = new URL(window.location.href);
                    url.searchParams.set('sabga_group', select.value);
                    window.history.replaceState(null, '', url.toString());
                }
            } catch (exception) {
                if (current !== sequence) return;
                root.querySelectorAll('[data-metric]').forEach(el => { el.textContent = '—'; });
                root.querySelector('.sabga-leagues__summary-warning').hidden = true;
                // Remove old rows, so they cannot be mistaken for the new group.
                table.querySelector('tbody').replaceChildren();
                root.querySelector('.sabga-leagues__group').textContent = select.options[select.selectedIndex].text;
                root.querySelector('.sabga-leagues__timestamp').textContent = '';
                root.querySelector('.sabga-leagues__warning').hidden = true;
                root.querySelector('.sabga-leagues__empty').hidden = true;
                error.textContent = exception.name === 'AbortError' ? 'The request timed out. Choose Show standings to try again.' : exception.message;
                error.hidden = false;
                status.textContent = 'Standings unavailable.';
            } finally {
                clearTimeout(timeout);
                if (current === sequence) root.setAttribute('aria-busy', 'false');
            }
        }
        select.addEventListener('change', () => load(true));
        form.addEventListener('submit', function (event) { event.preventDefault(); load(true); });
        load(false);
    });
})();
