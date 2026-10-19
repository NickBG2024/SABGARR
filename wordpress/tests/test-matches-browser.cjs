const {chromium}=require('playwright');
const {execFileSync}=require('child_process');
const path=require('path'),assert=require('assert');
const php=process.env.SABGA_TEST_PHP || 'php', harness=path.join(__dirname,'test-plugin.php');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1280,height:950}});
 let failure=false,race=false,injection=false;const errors=[];page.on('pageerror',e=>errors.push(e.message));
 async function install(p){
  await p.route('**/tests/preview.html*',route=>route.fulfill({status:200,contentType:'text/html',body:execFileSync(php,[harness,'--render',new URL(route.request().url()).searchParams.toString()],{encoding:'utf8'})}));
  await p.route('**/tests/history-preview.html*',route=>route.fulfill({status:200,contentType:'text/html',body:execFileSync(php,[harness,'--render-history',new URL(route.request().url()).searchParams.toString() || 'standings'],{encoding:'utf8'})}));
  await p.route('**/api/sabga-leagues/v1/standings?*',route=>route.fulfill({status:200,contentType:'application/json',body:execFileSync(php,[harness,'--payload',new URL(route.request().url()).searchParams.get('group')],{encoding:'utf8'})}));
  await p.route('**/api/sabga-leagues/v1/history?*',route=>route.fulfill({status:200,contentType:'application/json',body:execFileSync(php,[harness,'--history-report',JSON.stringify(Object.fromEntries(new URL(route.request().url()).searchParams))],{encoding:'utf8'})}));
  await p.route('**/api/sabga-leagues/v1/matches?*',async route=>{
   if(failure)return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({message:'Match test unavailable.'})});
   const input=Object.fromEntries(new URL(route.request().url()).searchParams);
   if(race && input.view==='remaining')await new Promise(resolve=>setTimeout(resolve,180));
   const data=JSON.parse(execFileSync(php,[harness,'--matches-report',JSON.stringify(input)],{encoding:'utf8'}));
   if(injection){data.rows[0][0]='<img src=x onerror=alert(1)>';data.players[0].label='<script>bad</script>';}
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)}).catch(()=>{});
  });
 }
 await install(page);await page.goto('http://127.0.0.1:8765/tests/preview.html');
 assert.equal(await page.locator('.sabga-matches').isVisible(),false);
 await page.getByRole('link',{name:'Remaining Fixtures',exact:true}).click();
 await page.locator('.sabga-matches__status').filter({hasText:'Matches loaded.'}).waitFor();
 assert.equal(await page.locator('.sabga-leagues__standings-panel').isVisible(),false);
 assert.equal(await page.locator('.sabga-matches tbody tr').count(),2);
 await page.getByLabel('Filter by player').selectOption('3');
 await page.waitForFunction(()=>document.querySelector('.sabga-matches tbody')?.children.length===1);
 assert.equal(await page.locator('.sabga-matches__report > p').first().innerText(),'1 of 2 matches');
 // Switching groups resets the player filter, and keeps the current match view.
 await page.getByLabel('League group',{exact:true}).selectOption('92');
 await page.waitForFunction(()=>document.querySelector('.sabga-matches tbody')?.children.length===2);
 assert.equal(await page.getByLabel('Filter by player').inputValue(),'0');
 await page.getByRole('link',{name:'Results',exact:true}).click();
 await page.getByRole('columnheader',{name:'PR 1',exact:true}).waitFor();
 assert.equal(await page.locator('.sabga-matches tbody td').nth(2).innerText(),'8 – 11');
 assert.equal(await page.locator('.sabga-matches tbody td').nth(4).innerText(),'—');
 await page.getByLabel('Filter by player').selectOption('3');
 await page.getByText('No recorded results for this selection.',{exact:true}).waitFor();
 failure=true;await page.getByLabel('Filter by player').selectOption('0');await page.locator('.sabga-matches [role="alert"]').waitFor();
 assert.equal(await page.locator('.sabga-matches tbody').count(),0);
 failure=false;injection=true;await page.getByRole('button',{name:'Show matches',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.sabga-matches tbody td')?.textContent.includes('<img'));
 assert.equal(await page.locator('.sabga-matches img,.sabga-matches script').count(),0);
 injection=false;race=true;await page.getByRole('link',{name:'Remaining Fixtures',exact:true}).click();await page.getByRole('link',{name:'Results',exact:true}).click();
 await page.getByRole('columnheader',{name:'PR 1',exact:true}).waitFor();
 await page.waitForTimeout(220);assert.equal(await page.locator('.sabga-matches__heading').innerText(),'Results');
 await page.getByRole('link',{name:'Standings',exact:true}).click();assert.equal(await page.locator('.sabga-matches').isVisible(),false);
 assert.equal(await page.locator('.sabga-leagues__standings-panel').isVisible(),true);
 race=false;
 await page.goto('http://127.0.0.1:8765/tests/history-preview.html');
 await page.getByRole('link',{name:'Remaining Fixtures',exact:true}).click();
 await page.locator('.sabga-matches__status').filter({hasText:'Matches loaded.'}).waitFor();
 assert.ok((await page.locator('.sabga-matches__note').innerText()).includes('previous series'));
 await page.getByLabel('League group',{exact:true}).selectOption('122');
 await page.waitForFunction(()=>document.querySelector('.sabga-matches').getAttribute('aria-busy')==='false');
 assert.equal(new URL(page.url()).searchParams.get('sabga_history_group'),'122');
 await page.getByRole('link',{name:'Results',exact:true}).click();await page.getByRole('columnheader',{name:'PR 1',exact:true}).waitFor();
 await page.screenshot({path:path.join(__dirname,'matches-desktop-preview.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 await page.screenshot({path:path.join(__dirname,'matches-mobile-preview.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 // Ordinary links/filter forms remain usable without JavaScript.
 const plain=await browser.newPage({javaScriptEnabled:false});await install(plain);
 await plain.goto('http://127.0.0.1:8765/tests/preview.html');
 await plain.getByRole('link',{name:'Remaining Fixtures',exact:true}).click();assert.equal(await plain.locator('.sabga-matches tbody tr').count(),2);
 await plain.getByLabel('Filter by player').selectOption('3');await plain.getByRole('button',{name:'Show matches',exact:true}).click();
 assert.equal(await plain.locator('.sabga-matches tbody tr').count(),1);
 await plain.goto('http://127.0.0.1:8765/tests/history-preview.html');await plain.getByRole('link',{name:'Results',exact:true}).click();
 assert.equal(await plain.getByRole('columnheader',{name:'PR 1',exact:true}).count(),1);
 console.log('PASS: current/historical match tabs, player filtering/reset, score/PR alignment, empty state, errors/retry, race cancellation, XSS text safety, mobile containment and no-JavaScript links/forms');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
