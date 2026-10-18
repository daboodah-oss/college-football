#!/usr/bin/env node
/* Execute the built page in jsdom and prove every section populated with zero script errors.

     npm install --no-save jsdom@24.1.0      (once, in any folder on NODE_PATH or next to this repo)
     node tools/render_check.js [index.html | https://cf.daboodah.com/]

   Why: a byte-identical push once shipped a blank IU page for ~2.5 days (a const helper used before its
   definition, a TDZ ReferenceError, killed the page script).  A page that has not been executed is not done.
   Ported from daboodah-oss/nd-report; the checks are this page's.

   It loads the page (a file or a live URL) and runs its script in light and then dark theme.  The page fetches
   the rows of anything picked from data/*.json on its own origin; for a file target those come from the files
   next to it, for a URL from the live site.  It checks: no uncaught error or console.error; the Team tab opens
   on the config default (Indiana 2026 vs Notre Dame 2026) with table and chart drawn, and the page's own totals
   for it equal the build's; the eight stats with correct leader boxes and a line swatch per row; picking a 3rd
   and a cross-season team re-renders table, chart and logs; the cap stops one past the limit with the friendly
   message; × removes; chips toggle and all-off shows the empty state; a chart tap pins the tooltip and a tap
   outside dismisses it; the AP list in the picker is in rank order, unranked last; the Player tab opens each of
   QB, RB, WR with its default picks, table, chart, National Top 3 line, game logs and method, takes a
   cross-season pick and enforces its cap; the manifest link is present.  It also scans the page script for
   const/let helpers whose first use at top level comes before their definition (the TDZ bug class).
   Exit 0 = pass.  Prints one line per check and a summary with the section and error counts. */
const fs = require("fs");
const path = require("path");
const { JSDOM, VirtualConsole } = require("jsdom");

const target = process.argv[2] || path.join(__dirname, "..", "index.html");
const live = /^https?:/.test(target);
const results = []; let failed = 0;
const ok = (cond, what) => { results.push(`${cond ? "PASS" : "FAIL"}  ${what}`); if (!cond) failed++; return cond; };
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function load() {
  if (live) { const r = await fetch(target); if (!r.ok) throw new Error(`GET ${target}: ${r.status}`); return await r.text(); }
  return fs.readFileSync(target, "utf8");
}

