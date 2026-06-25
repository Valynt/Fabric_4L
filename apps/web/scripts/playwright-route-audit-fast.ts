import { chromium, type ConsoleMessage, type Page, type Request } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = 'http://localhost:3001';
const OUT = path.resolve(process.cwd(), '../audit-output');
const SCR = path.join(OUT, 'screenshots');
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(SCR, { recursive: true });

interface R {
  path: string; from: string; title: string; heading: string;
  status: 'Pass'|'Partial'|'Fail'|'Blocked';
  shot: string; ce: string[]; nf: string[]; notes: string[]; vp: string;
}

const ROUTES: { path: string; from: string }[] = [
  {path:'/',from:'root'},{path:'/login',from:'nav'},{path:'/signup',from:'nav'},
  {path:'/home',from:'sidebar'},{path:'/command-center',from:'sidebar'},{path:'/accounts',from:'sidebar'},
  {path:'/accounts/acct-123',from:'deep-link'},
  {path:'/workflow/prospect',from:'sidebar'},{path:'/workflow/intelligence',from:'sidebar'},{path:'/workflow/ai-model',from:'sidebar'},
  {path:'/workflow/driver-tree',from:'sidebar'},{path:'/workflow/evidence',from:'sidebar'},{path:'/workflow/calculator',from:'sidebar'},{path:'/workflow/value-case',from:'sidebar'},
  {path:'/intelligence/acct-123',from:'redirect'},{path:'/intelligence/acct-123/signals',from:'tab'},{path:'/intelligence/acct-123/drivers',from:'tab'},
  {path:'/intelligence/acct-123/evidence',from:'tab'},{path:'/intelligence/acct-123/stakeholders',from:'tab'},{path:'/intelligence/acct-123/enrichment',from:'tab'},
  {path:'/intelligence/acct-123/hypotheses',from:'tab'},{path:'/intelligence/acct-123/competitive',from:'tab'},{path:'/intelligence/acct-123/roi',from:'tab'},
  {path:'/intelligence/acct-123/evidence-library',from:'tab'},{path:'/intelligence/acct-123/ontology-match',from:'tab'},
  {path:'/hypothesis/acct-123/hypothesis',from:'tab'},{path:'/hypothesis/acct-123/discovery-questions',from:'tab'},
  {path:'/hypothesis/acct-123/persona-fit',from:'tab'},{path:'/hypothesis/acct-123/assumptions',from:'tab'},
  {path:'/drivers/acct-123',from:'sidebar'},
  {path:'/evidence/acct-123/evidence',from:'tab'},{path:'/evidence/acct-123/alternatives',from:'tab'},{path:'/evidence/acct-123/solution-cost',from:'tab'},
  {path:'/calculator/acct-123/roi',from:'tab'},{path:'/calculator/acct-123/value-model',from:'tab'},
  {path:'/value-case/acct-123',from:'sidebar'},{path:'/realization/acct-123',from:'sidebar'},
  {path:'/studio/acct-123/action-plan',from:'tab'},{path:'/studio/acct-123/value-model',from:'tab'},{path:'/studio/acct-123/narrative',from:'tab'},
  {path:'/context/packs',from:'sidebar'},{path:'/context/models',from:'sidebar'},
  {path:'/context/formulas',from:'sidebar'},{path:'/context/formulas/new',from:'button'},{path:'/context/value-trees/explorer',from:'sidebar'},
  {path:'/context/agents',from:'sidebar'},{path:'/context/ontology',from:'sidebar'},{path:'/context/ontology/entities',from:'sub-nav'},
  {path:'/context/ontology/entities/ent-123',from:'deep-link'},{path:'/context/ontology/graph',from:'sub-nav'},
  {path:'/context/ingestion/jobs',from:'sidebar'},{path:'/context/extraction',from:'sidebar'},
  {path:'/context/integrations',from:'sidebar'},{path:'/context/sources',from:'sidebar'},
  {path:'/deliverables/cases',from:'sidebar'},{path:'/deliverables/cases/case-123',from:'deep-link'},
  {path:'/deliverables/calculators',from:'sidebar'},
  {path:'/deliverables/views/cfo',from:'sidebar'},{path:'/deliverables/views/executive',from:'sidebar'},{path:'/deliverables/views/technical',from:'sidebar'},
  {path:'/settings/content/formulas',from:'sidebar'},{path:'/settings/data/variables',from:'sidebar'},{path:'/settings/access/roles',from:'sidebar'},
  {path:'/settings/system/settings',from:'sidebar'},{path:'/settings/system/billing',from:'sidebar'},
  {path:'/governance/traces',from:'sidebar'},{path:'/governance/evidence',from:'sidebar'},
  {path:'/governance/provenance',from:'sidebar'},{path:'/governance/compliance',from:'sidebar'},
  {path:'/governance/benchmarks',from:'sidebar'},{path:'/governance/audit/log',from:'sidebar'},{path:'/governance/health',from:'sidebar'},
  {path:'/dev/integration',from:'sidebar'},
  {path:'/nonexistent-route-xyz',from:'edge-case'},
  {path:'/intelligence',from:'edge-case'},{path:'/studio',from:'edge-case'},
];

