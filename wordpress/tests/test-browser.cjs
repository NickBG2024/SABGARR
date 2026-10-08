// Browser behaviour tests against PHP-rendered markup and PHP-generated payloads.
// Deliberately independent of WordPress hosting or production league data.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert');

(async () => {
    const binary = process.env.CHROMIUM_EXECUTABLE_PATH;
    const browser = await chromium.launch({headless:true, executablePath:binary || undefined,
        args:['--no-sandbox', '--disable-dev-shm-usage']});
    const page = await browser.newPage({viewport:{width:1280,height:900}});
    let mode = 'normal';
    let requests = [];
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/api/sabga-leagues/v1/standings?*', async route => {
        const group = new URL(route.request().url()).searchParams.get('group');
        requests.push(group);
        if (mode === 'failure') return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({message:'Test connection unavailable.'})});
        if (mode === 'race' && group === '92') await new Promise(resolve=>setTimeout(resolve,150));
        const payload = JSON.parse(fs.readFileSync(path.join(__dirname, 'payload-' + group + '.json'),'utf8'));
        if (mode === 'injection') payload.standings[0].name = '<img src=x onerror="window.injected=true">';
        await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload)}).catch(()=>{});
    });
    await page.goto('http://127.0.0.1:8765/tests/preview.html');
    await page.getByRole('status').filter({hasText:'A-League loaded.'}).waitFor();
    assert.equal(await page.locator('tbody tr').count(),8);
    assert.equal(await page.locator('.sabga-leagues__demo').isVisible(),true);
    assert.equal(await page.locator('select option').count(),11);
    assert.equal(await page.locator('tbody tr').nth(6).locator('td').nth(7).innerText(),'—');
    for (const id of ['92','93','94','95','96','97','98','100','99','101','91']) {
        await page.locator('select').selectOption(id);
        await page.waitForFunction(() => document.querySelector('.sabga-leagues').getAttribute('aria-busy')==='false');
        assert.equal(new URL(page.url()).searchParams.get('sabga_group'),id);
        assert.equal(await page.locator('tbody tr').count(),8);
    }
    mode = 'race';
    await page.locator('select').selectOption('92');
    await page.locator('select').selectOption('93');
    await page.waitForFunction(()=>document.querySelector('.sabga-leagues__group').textContent==='C-League' && document.querySelector('.sabga-leagues').getAttribute('aria-busy')==='false');
    assert.equal(await page.locator('.sabga-leagues__group').innerText(),'C-League');
    mode = 'injection';
    await page.getByRole('button',{name:'Show standings'}).click();
    await page.waitForFunction(()=>document.querySelector('tbody th').textContent.includes('<img'));
    assert.equal(await page.locator('tbody img').count(),0);
    assert.equal(await page.evaluate(()=>window.injected),undefined);
    mode = 'failure';
    await page.locator('select').selectOption('94');
    await page.locator('.sabga-leagues__error').waitFor({state:'visible'});
    assert.equal(await page.locator('tbody tr').count(),0);
    assert.equal(await page.locator('.sabga-leagues__error').innerText(),'Test connection unavailable.');
    mode = 'normal';
    await page.getByRole('button',{name:'Show standings'}).click();
    await page.waitForFunction(()=>document.querySelector('tbody').children.length===8);
    assert.equal(await page.locator('.sabga-leagues__error').isVisible(),false);
    await page.setViewportSize({width:390,height:844});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
    assert.equal(await page.locator('.sabga-leagues__scroll').evaluate(el=>el.scrollWidth>el.clientWidth),true);
    await page.locator('.sabga-leagues__scroll').evaluate(el=>{el.scrollLeft=200;});
    assert.ok(await page.locator('.sabga-leagues__scroll').evaluate(el=>el.scrollLeft)>0);
    await page.locator('.sabga-leagues__scroll').evaluate(el=>{el.scrollLeft=0;});
    await page.screenshot({path:path.join(__dirname,'mobile-preview.png'),fullPage:true});
    await page.setViewportSize({width:1280,height:900});
    await page.screenshot({path:path.join(__dirname,'desktop-preview.png'),fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('PASS: all 11 selectors, rows, missing PR, share links, rapid-switch race, XSS text escaping, failure/retry, mobile overflow and no browser errors ('+requests.length+' API requests)');
    await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