function tdzScan(js) {
  // const/let definitions in the page script, then any *call* of that name before its definition that would run
  // at load: not inside a function body (a function declaration, a braced arrow, or an arrow assigned to a
  // const/let, all of which run later).  Braces of object literals, blocks and template-literal ${} count as
  // load-time scope, so a helper called in a top-level forEach callback or object literal is caught too.
  const defs = [...js.matchAll(/^\s*(?:const|let)\s+([A-Za-z_$][\w$]*)\s*=/gm)].map(m => ({ name: m[1], at: m.index }));
  const fnDefs = new Map([...js.matchAll(/^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(/gm)].map(m => [m[1], m.index]));
  // one pass: for each offset, is it inside a deferred (function) body?  Strings and comments are skipped.
  const deferred = new Uint8Array(js.length + 1), text = new Uint8Array(js.length + 1), stack = [];
  let i = 0, q = null, tpl = [];
  const lazyArrow = at => { // the statement holding `at` is `const x = (...) =>` / `let x = y =>` (an arrow defined, not run)
    const st = Math.max(js.lastIndexOf(";", at), js.lastIndexOf("\n", at), js.lastIndexOf("{", at)) + 1;
    return /^\s*(?:const|let)\s+[\w$]+\s*=\s*(?:async\s*)?(?:\([^)]*\)|[\w$]+)\s*=>/.test(js.slice(st, at)); };
  while (i < js.length) {
    const c = js[i], fn = stack.includes("fn");
    if (q) { deferred[i] = fn; text[i] = 1; if (c === "\\") { text[i + 1] = 1; i += 2; continue; } if (c === q) q = null;
      else if (q === "`" && c === "$" && js[i + 1] === "{") { tpl.push(stack.length); stack.push("tpl"); q = null; i += 2; continue; }
      i++; continue; }
    if (c === "/" && js[i + 1] === "/") { const e = js.indexOf("\n", i); for (const end = e < 0 ? js.length : e; i < end; i++) text[i] = 1; continue; }
    if (c === "/" && js[i + 1] === "*") { const e = js.indexOf("*/", i + 2); for (const end = e < 0 ? js.length : e + 2; i < end; i++) text[i] = 1; continue; }
    if (c === '"' || c === "'" || c === "`") { q = c; deferred[i] = fn; i++; continue; }
    if (c === "{") { const pre = js.slice(Math.max(0, i - 400), i).replace(/\s+$/, "");
      stack.push(/\(\s*(?:async\s+)?function\s*\(\)$/.test(pre) ? "iife"  // the page's (function(){ ... })() wrapper runs at load
        : /=>$/.test(pre) || /function\s*[\w$]*\s*\([^()]*(?:\([^()]*\)[^()]*)*\)$/.test(pre) ? "fn" : "blk"); }
    else if (c === "}") { const t = stack.pop(); if (t === "tpl" && tpl.length && tpl[tpl.length - 1] === stack.length) { tpl.pop(); q = "`"; } }
    deferred[i] = stack.includes("fn") ? 1 : 0; i++;
  }
  const issues = [], top = defs.filter(d => !deferred[d.at + js.slice(d.at).search(/\S/)]);  // locals inside functions cannot be reached early
  for (const d of top) {
    const re = new RegExp(`(^|[^\\w$.])${d.name.replace(/\$/g, "\\$")}\\s*\\(`, "g");
    let m;
    while ((m = re.exec(js)) && m.index < d.at) {
      const at = m.index + m[1].length;
      if (!text[at] && !deferred[at] && !lazyArrow(at)) { issues.push(`${d.name} called at offset ${at} before its definition at ${d.at}`); break; }
    }
  }
  return { defs: top.length, fns: fnDefs.size, issues };
}

// the page's fetch of its own data files: local files next to a file target, the live origin for a URL
function pageFetch(w) {
  const base = live ? new URL(target) : null, dir = live ? null : path.dirname(path.resolve(target));
  return async url => {
    const u = String(url);
    if (live) { const r = await fetch(new URL(u, base)); return { ok: r.ok, status: r.status, json: () => r.json() }; }
    const f = path.join(dir, u.split("?")[0]);
    if (!fs.existsSync(f)) return { ok: false, status: 404, json: async () => { throw new Error("404"); } };
    const txt = fs.readFileSync(f, "utf8");
    return { ok: true, status: 200, json: async () => w.JSON.parse(txt) };
  };
}

async function run(html, theme) {
  const errors = [];
  const vc = new VirtualConsole();
  vc.on("jsdomError", e => errors.push(`jsdomError: ${e.message}`));
  vc.on("error", (...a) => errors.push(`console.error: ${a.join(" ")}`));
  const dom = new JSDOM(html, {
    runScripts: "dangerously", pretendToBeVisual: true, url: "https://cf.daboodah.com/", virtualConsole: vc,
    beforeParse(w) {
      w.matchMedia = q => ({ matches: theme === "dark" && /dark/.test(q), media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} });
      w.scrollTo = () => {};  // jsdom does not implement scrolling; the page calls it when a tab is opened by the user
      w.fetch = pageFetch(w);
      w.addEventListener("error", e => errors.push(`window error: ${e.message}`));
      w.addEventListener("unhandledrejection", e => errors.push(`unhandled rejection: ${e.reason}`));
      Object.defineProperty(w.HTMLElement.prototype, "clientWidth", { get() { return 900; } });
      w.SVGElement.prototype.getBoundingClientRect = () => ({ left: 0, top: 0, width: 900, height: 360, right: 900, bottom: 360 });
      try { w.localStorage.setItem("cf-theme", theme); } catch (e) {}
    },
  });
  await sleep(300);
  return { dom, errors };
}

const nonEmpty = (doc, sel) => { const e = doc.querySelector(sel); return !!e && e.textContent.trim().length > 0; };
const rowsOf = (doc, sel) => [...doc.querySelectorAll(`${sel} table.cmp tr`)].slice(1);

