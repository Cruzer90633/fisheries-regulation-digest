# Species Vocabulary

Controlled list used for tagging and filtering. Tags come from this file only.

**Verified 2026-09-20** against each managing body's own species pages. Sources are
named under each section. Re-check when a new amendment or addendum changes a list.

Format: `- Canonical name (common alternate)`. Both forms resolve to the canonical
name, so a notice saying "fluke" tags as "Summer flounder".

## Mid-Atlantic Fishery Management Council

Source: [mafmc.org/fishery-management-plans](https://www.mafmc.org/fishery-management-plans).
Seven FMPs covering 15 species.

**Summer Flounder, Scup, and Black Sea Bass FMP**

- Summer flounder (fluke)
- Scup (porgy)
- Black sea bass

**Bluefish FMP**

- Bluefish

**Mackerel, Squid, and Butterfish FMP** — five species, per
[mafmc.org/msb](https://www.mafmc.org/msb)

- Atlantic mackerel
- Chub mackerel
- Longfin squid
- Illex squid (shortfin squid)
- Butterfish

**Atlantic Surfclam and Ocean Quahog FMP**

- Atlantic surfclam
- Ocean quahog

**Golden and Blueline Tilefish FMP**

- Golden tilefish
- Blueline tilefish

**Spiny Dogfish FMP** — joint with New England

- Spiny dogfish

**Monkfish FMP** — joint with New England

- Monkfish (goosefish)

## New England Fishery Management Council

Source: [nefmc.org/management-plans](https://www.nefmc.org/management-plans). Nine FMPs
covering, in the Council's own words, 28 marine species and one anadromous species.
The lists below add up to exactly that.

**Northeast Multispecies (Groundfish) FMP** — 13 large-mesh species across 22 stocks

- Atlantic cod
- Haddock
- Yellowtail flounder
- Winter flounder
- Witch flounder
- Windowpane flounder
- American plaice
- Pollock
- Acadian redfish (redfish)
- White hake
- Atlantic halibut
- Ocean pout
- Atlantic wolffish

**Small-Mesh Multispecies (Whiting) FMP** — in the Groundfish FMP, managed separately

- Silver hake (whiting)
- Red hake
- Offshore hake

**Northeast Skate Complex FMP** — seven species

- Barndoor skate
- Clearnose skate
- Little skate
- Rosette skate
- Smooth skate
- Thorny skate
- Winter skate

**Atlantic Sea Scallop FMP**

- Atlantic sea scallop

**Atlantic Herring FMP**

- Atlantic herring

**Red Crab FMP**

- Atlantic deep-sea red crab

**Atlantic Salmon FMP** — the one anadromous species

- Atlantic salmon

Monkfish and spiny dogfish are the other two New England plans. Both are joint with the
Mid-Atlantic Council and are listed above rather than repeated here.

## Atlantic States Marine Fisheries Commission

Source: [asmfc.org/species](https://asmfc.org/species/). The Commission coordinates
management of 27 shellfish, diadromous, and marine species across the 15 Atlantic
coastal states. Some are Commission-only; others are managed cooperatively with NOAA
Fisheries and the councils.

Nine of the 27 are already listed above because a council also manages them: Atlantic
herring, black sea bass, bluefish, scup, spiny dogfish, summer flounder, winter
flounder, American lobster, and Jonah crab. The remaining 18 are new here.

- American eel
- American lobster
- American shad
- Atlantic croaker
- Atlantic menhaden
- Atlantic striped bass
- Atlantic sturgeon
- Black drum
- Coastal sharks
- Cobia
- Horseshoe crab
- Jonah crab
- Northern shrimp
- Red drum
- River herring
- Spanish mackerel
- Spot
- Spotted seatrout
- Tautog
- Weakfish

American lobster and Jonah crab are repeated here because this is where they actually
belong; they are Commission species with complementary federal measures, not council
FMP species.

"Coastal sharks" is the Commission's own complex name. It overlaps the federal shark
list below, which NOAA manages separately. Tag whichever name the notice uses.

## Atlantic Highly Migratory Species

Source: [NOAA Fisheries — Atlantic Highly Migratory
Species](https://www.fisheries.noaa.gov/topic/atlantic-highly-migratory-species).
Managed by NOAA's HMS Management Division, not by GARFO or either council, and covering
U.S. Atlantic, Gulf of America, and Caribbean waters.

**Tunas**

- Bluefin tuna
- Bigeye tuna
- Yellowfin tuna
- Albacore tuna
- Skipjack tuna

**Swordfish**

- Swordfish

**Billfish**

- Blue marlin
- White marlin
- Roundscale spearfish
- Sailfish

**Sharks — retention permitted**

- Atlantic sharpnose shark
- Blacknose shark
- Blacktip shark
- Blue shark
- Bonnethead shark
- Bull shark
- Carolina hammerhead shark
- Common thresher shark
- Finetooth shark
- Florida smoothhound
- Great hammerhead shark
- Gulf smoothhound
- Lemon shark
- Nurse shark
- Porbeagle shark
- Sandbar shark
- Scalloped hammerhead shark
- Shortfin mako shark
- Silky shark
- Smooth dogfish
- Smooth hammerhead shark
- Spinner shark
- Tiger shark

**Sharks — prohibited species**

NOAA marks these as prohibited. They are still managed species and still appear in
notices, so they are still tags.

- Atlantic angel shark
- Basking shark
- Bigeye sand tiger shark
- Bigeye sixgill shark
- Bigeye thresher shark
- Bignose shark
- Caribbean reef shark
- Caribbean sharpnose shark
- Dusky shark
- Galapagos shark
- Longfin mako shark
- Narrowtooth shark
- Night shark
- Oceanic whitetip shark
- Sand tiger shark
- Sevengill shark
- Sixgill shark
- Smalltail shark
- Whale shark
- White shark

**Smooth dogfish is not spiny dogfish.** Smooth dogfish is an HMS shark. Spiny dogfish
is a council and Commission species. They are different animals under different rules,
and the names are one word apart. Check which one a notice means.

## Coverage note

The ingest filter was widened on 2026-09-20 to cover all three families. It now queries
50 CFR parts 648, 635, and 697, plus the matching title phrases, so Northeast council
actions, Highly Migratory Species actions, and Atlantic Coastal Fisheries Cooperative
Management actions all reach the pipeline. Every species on this list can now be
tagged. See `resources/source-registry.md` for the queries.

## Rules

- One canonical name per species. A common alternate goes in parentheses and resolves
  to the canonical entry.
- A notice covering several species gets several tags.
- A notice covering a whole plan, such as a groundfish framework, is tagged with every
  species that plan covers.
- River herring and shad are Commission-managed species, and they are also subject to a
  catch cap in the Mackerel, Squid, and Butterfish FMP. A notice may reference the cap
  without the rule being about the species. Tag on what the notice is actually about.
- If a notice names a species that is not on this list, leave it untagged and flag it.
  The pipeline drops unknown tags and records them rather than guessing.