type UserTier = 'standard' | 'advanced' | 'admin';

interface AuditUser {
  id: string;
  email: string;
  role: UserTier;
  tenantId: string;
  tenantSlug: string;
}

interface RouteAuditSummary {
  health: number;
  verdict: string;
  ceTotal: number;
  nfTotal: number;
  pass: number;
  partial: number;
  fail: number;
  blocked: number;
  risks: string[];
}

function isErrorWithMessage(value: unknown): value is { message: string } {
  return typeof value === 'object' && value !== null && 'message' in value && typeof (value as { message: unknown }).message === 'string';
}

async function seed(page: Page, tier: UserTier = 'admin'){
  const user: AuditUser = {id:'audit-001',email:'audit@test.com',role:tier,tenantId:'tenant-audit',tenantSlug:'audit'};
  await page.goto(`${BASE_URL}/login`,{waitUntil:'domcontentloaded',timeout:15000});
  await page.evaluate((u: AuditUser)=>{
    const payload={exp:Math.floor(Date.now()/1000)+86400,iat:Math.floor(Date.now()/1000),sub:u.id,tenant_id:u.tenantId};
    const token=`header.${btoa(JSON.stringify(payload))}.signature`;
    localStorage.setItem('accessToken',token);
    localStorage.setItem('userInfo',JSON.stringify(u));
    localStorage.setItem('tenantId',u.tenantId);
    localStorage.setItem('user-tier-storage',JSON.stringify({state:{currentTier:u.role,isAdvancedModeEnabled:u.role!=='standard',userRole:u.role},version:0}));
  },user);
}

function safe(s: string){return s.replace(/[^a-z0-9_-]/gi,'_').replace(/_+/g,'_');}

type ConsoleErrorHandler = (message: ConsoleMessage) => void;
type RequestFailureHandler = (request: Request) => void;

async function audit(page: Page, routePath: string, from: string): Promise<R>{
  const ce: string[]=[]; const nf: string[]=[]; const notes: string[]=[];
  const onC: ConsoleErrorHandler=(m)=>{if(m.type()==='error')ce.push(m.text());};
  const onF: RequestFailureHandler=(r)=>{
    const failure = r.failure();
    if(failure){
      nf.push(`${r.method()} ${r.url()} — ${failure.errorText}`);
    }
  };
  page.on('console',onC); page.on('requestfailed',onF);
  try{
    await page.goto(`${BASE_URL}${routePath}`,{waitUntil:'domcontentloaded',timeout:15000});
  }catch(e: unknown){notes.push(`nav fail:${isErrorWithMessage(e) ? e.message : String(e)}`);}
  await page.waitForTimeout(400);
  const title=await page.title().catch(()=>'?');
  const h1=await page.locator('h1').first().textContent().catch(()=>'');
  const h2=await page.locator('h2').first().textContent().catch(()=>'');
  const heading=(h1||h2||'No heading').substring(0,60);
  const shot=`audit-output/screenshots/${safe(`${routePath}_desktop`)}.png`;
  try{await page.screenshot({path:path.join(OUT,'screenshots',safe(`${routePath}_desktop`)+'.png')});}catch{notes.push('sshot fail');}
  const final=new URL(page.url()).pathname;
  if(final!==routePath&&!routePath.startsWith('/nonexistent'))notes.push(`redirect:${routePath}→${final}`);
  let status: R['status']='Pass';
  if(ce.length||nf.length)status='Partial';
  if(ce.some((e: string)=>/crash|undefined|null|Cannot read|not a function/i.test(e)))status='Fail';
  if(notes.some((n: string)=>n.includes('nav fail')))status='Blocked';
  page.off('console',onC); page.off('requestfailed',onF);
  return {path:routePath,from,title,heading,status,shot,ce,nf,notes,vp:'desktop'};
}

