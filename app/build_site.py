"""Generate the static site from approved summaries.

Writes docs/index.html (self-contained) and docs/data.json. The folder is docs/
because that is one of only two locations GitHub Pages will serve from.

Everything the page needs is embedded, so the site works from any static host or
straight off the filesystem. Filtering and search run in the browser.

The HTML template uses {{TOKEN}} placeholders rather than str.format, so the CSS
and JavaScript braces need no escaping.

TEMPLATE must stay a raw string. The CSS disclosure arrow and the date regex both
contain backslash sequences Python would otherwise interpret. The CSS one is an
octal escape: it does not warn and does not fail, it silently swaps the arrow for
a control character. Keep the r prefix.
"""

from __future__ import annotations

import html
import json
import logging
from datetime import date

from . import config, store

log = logging.getLogger(__name__)


def _card_data(record: dict) -> dict:
    """The subset of a notice the page actually renders."""
    return {
        "id": record["document_number"],
        "title": record["title"],
        "type": record.get("doc_type") or "",
        "published": record.get("publication_date") or "",
        "effective": record.get("effective_on") or "",
        "url": record.get("html_url") or "",
        "what_changed": record.get("what_changed") or "",
        "who_affected": record.get("who_affected") or "",
        "key_details": record.get("key_details") or [],
        "species": record.get("species") or [],
        "regions": record.get("regions") or [],
        # Published deliberately. A summary that hides what it could not determine
        # is less trustworthy than one that says so.
        "open_questions": record.get("unclear") or [],
        # Which regulatory programme the notice came from, taken from the query
        # that matched it, not inferred from the title.
        "programs": record.get("programs") or [],
    }


