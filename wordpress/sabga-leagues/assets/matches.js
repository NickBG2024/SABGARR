(function () {
    'use strict';
    document.querySelectorAll('.sabga-matches').forEach(function (panel) {
        const root = panel.closest('.sabga-leagues, .sabga-history');
        const context = JSON.parse(panel.dataset.context);
        const isCurrent = context.scope === 'current';
        const standings = root.querySelector(isCurrent ? '.sabga-leagues__standings-panel' : '.sabga-history__report');
        const links = root.querySelectorAll('[data-match-view]');
        const group = root.querySelector(isCurrent ? '.sabga-leagues__controls select' : '.sabga-history__report-form select');
        const form = panel.querySelector('form'), player = form.querySelector('select');
        const report = panel.querySelector('.sabga-matches__report'), status = panel.querySelector('.sabga-matches__status');
        const viewKey = isCurrent ? 'sabga_view' : 'sabga_history_view';
        const groupKey = isCurrent ? 'sabga_group' : 'sabga_history_group';
        let view = panel.dataset.view, sequence = 0, controller;
        function updateLinks() {
            links.forEach(link => {
                const url = new URL(link.href, window.location.href); url.searchParams.set(groupKey, context.group);
                url.searchParams.delete(isCurrent ? 'sabga_match_player' : 'sabga_history_match_player'); link.href = url.toString();
                if (link.dataset.matchView === view) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
            });
            form.querySelector('[name="' + groupKey + '"]').value = context.group;
            form.querySelector('[name="' + viewKey + '"]').value = view;
        }
        function updateUrl() {
            const url = new URL(window.location.href); url.searchParams.set(viewKey, view); url.searchParams.set(groupKey, context.group);
            url.searchParams.set(player.name, player.value); window.history.replaceState(null, '', url.toString());
        }
        function render(data) {
            const chosen = String(data.player); player.replaceChildren(new Option('All players', '0'));
            data.players.forEach(p => player.add(new Option(p.label, String(p.id)))); player.value = chosen;
            report.replaceChildren();
            const count = document.createElement('p'); count.textContent = data.count + ' of ' + data.total + ' matches'; report.appendChild(count);
            const note = document.createElement('p'); note.className = 'sabga-matches__note'; note.textContent = data.note; report.appendChild(note);
            if (!data.rows.length) { const empty = document.createElement('p'); empty.textContent = data.empty; report.appendChild(empty); return; }
            const scroll = document.createElement('div'); scroll.className = 'sabga-matches__scroll'; scroll.tabIndex = 0;
            scroll.setAttribute('role','region'); scroll.setAttribute('aria-label','Fixtures and results; scroll for more columns');
            const table = document.createElement('table'), caption = document.createElement('caption'); caption.textContent = 'League matches'; table.appendChild(caption);
            const head = document.createElement('thead'), tr = document.createElement('tr');
            data.columns.forEach(label => { const th = document.createElement('th'); th.scope='col'; th.textContent=label; tr.appendChild(th); });
            head.appendChild(tr); table.appendChild(head); const body = document.createElement('tbody');
            data.rows.forEach(row => { const tr = document.createElement('tr'); row.forEach(value => { const td = document.createElement('td'); td.textContent=value; tr.appendChild(td); }); body.appendChild(tr); });
            table.appendChild(body); scroll.appendChild(table); report.appendChild(scroll);
        }
        async function load(updateLink) {
            const current = ++sequence; if (controller) controller.abort();
            const request = new AbortController(); controller = request; const timeout = setTimeout(() => request.abort(),12000);
            panel.setAttribute('aria-busy','true'); status.textContent='Loading matches…'; report.replaceChildren();
            try {
                const url = new URL(panel.dataset.endpoint,window.location.href);
                Object.entries(context).forEach(([key,value]) => url.searchParams.set(key,value));
                url.searchParams.set('view',view); url.searchParams.set('player',player.value);
                const response = await fetch(url.toString(),{signal:request.signal,cache:'no-store',credentials:'same-origin'});
                const data = await response.json(); if (!response.ok) throw new Error(data.message || 'Matches could not be loaded.');
                if (current !== sequence) return; render(data); status.textContent='Matches loaded.'; if(updateLink) updateUrl();
            } catch(error) {
                if (current !== sequence) return; report.replaceChildren(); const message=document.createElement('p'); message.setAttribute('role','alert');
                message.textContent=error.name==='AbortError'?'The request timed out. Choose Show matches to retry.':error.message;
                report.appendChild(message);status.textContent='Matches unavailable.';
            } finally { clearTimeout(timeout); if(current===sequence)panel.setAttribute('aria-busy','false'); }
        }
        function show(next, updateLink) {
            view=next; panel.dataset.view=view; ++sequence; if(controller)controller.abort(); panel.setAttribute('aria-busy','false');
            standings.hidden=view!=='standings'; panel.hidden=view==='standings'; updateLinks();
            panel.querySelector('.sabga-matches__heading').textContent=view==='results'?'Results':'Remaining Fixtures';
            if(view!=='standings')load(updateLink);else if(updateLink)updateUrl();
        }
        links.forEach(link => link.addEventListener('click',event => {
            if(event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button!==0)return;
            event.preventDefault();show(link.dataset.matchView,true);
        }));
        form.addEventListener('submit',event=>{event.preventDefault();load(true);}); player.addEventListener('change',()=>load(true));
        if(group) group.addEventListener('change',()=>{
            context.group=Number(group.value);player.replaceChildren(new Option('All players','0'));report.replaceChildren();updateLinks();
            if(view!=='standings')load(true);
        });
        show(view,false);
    });
})();