function buildHookMap(results: R[]): Map<string,{routes:string[];msg:string}> {
  const hookMap=new Map<string,{routes:string[];msg:string}>();
  for(const r of results)for(const e of r.ce){
    let name='Generic error';
    if(/useParams|params/i.test(e))name='useParams null/undefined';
    else if(/useAuth|auth/i.test(e))name='useAuth context failure';
    else if(/zustand/i.test(e))name='Zustand store error';
    else if(/invalid hook/i.test(e))name='Invalid hook call';
    else if(/wouter/i.test(e))name='Wouter routing error';
    else if(/react query|tanstack|useQuery/i.test(e))name='React Query failure';
    else continue;
    const ex=hookMap.get(name)||{routes:[],msg:e};ex.routes.push(r.path);hookMap.set(name,ex);
  }
  return hookMap;
}

function generateMarkdownReport(summary: RouteAuditSummary, results: R[], backOk: boolean, reloadOk: boolean): string {
  let md=`# Playwright Route & Hook Audit Report\n**Date:** ${new Date().toISOString().split('T')[0]} **Base:** ${BASE_URL}\n\n`;
  md+=`## 1. Executive Summary\n- Health score: ${summary.health}%\n- Verdict: ${summary.verdict}\n- Console errors: ${summary.ceTotal} | Network failures: ${summary.nfTotal}\n`;
  md+=`### Top 5 Risks\n`;summary.risks.slice(0,5).forEach((r,i)=>md+=`${i+1}. ${r}\n`);
  md+=`### Top 5 Fixes\n1. Fix P0 hook null-checks on route params\n2. Add ErrorBoundary to all lazy tabs\n3. Handle API 401/403 with visible UI\n4. Preserve account/tenant context on refresh\n5. Fix responsive overflow & mobile nav\n\n`;
  md+=`## 2. Route Inventory\n| Route | From | Title | Heading | Status | CE | NF | Notes |\n|-------|------|-------|---------|--------|----|----|-------|\n`;
  for(const r of results){md+=`| ${r.path} | ${r.from} | ${r.title.substring(0,28)} | ${r.heading.substring(0,28)} | ${r.status} | ${r.ce.length} | ${r.nf.length} | ${r.notes.join('; ').substring(0,60).replace(/\|/g,'\\|')} |\n`;}
  md+=`\n## 3. Hook & State Audit\n`;
  const hookMap=buildHookMap(results);
  if(hookMap.size===0)md+=`_No hook errors detected._\n`;
  for(const [k,v] of hookMap){md+=`- **${k}** — routes: ${[...new Set(v.routes)].join(', ')} — ${v.msg.substring(0,120)}\n`;}
  md+=`\n## 4. Navigation & Routing Audit\n`;
  md+=`- Back/forward: ${backOk?'OK':'FAIL'}\n`;
  md+=`- Nested reload: ${reloadOk?'OK':'FAIL'}\n`;
  const reds=results.filter(r=>r.notes.some(n=>n.includes('redirect:')));
  if(reds.length){md+=`Redirects observed:\n`;reds.forEach(r=>md+=`  - ${r.path}\n`);}
  md+=`\n## 5. Data & API Audit\n`;
  const api=results.filter(r=>r.nf.length>0);
  if(api.length===0)md+=`_No API failures._\n`;else api.forEach(r=>md+=`- ${r.path}: ${r.nf.slice(0,2).join('; ')}\n`);
  md+=`\n## 6. Accessibility & Responsive Audit\n_Needs manual verification — automated checks limited in this run._\n`;
  md+=`\n## 7. Prioritized Fix Backlog\n`;
  results.filter(r=>r.status==='Fail'||r.status==='Blocked').slice(0,8).forEach((r,i)=>{
    md+=`### ${i+1}. Fix ${r.status.toLowerCase()} route ${r.path}\n`;
    md+=`- Severity: ${r.status==='Blocked'?'P0':'P1'} | Area: Routing/Rendering\n`;
    md+=`- Problem: ${r.ce.join('; ').substring(0,120)} ${r.notes.join('; ').substring(0,120)}\n`;
    md+=`- AC: No console errors, graceful empty/error states, screenshot match\n\n`;
  });
  md+=`## 8. Playwright Test Recommendations\n`;
  md+=`1. Route smoke tests for every canonical path\n`;
  md+=`2. Deep-link reload tests for /intelligence/:id/:tab and /studio/:id/:tab\n`;
  md+=`3. Auth/tenant context propagation tests\n`;
  md+=`4. Responsive viewport matrix (390/768/1280/1440)\n`;
  md+=`5. Axe-core scan on all pages + keyboard-only journey\n`;
  md+=`6. Error/empty/loading state tests with mocked API\n`;
  return md;
}

