const {chromium}=require('playwright');
const {execFileSync}=require('child_process');
const path=require('path');
const assert=require('assert');
const php=process.env.SABGA_TEST_PHP || 'php';
const harness=path.join(__dirname,'test-plugin.php');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE_PATH,args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1280,height:900}});let failure=false, injection=false; const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/tests/history-preview.html*',route=>{
  const url=new URL(route.request().url());
  const html=execFileSync(php,[harness,'--render-history',url.searchParams.toString() || 'standings'],{encoding:'utf8'});
  return route.fulfill({status:200,contentType:'text/html',body:html});
 });
 await page.route('**/api/sabga-leagues/v1/history?*',route=>{
  if(failure)return route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({message:'Records test unavailable.'})});
  const input=Object.fromEntries(new URL(route.request().url()).searchParams);
  const data=JSON.parse(execFileSync(php,[harness,'--history-report',JSON.stringify(input)],{encoding:'utf8'}));
  if(injection)data.rows[0][0]='<img src=x onerror=alert(1)>';
  return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(data)});
 });
 await page.goto('http://127.0.0.1:8765/tests/history-preview.html');
 assert.equal(await page.getByRole('navigation',{name:'Record sections'}).getByRole('link').count(),4);
 assert.equal(await page.getByRole('heading',{name:'Previous standings',exact:true}).count(),1);
 assert.equal(await page.getByLabel('Series',{exact:true}).locator('option').count(),2);
 assert.equal(await page.getByRole('table').locator('tbody tr').count(),8);
 await page.getByLabel('League group').selectOption('122');
 await page.getByRole('status').filter({hasText:'Records loaded.'}).waitFor();
 assert.equal(new URL(page.url()).searchParams.get('sabga_history_group'),'122');
 failure=true;await page.getByRole('button',{name:'Show standings'}).click();
 await page.getByRole('alert').waitFor();assert.equal(await page.getByRole('table').count(),0);
 failure=false;injection=true;await page.getByRole('button',{name:'Show standings'}).click();
 await page.getByRole('table').waitFor();assert.equal(await page.locator('tbody img').count(),0);
 assert.ok((await page.locator('tbody th').first().innerText()).includes('<img'));
 for(const label of ['Player of the Year','League PR trends','Player records']){
  await page.getByRole('link',{name:label,exact:true}).click();
  await page.getByRole('heading',{name:label,exact:true}).waitFor();
  assert.equal(await page.getByRole('table').count(),1);
 }
 injection=false;await page.getByLabel('Player',{exact:true}).selectOption('2');
 await page.getByRole('status').filter({hasText:'Records loaded.'}).waitFor();
 assert.equal(new URL(page.url()).searchParams.get('sabga_history_player'),'2');
 await page.screenshot({path:path.join(__dirname,'history-desktop-preview.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 await page.screenshot({path:path.join(__dirname,'history-mobile-preview.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 // Links and independent dependent-selector forms also work without JavaScript.
 const context=await browser.newContext({javaScriptEnabled:false});const plain=await context.newPage();
 await plain.route('**/tests/history-preview.html*',route=>{
  const url=new URL(route.request().url());
  const html=execFileSync(php,[harness,'--render-history',url.searchParams.toString() || 'standings'],{encoding:'utf8'});
  return route.fulfill({status:200,contentType:'text/html',body:html});
 });
 await plain.goto('http://127.0.0.1:8765/tests/history-preview.html');
 await plain.getByRole('link',{name:'Previous standings',exact:true}).click();
 await plain.getByLabel('Season',{exact:true}).selectOption('1');
 await plain.getByRole('button',{name:'Show season'}).click();
 assert.equal(await plain.getByLabel('Season',{exact:true}).inputValue(),'1');
 await plain.getByLabel('Series',{exact:true}).selectOption('5');await plain.getByRole('button',{name:'Show series'}).click();
 assert.equal(await plain.getByLabel('League group').inputValue(),'51');
 console.log('PASS: four archive tabs, dependent selections, AJAX switching, error clearing/retry, XSS escaping, mobile overflow and no-JavaScript forms');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