(async () => {
  const html = await load();
  const script = (html.match(/<script>\s*const MODEL[\s\S]*?<\/script>/) || [""])[0];
  const M = JSON.parse(script.match(/const MODEL = (\{[\s\S]*?\});\n\(function/)[1]);
  const tdz = tdzScan(script);
  ok(tdz.issues.length === 0, `TDZ scan: ${tdz.defs} top-level const/let definitions, ${tdz.fns} function declarations; first-call before definition: ${tdz.issues.length ? tdz.issues.join("; ") : "none"}`);
  ok(/<link rel="manifest" href="manifest\.webmanifest">/.test(html), "manifest link present in <head>");
  console.log(`built page: ${html.length.toLocaleString()} bytes`);
  const T = M.team, CAP = M.site.caps;
  const name = k => { const [id, s] = k.split("-"); return (T.index[s].find(e => e.k === k) || {}).name + " " + s; };

  let sections = 0, populated = 0, errorsTotal = 0;
  const sec = (doc, s, what) => { sections++; if (ok(nonEmpty(doc, s), what)) populated++; };
  for (const theme of ["light", "dark"]) {
    const { dom, errors } = await run(html, theme);
    const w = dom.window, doc = w.document, $ = s => doc.querySelector(s);
    const type = async (sel, v) => { const q = $(sel); q.dispatchEvent(new w.Event("focus")); q.value = v; q.dispatchEvent(new w.Event("input")); await sleep(20); };
    ok(doc.documentElement.getAttribute("data-theme") === theme, `[${theme}] theme applied before paint (data-theme=${doc.documentElement.getAttribute("data-theme")})`);
    const before = doc.documentElement.getAttribute("data-theme"); $("#theme-toggle").click();
    ok(doc.documentElement.getAttribute("data-theme") !== before, `[${theme}] theme toggle switches to ${doc.documentElement.getAttribute("data-theme")}`);
    $("#theme-toggle").click(); await sleep(50);

    /* ---------------- Team tab: default selection */
    ok(!$("#tab-team").hidden, `[${theme}] Team tab open on load`);
    for (const [s, what] of [["#team-pick", "picker + title"], ["#team-h2h", "head to head"], ["#team-compare", "compare chart"], ["#team-games", "game logs"], ["#team-method", "method and sources"]])
      sec(doc, s, `[${theme}] team ${s} (${what}) populated`);
    const want = T.defaults.map(name);
    ok(want.every(n => $("#team-title").textContent.includes(n)) && rowsOf(doc, "#team-table").length === T.defaults.length, `[${theme}] Team tab opens on the default: ${$("#team-title").textContent}`);
    ok(!!$("#team-chart svg") && $("#team-chart").querySelectorAll("path").length >= T.defaults.length, `[${theme}] team chart drew ${$("#team-chart").querySelectorAll("path").length} lines`);
    // the page's totals for the default must equal the build's (two independent computations from the same rows)
    const keys = ["games", "wins", "losses", "pf", "pa", "total_yds", "rush_yds", "pass_yds", "to_margin", "third_conv", "third_att"];
    for (const k of T.defaults) { const js = w.CF_CHECK.teamTotals(k), py = T.expect[k];
      ok(keys.every(x => js[x] === py[x]) && js.record === py.record, `[${theme}] ${name(k)}: page totals = build totals (${py.record}, ${py.pf}-${py.pa}, ${py.total_yds} yds, TO ${py.to_margin}, 3rd ${py.third_conv}/${py.third_att})`); }
    const heads = [...doc.querySelectorAll("#team-table th")].map(t => t.textContent);
    ok(heads.slice(2).join("|") === T.stats.map(s => s.short).join("|"), `[${theme}] team table stats: ${heads.slice(2).join(", ")}`);
    const leaderCheck = () => {  // recompute every leader box from the build's totals rule: best value wins, none when all tie
      const rows = rowsOf(doc, "#team-table"), sel = w.CF_CHECK.state().TS.sel, tots = sel.map(s => w.CF_CHECK.teamTotals(s.k));
      let bad = 0;
      T.stats.forEach((st, j) => {
        const v = tots.map(t => st.key === "wins" ? t.wins : t[st.key]).map(x => x == null ? null : Math.round(x * 10 ** st.dp) / 10 ** st.dp);
        const best = (st.hb ? Math.max : Math.min)(...v.filter(x => x != null)), L = v.map((x, i) => x === best ? i : -1).filter(i => i >= 0);
        const exp = L.length === v.length ? [] : L, got = rows.map((r, i) => r.querySelectorAll("td")[j + 2].classList.contains("win") ? i : -1).filter(i => i >= 0);
        if (exp.join() !== got.join()) bad++;
      });
      return { bad, swatches: rows.filter(r => r.querySelector("td.who svg.lsw")).length, n: rows.length };
    };
    let lc = leaderCheck(); ok(lc.bad === 0 && lc.swatches === lc.n, `[${theme}] team leader boxes correct on all 8 stats, ${lc.swatches}/${lc.n} rows carry a line swatch`);
    // AP list in the picker: rank ascending
    await type("#team-q", "");
    const apRanks = [...doc.querySelectorAll("#team-res [data-add]")].map(b => +(b.textContent.match(/^#(\d+)/) || [0, Infinity])[1]);
    ok(apRanks.length >= 5 && apRanks.every((r, i) => !i || r >= apRanks[i - 1]), `[${theme}] picker AP list (${apRanks.length} teams) in rank order`);
    await type("#team-q", "state");
    const mixed = [...doc.querySelectorAll("#team-res [data-add]")].map(b => (b.textContent.match(/^#(\d+)/) || [0, Infinity])[1]).map(Number);
    ok(mixed.every((r, i) => !i || r >= mixed[i - 1]), `[${theme}] picker search results ranked first by rank, unranked last (${mixed.length} hits)`);
    // add a third team (current season), then a cross-season pick of a default school
    await type("#team-q", "");
    const third = [...doc.querySelectorAll("#team-res [data-add]")].find(b => !b.disabled);
    third.click(); await sleep(150);
    ok(rowsOf(doc, "#team-table").length === T.defaults.length + 1 && $("#team-chart").querySelectorAll("path").length >= 3, `[${theme}] 3-team selection: ${$("#team-title").textContent}`);
    doc.querySelector('#team-season [data-k="' + M.site.seasons[0] + '"]').click();
    const dname = T.index[M.site.seasons[0]].find(e => T.defaults.some(k => name(k).startsWith(e.name + " ")));
    await type("#team-q", dname.name);
    const cross = [...doc.querySelectorAll("#team-res [data-add]")].find(b => b.dataset.add === dname.k);
    if (ok(!!cross, `[${theme}] picker finds ${dname.name} ${dname.season}`)) { cross.click(); await sleep(150); }
    const t4 = $("#team-title").textContent;
    ok(rowsOf(doc, "#team-table").length === T.defaults.length + 2 && t4.includes(`${dname.name} ${dname.season}`) && doc.querySelectorAll("#team-logs details").length === T.defaults.length + 2, `[${theme}] cross-season selection renders table, chart and logs: ${t4}`);
    lc = leaderCheck(); ok(lc.bad === 0 && lc.swatches === lc.n, `[${theme}] leader boxes still correct with ${lc.n} teams`);
    // fill to the cap, then one more
    doc.querySelector(`#team-season [data-k="${M.site.season}"]`).click();
    for (let guard = 0; w.CF_CHECK.state().TS.sel.length < CAP.teams && guard < 20; guard++) {
      await type("#team-q", ""); const b = [...doc.querySelectorAll("#team-res [data-add]")].find(b => !b.disabled); if (!b) break; b.click(); await sleep(120);
    }
    ok(rowsOf(doc, "#team-table").length === CAP.teams, `[${theme}] ${CAP.teams} teams selected (the cap)`);
    await type("#team-q", ""); const over = [...doc.querySelectorAll("#team-res [data-add]")].find(b => !b.disabled); over.click(); await sleep(60);
    ok(rowsOf(doc, "#team-table").length === CAP.teams && /readable with up to/.test($("#team-cap").textContent), `[${theme}] cap holds at ${CAP.teams}: "${$("#team-cap").textContent.slice(0, 70)}…"`);
    $("#team-picks [data-x]").click(); await sleep(30);
    ok(rowsOf(doc, "#team-table").length === CAP.teams - 1 && !$("#team-cap").textContent, `[${theme}] × removes a team and clears the cap message`);
    const chip = $("#team-chips .pc"); chip.click(); ok(chip.getAttribute("aria-pressed") === "false", `[${theme}] team chip toggles off`); chip.click();
    const all = [...doc.querySelectorAll("#team-chips .pc")]; all.forEach(b => b.click());
    ok(/toggled off/.test($("#team-chart").textContent), `[${theme}] all team chips off shows the friendly empty state`); all.forEach(b => b.click());
    for (const k of ["pa", "third_pct", "wins"]) { doc.querySelector(`#team-seg [data-k="${k}"]`).click(); }
    ok(!!$("#team-chart svg"), `[${theme}] team chart redraws on stat switch`);
    const hit = $("#team-chart rect[data-hit]");
    hit.dispatchEvent(new w.MouseEvent("pointerdown", { bubbles: true, clientX: 450, clientY: 100 }));
    const tip = $("#team-chart .tip");
    ok(tip && !tip.hidden, `[${theme}] tap in chart pins the tooltip`);
    hit.dispatchEvent(new w.MouseEvent("pointerleave", { bubbles: true }));
    ok(tip && !tip.hidden, `[${theme}] tooltip stays after pointerleave`);
    doc.body.dispatchEvent(new w.MouseEvent("pointerdown", { bubbles: true }));
    ok(tip && tip.hidden, `[${theme}] tap outside any chart dismisses the tooltip`);

    /* ---------------- Player tab */
    doc.querySelector('.tabs [data-tab="player"]').click(); await sleep(150);
    ok(!$("#tab-player").hidden, `[${theme}] Player tab opens`);
    for (const pos of ["qb", "rb", "wr"]) {
      doc.querySelector(`#player-pos [data-k="${pos}"]`).click(); await sleep(150);
      const P = M.player[pos], U = pos.toUpperCase();
      for (const [s, what] of [["#player-pick", "picker + title"], ["#player-h2h", "head to head"], ["#player-compare", "compare chart"], ["#player-games", "game logs"], ["#player-method", "method and sources"]])
        sec(doc, s, `[${theme}] ${U} ${s} (${what}) populated`);
      ok(rowsOf(doc, "#player-table").length === P.defaults.length && P.defaults.length === 2, `[${theme}] ${U} opens on the ${M.site.season} yardage leader and runner-up: ${$("#player-title").textContent}`);
      ok(!!$("#player-chart svg"), `[${theme}] ${U} chart drew an SVG`);
      const cats = [...doc.querySelectorAll("#player-compare details.cat > summary")].map(s => s.textContent.replace("▾", "").trim());
      ok(cats.join("|") === "Selected players|National Top 3", `[${theme}] ${U} chip groups: ${cats.join(", ")}`);
      const n0 = $("#player-chart").querySelectorAll("path").length, nt = $("#player-nrtop-pills .pc");
      if (ok(!!nt, `[${theme}] ${U} National Top 3 chips present`)) { nt.click(); await sleep(200); ok($("#player-chart").querySelectorAll("path").length > n0, `[${theme}] ${U} National Top 3 chip adds a gray line`); nt.click(); await sleep(50); }
      const pc = $("#player-chips .pc"); pc.click(); ok(pc.getAttribute("aria-pressed") === "false", `[${theme}] ${U} player chip toggles`); pc.click();
      // cross-season pick: the first search hit from an earlier season
      await type("#player-q", "a");
      const old = [...doc.querySelectorAll("#player-res [data-add]")].find(b => !b.disabled && !b.dataset.add.startsWith(String(M.site.season)));
      if (ok(!!old, `[${theme}] ${U} search finds an earlier-season player`)) { old.click(); await sleep(200); }
      ok(rowsOf(doc, "#player-table").length === 3 && doc.querySelectorAll("#player-logs details").length === 3, `[${theme}] ${U} cross-season pick renders: ${$("#player-title").textContent}`);
      for (let guard = 0; w.CF_CHECK.state().PS[pos].sel.length < CAP.players && guard < 20; guard++) {
        await type("#player-q", "e"); const b = [...doc.querySelectorAll("#player-res [data-add]")].find(b => !b.disabled); if (!b) break; b.click(); await sleep(150);
      }
      await type("#player-q", "e"); const b = [...doc.querySelectorAll("#player-res [data-add]")].find(b => !b.disabled); b.click(); await sleep(60);
      ok(rowsOf(doc, "#player-table").length === CAP.players && /readable with up to/.test($("#player-cap").textContent), `[${theme}] ${U} cap holds at ${CAP.players}`);
      $("#player-picks [data-x]").click(); await sleep(30);
      ok(rowsOf(doc, "#player-table").length === CAP.players - 1, `[${theme}] ${U} × removes a player`);
    }
    ok(errors.length === 0, `[${theme}] script errors: ${errors.length}${errors.length ? " -> " + errors.join(" | ") : ""}`);
    errorsTotal += errors.length;
    w.close();
  }
  console.log(results.join("\n"));
  console.log(`\nSUMMARY: ${populated}/${sections} sections populated across light and dark (${sections / 2} per theme), ${errorsTotal} script errors, ${failed} failed checks`);
  process.exit(failed ? 1 : 0);
})().catch(e => { console.log(results.join("\n")); console.error("render_check crashed (the page did not behave; see the failures above):", e.message); process.exit(2); });