def build(db_path=None, out_dir=None) -> dict:
    """Render the site. Returns a small summary of what was written."""
    out = out_dir or config.SITE_DIR
    out.mkdir(parents=True, exist_ok=True)

    with store.connect(db_path) as conn:
        records = store.approved(conn)

    cards = [_card_data(r) for r in records]
    species = sorted({s for c in cards for s in c["species"]})
    regions = sorted({r for c in cards for r in c["regions"]})
    types = sorted({c["type"] for c in cards if c["type"]})
    programs = sorted({p for c in cards for p in c["programs"]})

    payload = {
        "generated": date.today().isoformat(),
        "count": len(cards),
        "species": species,
        "regions": regions,
        "types": types,
        "programs": programs,
        "notices": cards,
    }

    (out / "data.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # GitHub Pages pipes a site through Jekyll unless this file exists. Jekyll
    # silently ignores files and folders beginning with an underscore, which is a
    # confusing way to lose a file later. Opt out once, here.
    (out / ".nojekyll").write_text("", encoding="utf-8")

    page = (
        TEMPLATE.replace("{{TITLE}}", html.escape(config.SITE_TITLE))
        .replace("{{TAGLINE}}", html.escape(config.SITE_TAGLINE))
        .replace("{{DISCLAIMER}}", html.escape(config.SITE_DISCLAIMER))
        .replace("{{GENERATED}}", payload["generated"])
        .replace("{{COUNT}}", str(len(cards)))
        .replace("{{DATA}}", json.dumps(payload, ensure_ascii=False))
    )
    (out / "index.html").write_text(page, encoding="utf-8")

    log.info("Wrote %d notice(s) to %s", len(cards), out)
    return {"path": out, "count": len(cards), "species": len(species), "regions": len(regions)}


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<meta name="description" content="{{TAGLINE}}">
<script>
  // Apply the saved theme before first paint, otherwise a visitor who chose light
  // sees a dark flash on every page load. Storage can throw in a private window.
  try {
    var saved = localStorage.getItem('theme');
    if (saved === 'dark' || saved === 'light') {
      document.documentElement.setAttribute('data-theme', saved);
    }
  } catch (e) {}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --deep:    #0b3a4a;
    --deep-2:  #11536a;
    --accent:  #0f7d94;
    --sand:    #f4efe6;
    --bg:      #f6f8f9;
    --surface: #ffffff;
    --bar:     rgba(246,248,249,.94);
    --border:  #dde5ea;
    --text:    #13232c;
    --muted:   #5d7180;
    --flag-bg: #fdf6e6;
    --flag-br: #e8d9ae;
    --flag-tx: #6b5415;
    --shadow:  0 1px 2px rgba(19,35,44,.05);
    --radius:  10px;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --deep: #7fd3e8; --deep-2: #4fb4cd; --accent: #58bcd6; --sand: #1b2730;
      --bg: #0d151a; --surface: #141f27; --bar: rgba(13,21,26,.94);
      --border: #263643; --text: #e8f0f4; --muted: #93a8b5;
      --flag-bg: #241f12; --flag-br: #4a3f21; --flag-tx: #e0cb92; --shadow: none;
    }
  }
  :root[data-theme="dark"] {
    --deep: #7fd3e8; --deep-2: #4fb4cd; --accent: #58bcd6; --sand: #1b2730;
    --bg: #0d151a; --surface: #141f27; --bar: rgba(13,21,26,.94);
    --border: #263643; --text: #e8f0f4; --muted: #93a8b5;
    --flag-bg: #241f12; --flag-br: #4a3f21; --flag-tx: #e0cb92; --shadow: none;
  }

  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 400 15.5px/1.55 "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .wrap { max-width: 880px; margin: 0 auto; padding: 0 16px 64px; }

  /* masthead */
  .masthead {
    background: var(--deep); color: var(--sand);
    padding: 24px 0 22px; border-bottom: 3px solid var(--accent);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) .masthead { background: var(--surface); color: var(--text); }
    :root:not([data-theme="light"]) .issue { border-top-color: var(--border); }
    :root:not([data-theme="light"]) .themebtn { border-color: var(--border); }
  }
  :root[data-theme="dark"] .masthead { background: var(--surface); color: var(--text); }
  :root[data-theme="dark"] .issue { border-top-color: var(--border); }
  :root[data-theme="dark"] .themebtn { border-color: var(--border); }
  .masthead .wrap { padding-bottom: 0; }
  .topline { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
  .brand { display: flex; align-items: center; gap: 11px; }
  h1 {
    margin: 0; font-family: Fraunces, Georgia, serif; font-weight: 600;
    font-size: clamp(1.35rem, 4vw, 1.8rem); line-height: 1.12; letter-spacing: -.015em;
  }
  .tagline { margin: 7px 0 0; opacity: .82; font-size: .92rem; max-width: 56ch; }
  .issue {
    margin: 12px 0 0; padding-top: 10px; border-top: 1px solid rgba(255,255,255,.16);
    font-size: .75rem; letter-spacing: .07em; text-transform: uppercase; opacity: .72;
  }
  .themebtn {
    flex: 0 0 auto; background: transparent; color: inherit; cursor: pointer;
    border: 1px solid rgba(255,255,255,.3); border-radius: 8px;
    padding: 6px 9px; line-height: 0; font: inherit;
  }
  .themebtn:hover { background: rgba(255,255,255,.1); }
  :root[data-theme="dark"] .themebtn:hover { background: rgba(255,255,255,.06); }

  /* sticky filter bar */
  .bar {
    position: sticky; top: 0; z-index: 10;
    background: var(--bar); backdrop-filter: blur(8px);
    border-bottom: 1px solid transparent; margin-bottom: 14px;
  }
  .bar.stuck { border-bottom-color: var(--border); }
  /* On a phone the five controls stack into a 284px bar — 35% of the screen, held
     there permanently. Not worth it. Below this width the bar scrolls away like
     ordinary content; every filter still works, it just is not pinned. */
  @media (max-width: 619px) {
    .bar { position: static; backdrop-filter: none; }
  }
  .bar .wrap { padding-top: 10px; padding-bottom: 8px; }
  .controls { display: grid; gap: 8px; }
  @media (min-width: 620px) { .controls { grid-template-columns: 1fr 1fr; } }
  @media (min-width: 860px) { .controls { grid-template-columns: 1.5fr repeat(4, 1fr); } }
  input, select {
    width: 100%; padding: 8px 11px; font: inherit; font-size: .9rem;
    color: var(--text); background: var(--surface);
    border: 1px solid var(--border); border-radius: 7px;
  }
  input:focus-visible, select:focus-visible, a:focus-visible, button:focus-visible {
    outline: 2px solid var(--accent); outline-offset: 2px;
  }
  .resultline {
    margin: 8px 0 0; font-size: .82rem; color: var(--muted);
    display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  }
  .clear {
    background: none; border: 0; padding: 0; font: inherit; font-size: .82rem;
    color: var(--accent); cursor: pointer; text-decoration: underline;
  }

  /* card */
  article {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 15px 17px 13px;
    margin-bottom: 11px; box-shadow: var(--shadow);
  }
  .kicker {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    margin-bottom: 6px; font-size: .69rem; letter-spacing: .07em; text-transform: uppercase;
  }
  .prog {
    font-weight: 700; color: var(--accent);
    background: color-mix(in srgb, var(--accent) 12%, transparent);
    padding: 2px 7px; border-radius: 4px; letter-spacing: .05em;
  }
  .kind { font-weight: 700; color: var(--deep-2); }
  .kicker .dot { color: var(--border); }
  .kicker time { color: var(--muted); }
  article h2 {
    margin: 0 0 9px; font-family: Fraunces, Georgia, serif; font-weight: 600;
    font-size: 1.05rem; line-height: 1.3; letter-spacing: -.005em;
  }
  .eff {
    display: inline-flex; align-items: baseline; gap: 7px; margin-bottom: 9px;
    background: var(--sand); border-radius: 6px; padding: 4px 10px;
    font-size: .84rem;
  }
  .eff .lab {
    font-size: .65rem; letter-spacing: .09em; text-transform: uppercase; color: var(--muted);
  }
  .eff .val { font-weight: 700; }
  .eff .val.none { font-weight: 600; color: var(--muted); }
  .what { margin: 0 0 9px; font-size: .97rem; }
  .who { margin: 0 0 10px; color: var(--muted); font-size: .89rem; }
  .who strong {
    display: block; font-size: .65rem; letter-spacing: .09em; text-transform: uppercase;
    margin-bottom: 2px; font-weight: 700;
  }

  .disc { display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 10px; }
  details > summary {
    cursor: pointer; font-size: .79rem; font-weight: 600; color: var(--accent);
    list-style: none; padding: 2px 0;
  }
  details > summary::-webkit-details-marker { display: none; }
  details > summary::before {
    content: "\25B8"; display: inline-block; margin-right: 6px; transition: transform .15s;
  }
  details[open] > summary::before { transform: rotate(90deg); }
  details { min-width: 0; }
  details[open] { flex: 1 1 100%; }
  ul.details { margin: 7px 0 0; padding-left: 18px; font-size: .89rem; }
  ul.details li { margin-bottom: 4px; }

  details.flag > summary { color: var(--flag-tx); }
  .flagbox {
    margin-top: 7px; background: var(--flag-bg); border: 1px solid var(--flag-br);
    border-radius: 7px; padding: 9px 12px;
  }
  .flagbox p { margin: 0 0 6px; font-size: .79rem; color: var(--flag-tx); }
  .flagbox ul { margin: 0; padding-left: 16px; font-size: .87rem; }
  .flagbox li { margin-bottom: 4px; }

  .tags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 10px; }
  .tag {
    font-size: .73rem; padding: 2px 9px; border-radius: 999px; white-space: nowrap;
    border: 1px solid transparent;
  }
  .tag.sp { background: color-mix(in srgb, var(--accent) 13%, transparent); color: var(--deep-2); }
  .tag.rg { background: transparent; border-color: var(--border); color: var(--muted); }

  .foot {
    display: flex; justify-content: space-between; align-items: center; gap: 12px;
    flex-wrap: wrap; border-top: 1px solid var(--border); padding-top: 9px;
  }
  .foot .pub { font-size: .76rem; color: var(--muted); }
  a { color: var(--accent); }
  .source { font-size: .84rem; font-weight: 700; text-decoration: none; }
  .source:hover { text-decoration: underline; }

  .empty {
    padding: 44px 16px; text-align: center; color: var(--muted);
    border: 1px dashed var(--border); border-radius: var(--radius);
  }
  footer {
    margin-top: 36px; padding-top: 18px; border-top: 1px solid var(--border);
    font-size: .81rem; color: var(--muted);
  }
  footer p { margin: 0 0 8px; }
  @media print { .bar { display: none; } }
