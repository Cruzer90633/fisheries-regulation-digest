"""Generate the static site from approved summaries.

Writes outputs/site/index.html (self-contained) and outputs/site/data.json.

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

    payload = {
        "generated": date.today().isoformat(),
        "count": len(cards),
        "species": species,
        "regions": regions,
        "types": types,
        "notices": cards,
    }

    (out / "data.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )

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
    --border:  #dde5ea;
    --text:    #13232c;
    --muted:   #5d7180;
    --flag-bg: #fdf6e6;
    --flag-br: #e8d9ae;
    --flag-tx: #6b5415;
    --shadow:  0 1px 2px rgba(19,35,44,.05), 0 8px 24px -16px rgba(19,35,44,.25);
    --radius:  12px;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --deep:    #7fd3e8;
      --deep-2:  #4fb4cd;
      --accent:  #58bcd6;
      --sand:    #1b2730;
      --bg:      #0d151a;
      --surface: #141f27;
      --border:  #263643;
      --text:    #e8f0f4;
      --muted:   #93a8b5;
      --flag-bg: #241f12;
      --flag-br: #4a3f21;
      --flag-tx: #e0cb92;
      --shadow:  none;
    }
  }
  :root[data-theme="dark"] {
    --deep:#7fd3e8; --deep-2:#4fb4cd; --accent:#58bcd6; --sand:#1b2730;
    --bg:#0d151a; --surface:#141f27; --border:#263643; --text:#e8f0f4;
    --muted:#93a8b5; --flag-bg:#241f12; --flag-br:#4a3f21; --flag-tx:#e0cb92;
    --shadow:none;
  }

  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  body {
    margin: 0; background: var(--bg); color: var(--text);
    font: 400 16px/1.65 "Source Sans 3", system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  .wrap { max-width: 880px; margin: 0 auto; padding: 0 16px 72px; }

  .masthead {
    background: var(--deep); color: var(--sand);
    margin: 0 0 28px; padding: 34px 0 30px;
    border-bottom: 3px solid var(--accent);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) .masthead { background: var(--surface); color: var(--text); }
    :root:not([data-theme="light"]) .issue { border-top-color: var(--border); }
  }
  :root[data-theme="dark"] .masthead { background: var(--surface); color: var(--text); }
  :root[data-theme="dark"] .issue { border-top-color: var(--border); }
  .masthead .wrap { padding-bottom: 0; }
  .brand { display: flex; align-items: center; gap: 13px; }
  .brand svg { flex: 0 0 auto; }
  h1 {
    margin: 0; font-family: Fraunces, Georgia, serif; font-weight: 600;
    font-size: clamp(1.5rem, 4.4vw, 2.05rem); line-height: 1.12; letter-spacing: -.015em;
  }
  .tagline { margin: 9px 0 0; opacity: .82; font-size: .97rem; max-width: 56ch; }
  .issue {
    margin-top: 16px; padding-top: 13px; border-top: 1px solid rgba(255,255,255,.16);
    font-size: .8rem; letter-spacing: .07em; text-transform: uppercase; opacity: .72;
  }

  .controls { display: grid; gap: 9px; margin-bottom: 6px; }
  @media (min-width: 680px) { .controls { grid-template-columns: 1.6fr 1fr 1fr 1fr; } }
  input, select {
    width: 100%; padding: 10px 12px; font: inherit; font-size: .93rem;
    color: var(--text); background: var(--surface);
    border: 1px solid var(--border); border-radius: 8px;
  }
  input:focus-visible, select:focus-visible, a:focus-visible, button:focus-visible {
    outline: 2px solid var(--accent); outline-offset: 2px;
  }
  .resultline {
    margin: 14px 0 20px; font-size: .86rem; color: var(--muted);
    display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  }
  .clear {
    background: none; border: 0; padding: 0; font: inherit; font-size: .86rem;
    color: var(--accent); cursor: pointer; text-decoration: underline;
  }

  article {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 22px 22px 18px;
    margin-bottom: 18px; box-shadow: var(--shadow);
  }
  .kicker {
    display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    margin-bottom: 9px; font-size: .74rem; letter-spacing: .08em; text-transform: uppercase;
  }
  .kind { font-weight: 700; color: var(--deep-2); }
  .kicker .dot { color: var(--border); }
  .kicker time { color: var(--muted); }
  article h2 {
    margin: 0 0 14px; font-family: Fraunces, Georgia, serif; font-weight: 600;
    font-size: 1.16rem; line-height: 1.34; letter-spacing: -.008em;
  }
  .effective {
    display: flex; align-items: baseline; gap: 9px; flex-wrap: wrap;
    background: var(--sand); border-radius: 9px; padding: 9px 13px; margin-bottom: 15px;
  }
  .effective .lab {
    font-size: .7rem; letter-spacing: .09em; text-transform: uppercase; color: var(--muted);
  }
  .effective .val { font-weight: 700; font-size: 1.02rem; }
  .effective .val.none { font-weight: 600; font-size: .92rem; color: var(--muted); }
  .what { margin: 0 0 13px; font-size: 1.04rem; }
  .who { margin: 0 0 15px; color: var(--muted); font-size: .95rem; }
  .who strong {
    display: block; font-size: .7rem; letter-spacing: .09em; text-transform: uppercase;
    color: var(--muted); margin-bottom: 3px; font-weight: 700;
  }
  details.details, details.flag { margin-bottom: 14px; }
  details > summary {
    cursor: pointer; font-size: .82rem; font-weight: 600; color: var(--accent);
    list-style: none; padding: 3px 0;
  }
  details > summary::-webkit-details-marker { display: none; }
  details > summary::before { content: "\25B8"; display: inline-block; margin-right: 7px; transition: transform .15s; }
  details[open] > summary::before { transform: rotate(90deg); }
  ul.details { margin: 9px 0 0; padding-left: 19px; font-size: .93rem; }
  ul.details li { margin-bottom: 5px; }

  details.flag > summary { color: var(--flag-tx); }
  .flagbox {
    margin-top: 9px; background: var(--flag-bg); border: 1px solid var(--flag-br);
    border-radius: 9px; padding: 11px 13px 11px 15px;
  }
  .flagbox p { margin: 0 0 8px; font-size: .82rem; color: var(--flag-tx); }
  .flagbox ul { margin: 0; padding-left: 17px; font-size: .9rem; }
  .flagbox li { margin-bottom: 5px; }

  .tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 15px; }
  .tag {
    font-size: .76rem; padding: 3px 10px; border-radius: 999px; white-space: nowrap;
    border: 1px solid transparent;
  }
  .tag.sp { background: color-mix(in srgb, var(--accent) 13%, transparent); color: var(--deep-2); }
  .tag.rg { background: transparent; border-color: var(--border); color: var(--muted); }

  .foot {
    display: flex; justify-content: space-between; align-items: center; gap: 12px;
    flex-wrap: wrap; border-top: 1px solid var(--border); padding-top: 13px;
  }
  .foot .pub { font-size: .8rem; color: var(--muted); }
  a { color: var(--accent); }
  .source { font-size: .88rem; font-weight: 700; text-decoration: none; }
  .source:hover { text-decoration: underline; }

  .empty {
    padding: 52px 16px; text-align: center; color: var(--muted);
    border: 1px dashed var(--border); border-radius: var(--radius);
  }
  footer {
    margin-top: 44px; padding-top: 22px; border-top: 1px solid var(--border);
    font-size: .83rem; color: var(--muted);
  }
  footer p { margin: 0 0 9px; }
  @media print { .controls, .resultline { display: none; } }
</style>
</head>
<body>

<header class="masthead">
  <div class="wrap">
    <div class="brand">
      <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true" fill="none">
        <circle cx="17" cy="17" r="16" stroke="currentColor" stroke-width="1.5" opacity=".45"/>
        <path d="M3 20.5c3-3.4 5.6-3.4 8.5 0s5.5 3.4 8.5 0 5.6-3.4 8.5 0" stroke="currentColor"
              stroke-width="1.9" stroke-linecap="round" opacity=".95"/>
        <path d="M6 25.6c2.4-2.7 4.5-2.7 6.8 0s4.4 2.7 6.8 0 4.5-2.7 6.8 0" stroke="currentColor"
              stroke-width="1.5" stroke-linecap="round" opacity=".5"/>
        <path d="M11 11.5h12M11 8h8" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" opacity=".8"/>
      </svg>
      <h1>{{TITLE}}</h1>
    </div>
    <p class="tagline">{{TAGLINE}}</p>
    <p class="issue">{{COUNT}} summaries &middot; updated {{GENERATED}}</p>
  </div>
</header>

<div class="wrap">
  <div class="controls">
    <input id="q" type="search" placeholder="Search summaries" aria-label="Search summaries">
    <select id="species" aria-label="Filter by species"><option value="">All species</option></select>
    <select id="region" aria-label="Filter by region"><option value="">All regions</option></select>
    <select id="kind" aria-label="Filter by document type"><option value="">All types</option></select>
  </div>

  <p class="resultline">
    <span id="count"></span>
    <button class="clear" id="clear" type="button" hidden>Clear filters</button>
  </p>

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
  var sel = {
    species: document.getElementById('species'),
    region: document.getElementById('region'),
    kind: document.getElementById('kind')
  };

  function fill(node, values) {
    values.forEach(function (v) {
      var o = document.createElement('option');
      o.value = v; o.textContent = v;
      node.appendChild(o);
    });
  }

  fill(sel.species, data.species);
  fill(sel.region, data.regions);
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
    if (sel.kind.value && n.type !== sel.kind.value) return false;
    return true;
  }

  function card(n) {
    var tags = n.species.map(function (s) {
      return '<span class="tag sp">' + esc(s) + '</span>';
    }).concat(n.regions.map(function (r) {
      return '<span class="tag rg">' + esc(r) + '</span>';
    })).join('');

    var eff = longDate(n.effective);
    var effBlock = '<div class="effective"><span class="lab">Effective</span>'
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

    var pub = longDate(n.published);

    return '<article id="' + esc(n.id) + '">'
      + '<div class="kicker"><span class="kind">' + esc(n.type || 'Document') + '</span>'
      + (pub ? '<span class="dot">&bull;</span><time datetime="' + esc(n.published) + '">'
               + esc(pub) + '</time>' : '')
      + '</div>'
      + '<h2>' + esc(n.title) + '</h2>'
      + effBlock
      + '<p class="what">' + esc(n.what_changed) + '</p>'
      + who + details + open
      + '<div class="tags">' + tags + '</div>'
      + '<div class="foot">'
      + '<span class="pub">Document ' + esc(n.id) + '</span>'
      + '<a class="source" href="' + esc(n.url) + '" rel="noopener">Read the original &rarr;</a>'
      + '</div>'
      + '</article>';
  }

  function render() {
    var shown = data.notices.filter(matches);
    var filtered = q.value.trim() || sel.species.value || sel.region.value || sel.kind.value;

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
