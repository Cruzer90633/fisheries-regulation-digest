# Region Vocabulary

Controlled list used for tagging and filtering. Tags come from this file only.

**Verified 2026-09-20.** The region extent comes from NOAA's own description of the
Greater Atlantic Regional Fisheries Office. The stock and management area names come
from the fishery management plans themselves, not from general usage.

## Broad areas

- Greater Atlantic
- New England
- Mid-Atlantic
- Federal waters (EEZ)
- State waters

GARFO describes the Greater Atlantic Region as roughly 100,000 square miles of the
Northwest Atlantic, covering the large marine ecosystems **from Maine to Cape Hatteras,
North Carolina**, plus the Great Lakes and the rivers and estuaries in that range.
Source: [GARFO — About Us](https://www.fisheries.noaa.gov/about/greater-atlantic-regional-fisheries-office).

Federal waters run 3 to 200 nautical miles offshore. State waters run 0 to 3 nautical
miles. Both are written out in full here because the abbreviations rarely appear alone
in a notice.

## States

The eleven states in the Greater Atlantic Region, north to south. These are the same
states that receive commercial quota allocations in the summer flounder, scup, black
sea bass, and bluefish fisheries, which is why state names turn up constantly in quota
transfer notices.

- Maine
- New Hampshire
- Massachusetts
- Rhode Island
- Connecticut
- New York
- New Jersey
- Delaware
- Maryland
- Virginia
- North Carolina

## Stock and management areas

These names come from the Northeast Multispecies FMP's own stock list
([nefmc.org](https://www.nefmc.org/management-plans/northeast-multispecies)). They
appear verbatim in groundfish notices, so they are tags rather than free text.

- Gulf of Maine
- Eastern Gulf of Maine
- Western Gulf of Maine
- Georges Bank
- Southern New England
- Cape Cod

A stock is often named as a compound, for example "Southern New England/Mid-Atlantic
yellowtail flounder" or "Cape Cod/Gulf of Maine yellowtail flounder". Tag each named
area in the compound separately.

## Atlantic Highly Migratory Species areas

**Verified 2026-09-20** against the full text of 50 CFR part 635, retrieved from the
eCFR API. These are not council areas — HMS fisheries range far beyond the Greater
Atlantic Region, so these tags cover water the rest of this file does not.

### Ocean basins

The regulation defines its own scope, at 50 CFR 635.2: *"Atlantic Ocean, as used in
this part, includes the North and South Atlantic Oceans, the Gulf of America, and the
Caribbean Sea."* Tag the specific water body when the notice names one, and Atlantic
Ocean when it does not.

Gulf of America is the current name in the regulations; older notices say Gulf of
Mexico. The alternate resolves to the same tag, so a search for either finds both.

- Atlantic Ocean
- Gulf of America (Gulf of Mexico)
- Caribbean Sea

### Gear restricted areas

Listed at 50 CFR 635.35, with coordinates defined at 635.2. A small, fixed, named set —
unlike the council statistical areas below, these are worth tagging.

- Mid-Atlantic Bottom Longline Gear Restricted Area
- Charleston Bump Gear Restricted Area
- East Florida Coast Gear Restricted Area
- DeSoto Canyon Gear Restricted Area
- Northeast Distant Gear Restricted Area (NED)

### Monitoring areas

- Charleston Bump Monitoring Area
- East Florida Coast Monitoring Area

### Basin-wide actions also get Greater Atlantic

A notice whose scope is the whole U.S. Atlantic — an ocean-basin quota, a gear rule
covering the Atlantic Ocean, Gulf of America, and Caribbean Sea — **also gets the
Greater Atlantic tag**, because such a rule reaches waters from Maine to Cape Hatteras
and therefore affects readers of this digest.

The basin tags say where a rule applies. Greater Atlantic keeps it findable for
someone filtering by their own region. Without it, a fisherman in New England filtering
for their area would miss a swordfish quota that genuinely binds them.

The exception: do not add Greater Atlantic when every area the notice names sits
outside that range. A closure limited to the Gulf of America or the Caribbean Sea gets
the basin tag alone.

### Stock boundaries, recorded but not tagged

Swordfish stocks split at a line of latitude rather than a named area: North Atlantic
swordfish means fish north of 5° N, South Atlantic swordfish south of it. That is a
property of the stock, not a place, so it belongs in the species tag and the summary
text, not here.

### Deliberately excluded

The pelagic longline statistical reporting areas NEC, NCA, and SAR appear in proposed
rule discussions but are **not defined anywhere in 50 CFR 635** — checked 2026-09-20.
They are not tags. A summary that meets them should say so in `unclear`.

Gulf of Maine is not an HMS area in the regulations either, though bluefin tuna angling
category notices use it operationally. It is already in the stock areas section above,
which covers those notices.

## Areas recorded verbatim, not tagged

Statistical areas, scallop access areas, and closed areas are referenced by their
official designation exactly as the notice writes it — "Closed Area II", "Statistical
Area 537", "Nantucket Lightship Access Area". Record the designation as given. Do not
paraphrase it, and do not add it to this vocabulary; there are too many and they change
by action.

## Rules

- Tag the narrowest area the notice actually names, plus the broad area it sits in.
- A rule covering the whole U.S. Atlantic also gets Greater Atlantic, unless every
  area it names lies outside Maine to Cape Hatteras. See the HMS section above.
- If a notice gives coordinates but no named area, record the coordinates verbatim and
  tag the broad area only.
- Never infer a state or area the notice does not name.