</style>
</head>
<body>

<header class="masthead">
  <div class="wrap">
    <div class="topline">
      <div class="brand">
        <svg width="30" height="30" viewBox="0 0 34 34" aria-hidden="true" fill="none">
          <circle cx="17" cy="17" r="16" stroke="currentColor" stroke-width="1.5" opacity=".45"/>
          <path d="M3 20.5c3-3.4 5.6-3.4 8.5 0s5.5 3.4 8.5 0 5.6-3.4 8.5 0" stroke="currentColor"
                stroke-width="1.9" stroke-linecap="round" opacity=".95"/>
          <path d="M6 25.6c2.4-2.7 4.5-2.7 6.8 0s4.4 2.7 6.8 0 4.5-2.7 6.8 0" stroke="currentColor"
                stroke-width="1.5" stroke-linecap="round" opacity=".5"/>
          <path d="M11 11.5h12M11 8h8" stroke="currentColor" stroke-width="1.9"
                stroke-linecap="round" opacity=".8"/>
        </svg>
        <h1>{{TITLE}}</h1>
      </div>
      <button class="themebtn" id="theme" type="button" aria-label="Switch between light and dark">
        <svg id="themeicon" width="17" height="17" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"></svg>
      </button>
    </div>
    <p class="tagline">{{TAGLINE}}</p>
    <p class="issue">{{COUNT}} summaries &middot; updated {{GENERATED}}</p>
  </div>