async function main(){
  console.log('Starting fast audit...');
  const browser=await chromium.launch();
  const context=await browser.newContext({viewport:{width:1280,height:800}});
  context.setDefaultTimeout(2000);
  const page=await context.newPage();
  await seed(page,'admin');
  const results: R[]=[];
  for(const r of ROUTES){
    console.log(`  ${r.path}`);
    results.push(await audit(page,r.path,r.from));
  }
  // nav checks
  await page.goto(`${BASE_URL}/home`,{waitUntil:'domcontentloaded'});
  await page.goto(`${BASE_URL}/accounts`,{waitUntil:'domcontentloaded'});
  await page.goBack({waitUntil:'domcontentloaded'}); const backOk=page.url().includes('/home');
  await page.goForward({waitUntil:'domcontentloaded'}); const forwardOk=page.url().includes('/accounts');
  await page.goto(`${BASE_URL}/intelligence/acct-123/signals`,{waitUntil:'domcontentloaded'});
  await page.reload({waitUntil:'domcontentloaded'}); const reloadOk=page.url().includes('/intelligence/acct-123/signals');

  const pass=results.filter(r=>r.status==='Pass').length;
  const partial=results.filter(r=>r.status==='Partial').length;
  const fail=results.filter(r=>r.status==='Fail').length;
  const blocked=results.filter(r=>r.status==='Blocked').length;
  const ceTotal=results.reduce((s,r)=>s+r.ce.length,0);
  const nfTotal=results.reduce((s,r)=>s+r.nf.length,0);
  const health=Math.round((pass/Math.max(results.length,1))*100);
  const verdict=health>=90?'Ready with minor fixes':health>=70?'Conditional — fix P0/P1':'Not ready — significant issues';
  const risks: string[]=[];
  if(fail)risks.push(`${fail} routes crash`);
  if(blocked)risks.push(`${blocked} routes blocked`);
  if(ceTotal>20)risks.push(`${ceTotal} console errors`);
  if(!backOk)risks.push('Back nav broken');
  if(!reloadOk)risks.push('Nested reload broken');

  const summary: RouteAuditSummary = { health, verdict, ceTotal, nfTotal, pass, partial, fail, blocked, risks };
  const md=generateMarkdownReport(summary, results, backOk, reloadOk);

  const mdPath=path.join(OUT,`playwright-route-hook-audit-${new Date().toISOString().split('T')[0]}.md`);
  fs.writeFileSync(mdPath,md);
  console.log(`\nReport: ${mdPath}`);
  console.log(`Routes:${results.length} Pass:${pass} Partial:${partial} Fail:${fail} Blocked:${blocked} CE:${ceTotal} NF:${nfTotal}`);
  console.log(`Risks: ${risks.slice(0,5).join(' | ')}`);
  await browser.close();
}
main().catch(e=>{console.error(e);process.exit(1);});
