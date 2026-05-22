#!/usr/bin/env node
import { promises as fs } from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.cwd(), 'src');
const OUT = path.resolve(process.cwd(), 'docs/async-boundary-inventory.md');

async function walk(dir){
  const entries = await fs.readdir(dir,{withFileTypes:true});
  const files=[];
  for (const e of entries){
    const p=path.join(dir,e.name);
    if(e.isDirectory()){ if(['node_modules','dist'].includes(e.name)) continue; files.push(...await walk(p)); }
    else if(/\.(ts|tsx)$/.test(e.name) && !e.name.endsWith('.test.ts') && !e.name.endsWith('.test.tsx')) files.push(p);
  }
  return files;
}

function lineNo(src, idx){ return src.slice(0, idx).split('\n').length; }

function scan(file, src){
  const rel = path.relative(process.cwd(), file).replaceAll('\\','/');
  const items=[];
  for (const m of src.matchAll(/\b(async\s+function\s+\w+|const\s+\w+\s*=\s*async\s*\(|queryFn\s*:\s*async\s*\(|mutationFn\s*:\s*async\s*\(|onClick\s*=\{\s*async\s*\(|useEffect\s*\(\s*\(\)\s*=>\s*\{[\s\S]{0,220}?\bvoid\s+[\w$.]+\()/g)){
    items.push({line:lineNo(src,m.index),kind:'async-boundary',snippet:m[0].split('\n')[0].trim()});
  }
  for (const m of src.matchAll(/\bvoid\s+([\w$.]+\([^;]*\));/g)){
    const seg = src.slice(m.index, m.index+220);
    if(!seg.includes('.catch(')) items.push({line:lineNo(src,m.index),kind:'fire-and-forget-no-catch',snippet:m[0].trim()});
  }
  return {rel, items};
}

const files = await walk(ROOT);
const report = files.map(async f=>scan(f, await fs.readFile(f,'utf8')));
const rows = await Promise.all(report);
const flagged = rows.filter(r=>r.items.length);
let md = '# Async Boundary Inventory\n\n';
md += `Generated: ${new Date().toISOString()}\n\n`;
for(const r of flagged){
  md += `## ${r.rel}\n`;
  for(const it of r.items){ md += `- L${it.line} [${it.kind}] \`${it.snippet.replace(/`/g,'\\`')}\`\n`; }
  md += '\n';
}
await fs.mkdir(path.dirname(OUT), {recursive:true});
await fs.writeFile(OUT, md);

const violations = flagged.flatMap(r=>r.items.filter(i=>i.kind==='fire-and-forget-no-catch').map(i=>`${r.rel}:${i.line} ${i.kind}`));
if(violations.length){
  console.error('Async audit violations found:\n'+violations.join('\n'));
  process.exit(1);
}
console.log(`Async boundary inventory written to ${path.relative(process.cwd(), OUT)}.`);