</header>

<div class="bar" id="bar">
  <div class="wrap">
    <div class="controls">
      <input id="q" type="search" placeholder="Search summaries" aria-label="Search summaries">
      <select id="species" aria-label="Filter by species"><option value="">All species</option></select>
      <select id="region" aria-label="Filter by region"><option value="">All regions</option></select>
      <select id="program" aria-label="Filter by programme"><option value="">All programmes</option></select>
      <select id="kind" aria-label="Filter by document type"><option value="">All types</option></select>
    </div>
    <p class="resultline">
      <span id="count"></span>
      <button class="clear" id="clear" type="button" hidden>Clear filters</button>
    </p>
  </div>
</div>

<div class="wrap">
  <main id="list"></main>

  <footer>
    <p>{{DISCLAIMER}}</p>
    <p>Summaries are drafted automatically and reviewed by a person before publication.
       Open questions are shown rather than hidden. Source data: the U.S. Federal Register.</p>
  </footer>
</div>

<script type="application/json" id="payload">{{DATA}}</script>
<script>
(function () {
  var data = JSON.parse(document.getElementById('payload').textContent);
  var list = document.getElementById('list');
  var count = document.getElementById('count');
  var clear = document.getElementById('clear');
  var q = document.getElementById('q');
  var bar = document.getElementById('bar');
  var sel = {
    species: document.getElementById('species'),
    region: document.getElementById('region'),
    program: document.getElementById('program'),
    kind: document.getElementById('kind')
  };

  /* --- theme toggle --- */
  var SUN = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4'
          + 'M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>';
  var MOON = '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>';
  var icon = document.getElementById('themeicon');
  var btn = document.getElementById('theme');

  function prefersDark() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
  function isDark() {
    var set = document.documentElement.getAttribute('data-theme');
    return set ? set === 'dark' : prefersDark();
  }
  function paintIcon() {
    // Show what clicking will switch TO, which is the convention people expect.
    icon.innerHTML = isDark() ? SUN : MOON;
  }
  btn.addEventListener('click', function () {
    var next = isDark() ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
    paintIcon();
  });
  paintIcon();

  /* --- sticky bar shadow --- */
  var sentinel = document.createElement('div');
  bar.parentNode.insertBefore(sentinel, bar);
  if (window.IntersectionObserver) {
    new IntersectionObserver(function (entries) {
      bar.classList.toggle('stuck', !entries[0].isIntersecting);
    }).observe(sentinel);
  }

  /* --- filters --- */
  function fill(node, values) {
    values.forEach(function (v) {
      var o = document.createElement('option');
      o.value = v; o.textContent = v;
      node.appendChild(o);
    });
  }
  fill(sel.species, data.species);
  fill(sel.region, data.regions);
  fill(sel.program, data.programs || []);
  fill(sel.kind, data.types);

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
                'August', 'September', 'October', 'November', 'December'];

  // "2026-09-10" -> "10 September 2026". Parsed as parts, never through Date(),
  // so a browser west of UTC cannot shift a regulatory date by a day.
  function longDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || '');
    if (!m) return null;
    return parseInt(m[3], 10) + ' ' + MONTHS[parseInt(m[2], 10) - 1] + ' ' + m[1];
  }

  function matches(n) {
    var term = q.value.trim().toLowerCase();
    if (term) {
      var hay = [n.title, n.what_changed, n.who_affected]
        .concat(n.key_details).concat(n.species).concat(n.regions)
        .join(' ').toLowerCase();
      if (hay.indexOf(term) === -1) return false;
    }
    if (sel.species.value && n.species.indexOf(sel.species.value) === -1) return false;
    if (sel.region.value && n.regions.indexOf(sel.region.value) === -1) return false;
    if (sel.program.value && (n.programs || []).indexOf(sel.program.value) === -1) return false;
    if (sel.kind.value && n.type !== sel.kind.value) return false;
    return true;
  }

  function card(n) {
    var tags = n.species.map(function (s) {
      return '<span class="tag sp">' + esc(s) + '</span>';
    }).concat(n.regions.map(function (r) {
      return '<span class="tag rg">' + esc(r) + '</span>';
    })).join('');

    var progs = (n.programs || []).map(function (p) {
      return '<span class="prog">' + esc(p) + '</span>';
    }).join('');

    var eff = longDate(n.effective);
    var effBlock = '<div class="eff"><span class="lab">Effective</span>'
      + (eff ? '<span class="val">' + esc(eff) + '</span>'
             : '<span class="val none">Not stated in the notice</span>')
      + '</div>';

    var who = n.who_affected
      ? '<p class="who"><strong>Who it affects</strong>' + esc(n.who_affected) + '</p>'
      : '';

    var details = n.key_details.length
      ? '<details class="details"><summary>Key details ('
        + n.key_details.length + ')</summary><ul class="details">'
        + n.key_details.map(function (d) { return '<li>' + esc(d) + '</li>'; }).join('')
        + '</ul></details>'
      : '';

    var open = n.open_questions.length
      ? '<details class="flag"><summary>Open questions ('
        + n.open_questions.length + ')</summary><div class="flagbox">'
        + '<p>This summary could not settle the following. Check the original notice.</p><ul>'
        + n.open_questions.map(function (u) { return '<li>' + esc(u) + '</li>'; }).join('')
        + '</ul></div></details>'
      : '';

    var disclosures = (details || open)
      ? '<div class="disc">' + details + open + '</div>' : '';

    var pub = longDate(n.published);

    return '<article id="' + esc(n.id) + '">'
      + '<div class="kicker">' + progs
      + '<span class="kind">' + esc(n.type || 'Document') + '</span>'
      + (pub ? '<span class="dot">&bull;</span><time datetime="' + esc(n.published) + '">'
               + esc(pub) + '</time>' : '')
      + '</div>'
      + '<h2>' + esc(n.title) + '</h2>'
      + effBlock
      + '<p class="what">' + esc(n.what_changed) + '</p>'
      + who + disclosures
      + '<div class="tags">' + tags + '</div>'
      + '<div class="foot">'
      + '<span class="pub">Document ' + esc(n.id) + '</span>'
      + '<a class="source" href="' + esc(n.url) + '" rel="noopener">Read the original &rarr;</a>'
      + '</div>'
      + '</article>';
  }

  function render() {
    var shown = data.notices.filter(matches);
    var filtered = q.value.trim() || sel.species.value || sel.region.value
                || sel.program.value || sel.kind.value;

    count.textContent = shown.length + (shown.length === 1 ? ' summary' : ' summaries')
      + (filtered ? ' of ' + data.notices.length : '');
    clear.hidden = !filtered;

    list.innerHTML = shown.length
      ? shown.map(card).join('')
      : '<p class="empty">Nothing matches those filters.</p>';
  }

  q.addEventListener('input', render);
  Object.keys(sel).forEach(function (k) { sel[k].addEventListener('change', render); });
  clear.addEventListener('click', function () {
    q.value = '';
    Object.keys(sel).forEach(function (k) { sel[k].value = ''; });
    render();
  });

  render();
})();
</script>
</body>
</html>
"""
