# Game Design v1.0 — complete first-playable mechanics proposal

Status: PROPOSAL, not human-approved. Strategy authored the mechanics; growth supplied attributed comparative research; qa independently critiqued and rechecked the saved rules/examples. COO consolidated this edition from GAME_DESIGN r8 and GAME_DESIGN_EXAMPLES r4 after operations delivered reports but did not update documents. Prior revisions preserve all earlier wording and failures. Sources: full protected BRIEF_V0_4.md r1 and MISSION.md r4; research and review evidence in REVIEWS.md r3–r7. No protected source or DECISIONS.md is changed.

## Executive summary
Two players manage a 40-card deck, dedicated reusable resource cards, one active fighter and three reserves. Fighters evolve through four distinct class achievements. A common 17-node Tech Tree has separate public progression and full personal reward pools for each player. Its four-node limit and resource costs force commitments; players can pivot using remaining slots. Rewards include persistent abilities, genuinely new cards and upgrades to every copy of existing actions. Win by five opposing fighter losses, eliminating all opposing fighters, or the opponent failing a mandatory draw; a round-15 limit prevents indefinite matches.

The supplied package specifies two exact legal mixed-class starters, all card/stage texts, acquisition/upgrade lifecycles, physical tracking, worked examples and a planned first playtest. QA rechecked r8 plus examples r4 in REVIEWS r7: no material mechanics blockers remained from QA-01–05. This consolidated edition still needs a final transcription/integration check. Balance, handling and match duration are unverified. No prototype has been manufactured, no match played, no software executed and no human approval granted.

## 1. Intent, scale and core loop
Prepare reserves, commit an active, spend resources on tactics or development, attack, survive opposing decisions, and evolve individual fighters. The illustrative 60-card deck is reduced to 40, with 14 Resource (35%), 12 Fighter and 14 Action, to reduce first-build handling. Three reserve slots and printed three-stage panels limit components. Target duration 25–40 minutes and 8–12 turns/player are hypotheses, not measurements.

## 2. Construction, zones and setup
Starting deck: exactly 40 = 14 Resource + 12 Fighter + 14 starting Action. Maximum four copies per Action name, twelve per Fighter name; Resources exempt. Choose one or two declared classes, at least four Fighters of each declared class, none of undeclared classes. Declaration is public and fixed. The four-name catalog has one Fighter name per class; the twelve-copy limit makes single-class construction possible. Exact starters remain six/six. Finite kit stock limits which simultaneous custom lists can be assembled. Development cards/references start outside construction.

Private zones: hand and face-down draw deck. Public: discard, removed zone, resource zone, active, three reserves, personal tree, personal face-up development pool. All damage/stage/progress, readiness, scores, classes, nodes and pool counts are public. Nobody inspects or reorders a deck without instruction. Cards never change owner. Removed cards cannot return this match. No hand limit.

Randomly determine first player. Each searches their own deck for two Resource and two Fighters, reveals and places two ready Resources, one Stage I active and one Stage I reserve, all fighter damage/progress zero. Shuffle the remaining 36, draw five. Simultaneously each may once set aside any number of those five face down, draw that many, then shuffle set-aside cards into their deck. End setup: deck31 + hand5 + resources2 + fighters2 =40; scores zero, no nodes. First player skips their first Draw and cannot attack on their first turn; second player draws and may attack normally.

## 3. Resource economy
Exhaust one ready Resource for each unit of cost. Pay exactly, no floating currency, refund or arbitrary spending. Resources refresh only at their owner's Start. Unspent ready resources can fund a defender Reaction on the opponent's turn. Resources enter ready; zone cap eight.

Once per own Main either play one Resource from hand free OR Supply: discard one non-Resource from hand, search your draw deck for a Resource, reveal/place it ready and shuffle. Supply uses that same allowance, is illegal at cap eight or with no Resource in deck, and never searches discard. This trades a useful hand card for reliable resources while retaining actual resource cards in the deck. No generic conversion into resource tokens exists.

## 4. Ordered turn, timing and reset table
Count own turns separately. A round is first player's turn then second player's.
1. Start: advance own-turn counter, apply reset/expiry table, then refresh own Resources.
2. Draw one. Exception: first player's first turn skips it. Failure of this mandatory Draw-step draw loses immediately. Effect draws take available cards without defeat. Never automatically reshuffle discard.
3. Main, in any order, each action fully resolved before another: use resource allowance; deploy a Fighter from hand into empty reserve for1; play/pay a Main Action; voluntary switch for1 once this Main (swap active and reserve); evolve once; unlock one node. No arbitrary sacrifice/discard/transfer. Newly deployed or promoted Fighters may act. Reserve cannot attack.
4. Combat: pass OR attack once with active, pay its current attack cost, target opposing active. Defender may play/pay at most one Reaction or pass; attacker cannot respond. Resolve Reaction, attack, then checkpoint. No stack or other Reaction windows; no Main after Combat.
5. End: resolve End effects and terminal checks, including round15 when applicable; clear only attack-duration additions/reductions and pass. Unspent resources stay ready.

| State | Reset or expiry |
|---|---|
| Both players' Death award allowance and X1 first-loss use | Reset for BOTH players at EVERY Start. DX shares the Death allowance. |
| Resource allowance, voluntary switch, evolution, node unlock, Hope opportunity, E1, RS, DX, DE own-turn uses | Reset for active player only at their own Start. Unowned abilities unavailable. DX still illegal after a loss already used the Death award this turn. |
| Hope tactical-spend tally | Zero for active player at own Start. First qualifying checkpoint consumes opportunity even if declined/no eligible Hope; no stored award. |
| Readiness | Refresh only active player's Resources at their Start. |
| Disrupt / until your next Start | Expire at CASTER/owner's next Start, not affected opponent's. Earlier affected unlock consumes Disrupt instead. |
| Rage/Luck per-turn caps | New allowance each Start; one attack/turn means no extra use token in this catalog. |
| A1/RA/HA/LA/injured attack addition/Guard | Recompute per announced attack. Guard ends with that attack; nothing carries to another attack. |
| Damage, stage, progress, nodes/upgrades, scores, classes and zone contents | Never reset at Start/End. Change only by explicit rule/effect or match reset; fighter leaving play resets its markers. |

No other blanket End reset. Once per turn means once during EACH player's turn; once per own turn means on yours only. Counters of own turns advance, not reset.

Main Actions cannot be played on opposing turns. Announce targets/choices before paying; no legal target means cannot play. After legal payment resolve instructions in order as much as possible; unavailable draws/discards do not halt later instructions or checkpoints or invent a card. Draw two with one available means draw one then continue; discard one if possible, otherwise none. Only mandatory Draw-step failure causes draw defeat. Costs are not undone. Resolving Action is face up outside hand/discard, and enters discard after instructions unless stated otherwise. Discard means from hand unless another zone is named. Actual exhausted resources count as spending, not discounted/hypothetical costs.

X1 draws if possible, then discards if possible, then promotion/defeat proceeds even with empty zones. Convert finishes healing/drawing after sacrifice before its checkpoint. No optional effect allows an action or Reaction between instructions.

## 5. Combat, destruction and end conditions
Only active can be an attack target. Damage counters placed = attack damage after additions then reductions, minimum0. No retaliation, spillover, accuracy roll, weakness or direct player damage. Damage persists through turns/switching/evolution. Healing removes up to the stated damage; health is a maximum, not a second current-health counter. Damage at least maximum health destroys.

Apply instructions in order. Immediately after each damage/sacrifice instruction, remove all doomed Fighters simultaneously, discard them and remove their markers. Award opponent one defeat point per friendly Fighter lost INCLUDING sacrifice. Finish the resolving action's remaining instructions. At its checkpoint process surviving eligible progress triggers; when both owners choose, turn player chooses first. Then X1, then free promotion of a reserve if active missing, then defeat check. No intervening actions or Reactions. Lethally hit Fighters cannot gain progress or evolve to survive. Promoted Fighters take no leftover damage. A resolving sacrifice's remaining instructions never prevent defeat if no Fighters remain at that check.

Lose if opponent has five points OR you have no Fighters in play. Fighters in hand do not delay defeat. Both losing at same check gives a draw. Mandatory Draw-step failure loses immediately. At end of round15, higher defeat score wins; tie draws. No other tiebreak. Concession permitted.

## 6. Evolution and class identities
Enter Stage I, progress0. Each Fighter has stage, damage and progress (0–3). Threshold I→II:2; II→III:3. Progress caps at current threshold, excess lost; Stage III never gains progress. In own Main, once total per own turn, pay1 to evolve one eligible friendly active OR reserve one stage. Remove ALL progress, retain damage/class/card identity. No mid-attack/opponent-turn evolution. Increased maximum health does not remove damage. Leaving play resets all fighter markers; later deployment starts I. No evolution-card deck or spendable progress currency.

- **Rage:** this Fighter gains1 progress when it survives an opposing attack placing at least1 damage on it, at most once/turn/Fighter. Friendly damage, sacrifice, lethal hits and non-attack damage do not qualify. Only active can be attacked, so Rage risks the active slot.
- **Hope:** once per own turn, after cumulative payment of at least3 resources for deployment, switching, Main Actions and/or attack, choose ONE eligible Hope in play for1 progress. Node/evolution costs and opposing-turn Reactions excluded. First qualifying checkpoint consumes opportunity even if declined or no eligible recipient; no stored trigger. Multiple Hope do not all grow; actual spending only.
- **Luck:** this Fighter gains1 progress if its own attack placed at least1 damage on opposing active, whether target survived or not; max once/turn. Zero damage does not qualify. No roll; reserve cannot earn attack progress.
- **Death:** when one or more OTHER friendly Fighters are destroyed/sacrificed in an event, choose one surviving eligible Death in play for1 progress. Max ONE award across all your Death per turn, either player's turn. Enemy losses do not qualify; simultaneous losses award only one. Reserve Death can progress through real losses, each still giving opposing points. No token Fighters.

At multi-trigger checkpoint remove lethal first, then apply Rage, Hope, Luck, Death awards where applicable. Progress never auto-evolves. DX can supply an alternative Death award but shares its cap. No self-damage cards exist here.

**Death III disclosure:** baseline loss-only III requires five different loss awards (2 then3). Fifth friendly loss ends the match before a later Main evolution; loss-only III is unattainable in this catalog. Reach II through two losses, then X1→DX converts finite discarded Fighters into progress without more loss points. Two DX awards on different own turns plus a third loss on another turn permit III at opposing score3 (§13.4). Thresholds unchanged; II is usable without DX. This required branch investment is provisional, not equal class pacing or proven fun.

## 7. Common Tech Tree with separate public progress
Shared means identical accessible map, NOT joint progress, ownership, market or race. Each player owns separate markers and full personal pool. Opponent unlocks grant you nothing and do not consume your options. Four retained paths: Aggression A, Survival S, Economy E, Sacrifice X. Each class has options on multiple paths.

Roots/Tier1: own turn≥2, cost2. Common Tier2/class: own turn≥4, cost3. Mixed M: own turn≥5, cost3. All Main actions, at most ONE unlock/own turn, maximum FOUR nodes total, each ID once. Pay ordinary resources, no development points or kill rebates. Prerequisites must preexist and cannot be bought same turn as child. Effects optional unless static, persistent for match, no self-stacking. No refunds, node removal, retirement or respec. Pivot by buying another root/child in a remaining slot; sunk costs and scarce slots are the opportunity cost. At four nodes only card/fighter choices redirect. No node increases resource cap or refreshes resources.

### Common nodes
| ID | Prerequisite | Complete effect |
|---|---|---|
| A1 | none | When your active attacks, may pay1 extra resource for +1 attack damage. Counts as attack payment for Hope. |
| S1 | none | All your Fighters have +1 maximum health at every stage. Does not heal. |
| E1 | none | Once per own Main, discard one card to draw one. No resource cost; discard required to use. |
| X1 | none | First time each turn one or more friendly Fighters are lost, may draw one then discard one. One use for simultaneous losses. After progress, before promotion/check; does not prevent defeat. Partial resolution per §4. |
| A2 | A1 | Acquire two Pursuit. |
| S2 | S1 | All your Repair copies become Repair+. |
| E2 | E1 | Acquire two Disrupt. |
| X2 | X1 | All your Cycle copies become Cycle+. |

### Class branches and mixed milestone
Class-node purchase also requires class declared AND friendly Stage II/III Fighter of that class currently in play. Losing the qualifying Fighter later does not deactivate the node. Maximum TWO class/mixed nodes combined within four total. Both branches of a class may coexist if their roots fit; not hard-exclusive.

| ID | Prerequisites | Complete effect |
|---|---|---|
| RA | A1; Rage | Damaged active Rage attacks for +1 damage, in addition to A1 if paid. |
| RS | S1; Rage | Once per own Main, heal1 from a friendly Rage. |
| HA | A1; Hope | Active Hope may pay1 extra resource when attacking for +2 damage; combines with A1 (+3 for +2 total payment). |
| HE | E1; Hope | Your Hope evolution costs0 instead of1; still uses once-per-own-turn evolution. |
| LA | A1; Luck | Active Luck attack +1 damage if target had zero damage when attack announced. |
| LS | S1; Luck | Immediately after voluntary switch moves active Luck to reserve, may heal2 from that Luck. Not promotion or card-driven switches. |
| DX | X1; Death | Once per own Main, remove a Fighter from your discard to award1 progress to friendly Death. SAME one-award-per-turn allowance as loss; illegal if already used or no eligible recipient. Removal not a loss. |
| DE | E1; Death | Once per own Main, remove a Fighter from your discard to draw one. Removal cost not a loss; no Death/X1 trigger. |
| M | Any two different roots; both declared classes each with a friendly Stage II+ Fighter currently in play; own turn≥5 | Immediately after your evolution action, heal2 from one OTHER friendly Fighter whose class differs from evolved Fighter. One use per evolution; no free evolution/progress/class conversion. Single-class cannot buy M. Counts as one class/mixed node. |

Links: A1→A2/RA/HA/LA; S1→S2/RS/LS; E1→E2/HE/DE; X1→X2/DX; any two different roots→M with its additional gates. 17 nodes =4 roots+4 common children+8 class branches+M.

### New-card acquisition and lifecycle
Mandatory when unlocked: reveal both personal pool cards, put ONE in hand, shuffle OTHER into remaining draw deck immediately. Empty deck becomes a one-card face-down pile. NEVER include existing discard/removed. Acquisition: hand+1/deck+1/discard+0. Shuffle whole remaining draw pile without inspection or revealing other hand contents. Matching opaque sleeves.

Each acquired name max two copies; each node once, no opponent pool or other acquisition route. Owned circulating cards 40→42→44 before removals; construction ratios may change during match. Deck size here is circulating ownership, not draw-pile size. Used/discarded rewards have no return effect; NO discard reshuffle. New one-card pile can satisfy next mandatory draw but cannot avert later empty-draw defeat by itself. Repeating purchases/respec cannot farm rewards.

### Existing-card upgrade lifecycle
All copies of base identity in hand, draw deck, discard or play use replacement text for rest of match, including copies drawn later. Public node/reference; no hidden search, marking or sleeve swap. No cards inserted/removed/shuffled. Base name/copy identity unchanged. Repair+ replaces Repair entirely, Cycle+ replaces Cycle entirely. No second upgrade to same identity; other continuous effects apply after replacement. Player-owned upgrade persists through individual zone changes; removed cards stay removed. No permanent attachments/individually upgraded Fighters. Match reset restores base texts.

### Adaptive choices and safeguards
Defensive Rage may buy S1/RS then pivot via A1/RA over separate turns (four slots, two class nodes), instead of being forced into offense. E1/E2 taxes a visible opposing development plan; A1/A2 punishes damaged reserves. Buying a counter delays healing, attacks or another upgrade. Fixed turn gates, one unlock/turn, resource competition, finite pools, no kill-funded research, point-giving sacrifices and capped triggers resist progression loops; they do NOT establish effective comeback. Leaders can also buy counters. Four full slots end tree redirection; M may be win-more. Test these risks rather than adding more systems speculatively.

## 8. Complete card catalog
All values provisional. Class printed, no dual-class Fighters. Deploy any Fighter for1 into reserve at Stage I. Only current stage line applies, not inherited cumulative abilities. Print three stage lines on each Fighter; no separate evolution cards.

**Resource — Resource card:** Once during own Main use resource allowance to play ready from hand if fewer than eight in zone. Exhaust to pay1 of a legal cost; refresh at own Start. No class, health, attack or other ability. Supply may find it.

### Fighters
Every attack targets opposing active. Table damage is before modifiers/reductions. No other abilities besides printed Rage attack condition and global class evolution rules.

| Name / class | Stage | Maximum health | Attack cost | Attack text |
|---|---|---:|---:|---|
| Rage Fighter / Rage | I |7|2|Deal2 damage.|
| Rage Fighter / Rage | II |9|2|Deal3 damage; add1 if this Fighter has at least3 damage when attack announced.|
| Rage Fighter / Rage | III |11|2|Deal4 damage; add1 if this Fighter has at least3 damage when attack announced.|
| Hope Fighter / Hope | I |6|2|Deal2 damage.|
| Hope Fighter / Hope | II |8|2|Deal3 damage.|
| Hope Fighter / Hope | III |10|1|Deal4 damage.|
| Luck Fighter / Luck | I |5|1|Deal2 damage.|
| Luck Fighter / Luck | II |7|2|Deal3 damage.|
| Luck Fighter / Luck | III |9|2|Deal5 damage.|
| Death Fighter / Death | I |6|2|Deal2 damage.|
| Death Fighter / Death | II |8|2|Deal3 damage.|
| Death Fighter / Death | III |10|2|Deal4 damage.|

Rage condition combines with RA/paid A1. Hope discount is cost change, not refund. Luck's cheap I attack risks lower health; Death's identity is loss-fed reserve progress/branches rather than an extra stage ability. No equal evolution-speed claim.

### Five starting Action identities
**Repair — Main Action, cost1.** Choose friendly Fighter with at least1 damage. Heal3 from it.

**Cycle — Main Action, cost1.** Draw two, then discard one. Take only available effect draws; discard none if unable. Resolving Cycle is not in hand/discard during instructions.

**Guard — Reaction, cost1.** Only as defender in attack Reaction window against your active. Reduce that attack damage by2, minimum0. Does not prevent non-attack damage or move active. Uses sole defender Reaction; keep face up until attack resolves, then discard.

**Reposition — Main Action, cost0.** Choose friendly reserve and exchange with active. Keep both Fighters' stage/progress/damage. Card-driven switch, no additional resource, neither uses nor satisfies voluntary-switch action, no LS trigger. Need both active and reserve.

**Convert — Main Action, cost1.** Choose friendly reserve, sacrifice it, then heal3 from active and draw one. Sacrifice an instruction, not resource payment. Opponent scores1; eligible Death/X1 at action checkpoint after remaining instructions. Heal allowed even with active damage0. Fifth point still defeats you at check. Draw available card only, no empty-effect-draw defeat. No reserve means illegal; cannot sacrifice last/only Fighter.

### Development-only Actions
**Pursuit — Main Action, cost2.** Choose opposing reserve Fighter and deal2 damage. Normal destruction/loss triggers. Not an attack, cannot target active, grants no Rage/Luck progress. Illegal without opposing reserve.

**Disrupt — Main Action, cost1.** Until your next Start, opponent's next node unlock costs2 extra resources, consuming effect. Multiple Disrupt against same player do not stack. Put caster-labeled reminder beside affected tree; remove on affected unlock or caster's next Start, whichever first. Changes only cost, not gates/prerequisites/caps or existing nodes/cards/health. May play against player with no nodes; they may wait it out.

Hand reward copy may be used same Main if affordable. Other copy shuffled into draw deck as §7. Neither has return-from-discard ability; two/name acquired once from personal pool.

### Upgrade references — never playable cards
**Repair+ — S2 replacement text; Main Action, cost1.** Choose friendly Fighter with at least1 damage; heal4. If it is in reserve, may then exchange with active. No extra cost, no voluntary-switch allowance use, no LS. Healing active gives no exchange option. Base identity Repair.

**Cycle+ — X2 replacement text; Main Action, cost0.** Draw two then discard one (available draws only; discard none if unable). May then remove one card from your discard. If you do, choose friendly Fighter and heal1. Resolving Cycle+ not yet discard, cannot remove itself. Removal not a loss, even for Fighter: no point, Death or X1. Base identity Cycle.

References beside node, not in hand/deck/discard; full text replaces all copies including already-held ones. Not extra construction/copy identities.

## 9. Exact legal starters and personal pools
| Card | Starter A (Rage/Hope) | Starter B (Luck/Death) |
|---|---:|---:|
| Resource |14|14|
| Rage Fighter |6|0|
| Hope Fighter |6|0|
| Luck Fighter |0|6|
| Death Fighter |0|6|
| Repair |4|3|
| Cycle |4|3|
| Guard |3|4|
| Reposition |3|2|
| Convert |0|2|
| TOTAL |40|40|

Both 14 Resource+12 Fighter+14 Action, six each declared class≥4, Actions≤4/name, Fighters≤12/name. A Actions4+4+3+3=14; B3+3+4+2+2=14. Suggested teaching setup A Rage active/Hope reserve, B Luck active/Death reserve; optional, not mandatory.

Combined starting stock: Resource28, six each of four Fighters (24), Repair7, Cycle7, Guard7, Reposition5, Convert2 =80.
Each player's personal pool: Pursuit2, Disrupt2, plus one Repair+ and one Cycle+ non-playable reference. Box pool8 game cards, four references. Both boards have all17 nodes; class gates restrict purchases. None in starting40. Max44 circulating cards before removals; removing cards never reopens rewards. After match return rewards to pool, restore removed starters, clear nodes/upgrades/markers and rebuild exact40. No irreversible component alterations.

The old r5–r7 second-copy-to-discard rule is superseded: it stranded a reward without return. Only hand+shuffled-deck is current; no discard recycling introduced. Prior revisions preserve the error/fix evidence.

## 10. Exact physical kit and tracking
This is a build specification, not manufactured material. No application, stickers, permanent card destruction, attachments, evolution deck or individual-copy upgrade markers.

### Cards, sleeves, boards and references
- 80 starter game cards in §9 quantities.
- 8 development game cards: Pursuit4/Disrupt4 split into two identical pools.
- 4 unsleeved non-playable upgrade references: Repair+2/Cycle+2, full replacement text, marked REFERENCE / DO NOT SHUFFLE.
- 88 opaque sleeves:44 matching per owner (40 starter+4 pool). No distinguishable acquired-card backs/thickness. Zero replacement game cards; zero evolution game cards.
- 2 identical player boards: active1, reserve3, Resource8, zones labeled, four declaration boxes, full17-node map with IDs/links/costs/gates/full effects and turn-use strip. Include class-stage rules and combined two-class-node cap; arrows alone insufficient.
- 2 rules reference sheets: ordered phases, reset table, defender-only Reaction, checkpoint order, evolution/thresholds, Supply, defeat/round cap and match reset. Both sides permitted; do not omit lethal or Hope exclusions.
Total92 card-sized pieces (88 game cards+4 references), two boards, two rules sheets.

### Optional fighter-stock expansion, NOT in starter totals
Add24 Fighters (six extra of each class) plus24 matching sleeves to supply twelve/name. Expanded112 game cards,116 card-sized pieces,112 sleeves. No new text/aids/markers. Supports a legal single-class choice with available Resource/Action stock, not arbitrary simultaneous deck pairs. Two identical mono-class decks need24 of that Fighter name, not supplied; Action stock also finite (e.g. seven Repair, not eight for two four-Repair lists). Unselected stock stays outside match and cannot be acquired. Single-class list:14 Resource+12 that Fighter+14 legal starting Actions; cannot buy M. Two-class fighter splits4/8 through8/4. Exact two starters require no expansion.

### 67 reusable tracking pieces (two-player totals)
| Component | Quantity | Range/use |
|---|---:|---|
| Stage clips |8|I/II/III, one/Fighter in play|
| Progress sliders/dials |8|0–3; I cap2, II cap3, III0|
| Damage dials |8|0–20, damage NOT remaining health|
| Node markers |8|4/player, owner+slot labeled|
| Declaration markers |4|2/player, fixed classes|
| Turn-use markers |22|11/player boxes: resource, voluntary switch, evolution, unlock, Hope, Death, E1, X1, RS, DX, DE|
| Tactical-spend dials |2|0–8, actual qualifying Hope spending|
| Score dials |2|0–8, opposing Fighters lost; victory at5|
| Own-turn dials |2|0–15, start0|
| Disrupt reminders |2|Caster/owner labeled|
| First-player marker |1|Fixed for match|

Sum8+8+8+8+4+22+2+2+2+2+1=67. DX use box redundant with shared Death allowance but aids reminders. Reset per §4, not all at End. Rage/Luck need no extra use token with one attack/turn. No fighter/resource-unit/development-currency tokens. Resource exhaustion by rotation.

Max attack7: Rage III4+injured1+RA1+A1=7; Hope III4+HA2+A1=7; Luck III5+LA1+A1=7; Death4+A1=5. Class additions cannot combine on one Fighter; Pursuit separate. Highest surviving damage11 on Rage III/S1 health12; transient11+7=18 fits dial20. Tactical spend≤8 because cap8 and no refresh/income multiplication. Score8 accommodates transient losses at score4; turn15 fits round cap.

Keep each Fighter's three markers beside it and move with switches. Clear when leaving play; never attach to cards entering hidden zones/discard. Nodes/references beside owner, not Fighters. No hidden copy markers. Resolving Actions face up beside discard; Guard visible to attack completion. Progress/damage/stages public. Own-turn15 for both with second player's End triggers round15; no extra round counter.

## 11. First physical-playtest procedure — planned, not performed
1. Two pilots inventory exact starters/pools/components; record rulebook revision. Set state zero; no mixing revisions. Paper log/clock are observation aids, not required game components.
2. Read phases/reset/checkpoints aloud, audit setup:2 resources/2 Fighters/hand5/deck31. Teach Supply, cap8, no discard reshuffle, optional teaching setup and first-player restriction.
3. Rehearse open boundary fixtures: Guard→zero Luck damage; lethal Rage; Convert point5; empty X1; Death/DX sharing cap; finite DeathIII; already-held Repair upgrade; Repair+ not LS; caster-timed Disrupt expiry; M before/after evolution; second acquisition into empty draw pile with discard untouched. These are future checks, not passing results. Restore/shuffle before matches.
4. Plan three paired sets (six games), swap first player per pair, swap deck pilots in pair2. Pair1 timing, pair2 tactics-vs-node costs, pair3 free adaptation; no rules change/fixed draws. Report actual smaller sample if incomplete.
5. Each own turn log score/resource size+ready, Supply discarded identity, active/stage/damage/progress, Hope spend, evolution/trigger, node/cost/turn, acquisition destinations/shuffle, Actions/Reaction, terminal hand/deck/discard counts. Log time/pauses/errors/missed triggers and private information exposed by corrections. Do not reveal hands for logging during normal matches; use after-game/open-fixture consent.
6. At pivots ask opposing public plan, foregone upgrade/attack, free slots, Disrupt paid/waited, Pursuit threat and behind-player alternative. For M log eligibility/purchase/healing/score/foregone node. Distinguish opportunity from purchase.
7. Stop disputes, record exact state and conflicting clauses. A joint temporary ruling makes game HOUSE RULING / NON-CANONICAL; do not claim printed rules resolved it. Do not aggregate changed rules with unmodified paired games. Shortage, unrepresentable state or essential ambiguity requires repair/replay before clean usability claim.
8. Summarize sample/revision, errors, round-cap endings, stage timing by class, lock-ins, shuffled-card draw/use turns and draw-out from economy. Six games reveal handling, not fair win rates. Prioritize ambiguities/repeated no-choice turns before tuning; change one explicit revision and rerun seats. Pilot agreement is not independent QA or CEO approval.

## 12. Evidence, review/fix record and limitations
Research facts belong to growth in REVIEWS r3–r4, not verified anew by this consolidation:
- Tapestry publisher diary https://stonemaiergames.com/games/tapestry/design-diary-tapestry/ supports shared linear tracks/individual nonblocking progress. Our branching/class gates/four slots/evolution are local untested proposals, not that game's rules. Duplicate boards avoid ownership confusion/obscured text.
- Star Realms guide https://www.starrealms.com/learn-to-play supports discard acquisition WITH later reshuffle. Our former discard second copy lacked that engine; QA-01 changed it explicitly to hand+shuffled-deck, not copying external rules or recycling discard. Personal fixed pools differ from contested market.
- Clank! Legacy FAQ https://www.direwolfdigital.com/clank-legacy-acquisitions-incorporated/faq/ supports temporary copy marking/permanent campaign changes, not reusable hidden-deck upgrades. We chose all-copy references over researcher's suggested per-copy replacements to avoid hidden searches/marked sleeves. Handling effectiveness untested.
- Research access failures remain documented: Dominion403, oversized Mystic Vale PDFs, earlier blocked Pokémon rules. No missing contents inferred, originality/legal assurance or comprehensive comparative survey claimed.

QA task2548319576f9449aaf1521c1512379a7 reviewed actual r7 in REVIEWS r5. Designer's saved r8 corrected QA-01 acquisition, QA-03 reset/partial resolution, QA-04 name12/optional stock and QA-05 disclosed DX-required DeathIII. Examples taskfeee4204fafa40e4a78be42304b2c9ea supplied §13. QA recheckd1b3c635840e46d39ab71aa91ebf5c0b reviewed actual r8+examplesr4 in REVIEWS r7: QA-01–05 closed, QA-07 max7 checked non-defect. QA corrected its own initial seating inversion transparently: A goes first in linked13.2–13.3, separate13.4 has Luck/Death owner first. COO incorporates this and narrows stock wording here. Recheck is evidence, not approval or measured balance.

QA-06 remains empirical: HopeIII efficiency/leader tempo, S1/RS/Repair+ stall, Luck denied by Guard, Cycle+ losing formerly paid Hope spend, M win-more, mandatory DX investment, tax usefulness and four-slot lock-in. No infinite refund/refresh/token-sacrifice/repeated acquisition loop found in desk audit; not an exhaustive proof. Leaders also access counters; no guaranteed comeback. 67 pieces, especially24 fighter-state pieces/22 use markers and dense references, may burden handling. Physical playtesting is the next primary step, not speculative systemic expansion.

### Actual task manifest
| Role/work | Task ID | Actual outcome |
|---|---|---|
| Growth research |3cb0de43e9404bbb9d8e7b2784c0abc0|Completed; REVIEWS r4|
| Strategy initial rules |e7777cd07919471dbc1982762691b3dd|Failed provider connection/timeout after saved r4/r5|
| Strategy catalog/kit continuation |0ef1bd26140145ec936438ef485c21ff|Completed r6/r7|
| QA critique |2548319576f9449aaf1521c1512379a7|Completed; REVIEWS r5|
| Strategy fixes |e5dde19c0049468ebeaab8f843e9dc4d|Failed provider connection/timeout after saved r8|
| Strategy examples continuation |feee4204fafa40e4a78be42304b2c9ea|Completed; examples r4, IDEAS r5, OPEN r7|
| QA recheck |d1b3c635840e46d39ab71aa91ebf5c0b|Completed; REVIEWS r7|
| Operations consolidation |40db41bd54c44f03bb86edc454d1a27e|Task completed with reports, but explicitly did NOT consolidate shared documents|

Failed tasks stay failed, not approvals or successful prerequisites. COO read actual surviving saves and performs integration here. Historical v0.3 failures remain in OPEN_QUESTIONS/revisions. No model/provider-limit changes, engineering/finance work, purchases, host execution or protected-document writes occurred. All numerical fixtures below are constructed desk examples, NOT physical playtests or simulations.

## 13. Worked turns and finite evolution route
Strategy-authored examples integrated from GAME_DESIGN_EXAMPLES r4, with QA seating clarification. Chosen draws, not guaranteed outcomes. Counts exclude unacquired pools/references; removed0 unless stated. I/II/III=stage, d=damage, p=progress; unstated d/p0. Names refer to catalog Fighters. Scores are points; all before round15.

### 13.1 Behind-player upgrade and defensive pivot — complete turn
Independent fixture A own turn6. A Starter A: resources7 exhausted; Fighters3 [active Rage II d6/p0; reserve Hope II d3/p0; reserve Rage I]; hand5 [Repair,Cycle,Guard,Reposition,Resource]; draw14; discard11 including three lost Fighters. Total7+3+5+14+11=40. Nodes S1; score A0:B3; S1 healths10/9/8. B: resources6 exhausted; Fighters3 [active Luck II d1/p1, reserve Death I, reserve Luck I]; hand4 [Resource,Convert,Reposition,Cycle]; draw16; discard11=40. B A1/LA telegraph offense, no Guard held; pools four each.
Start A advances6, resets own uses/tactical spend and both Death/X1, refreshes7. Draw Resource→hand6/deck13.
Main buy S2 for3 (preexisting S1, second node), ready7→4. All four Repair copies now Repair+, reference adds no card. Play held Repair for1, ready4→3: heal reserve Hope d3→0, exchange with Rage, move markers; no voluntary-switch/LS. Repair to discard: hand5 [Cycle,Guard,Reposition,Resource,Resource], discard12. Tactical spend1 (not node3). Resource allowance/evolution unused.
Combat Hope II pays2, ready3→1; B passes Reaction. Damage3 makes Luck d1→4<7. Tactical spend3 awards Hope p0→1 at checkpoint, too late for Main evolution. Scores unchanged.
End no defeat. A resources7 (1ready), Fighters3 [active Hope II d0/p1; reserve Rage II d6/p0; Rage I], named hand5, deck13, discard12;7+3+5+13+12=40, nodes S1/S2. B counts unchanged, Luck d4/p1. Score0:3. A preserves Guard resource/two slots, choosing survival rather than another route. Legal recovery attempt, not proven comeback.

### 13.2 Acquisition, shuffle and immediate use — complete turn
New linked fixture; A IS FIRST PLAYER for13.2–13.3. Round8 A8 then B8; round9 A9 then B9. Before B8: resources6 exhausted; Fighters3 [active Luck II d1/p2, reserve Death II d3/p0, reserve Luck I]; hand4 [Resource,Repair,Cycle,Reposition]; deck15; discard12 incl two lost Fighters=40. Nodes E1/X1; score A2:B0. A resources5 exhausted; Fighters3 [active Rage I d5/p1, reserve Hope II d1/p0, reserve Rage II]; hand4 [Resource,Resource,Rage Fighter,Hope Fighter]; deck16; discard12=40. A owns A1, Stage II Rage can qualify RA. Pools four each, no tax.
Start B advances8/resets/refresh6. Draw Guard→hand5/deck14.
Main E2 for3 (E1 preexists, third slot), ready6→3. Reveal Disrupt2, one hand/one shuffled into remaining deck: hand6/deck15/discard12, ownership42; pool Pursuit2. Discard untouched. Choose constructed shuffle outcome with second Disrupt top; NOT guaranteed draw or permission to stack real deck. Play hand Disrupt1, ready3→2, hand5 [Resource,Repair,Cycle,Reposition,Guard], discard13. A next unlock+2 until B's next Start. Tactical spend1; no Hope. No resource play/evolution/E1.
Combat Luck II pays2, ready2→0. A passes. Damage3 makes Rage d5→8≥7: discard before progress, B score0→1. Luck p2→3; B Death gets none from enemy loss. A no Death/X1, freely promotes Hope II, no spillover, two Fighters remain.
End B6resources+3Fighters+hand5+deck15+discard13=42, Luck p3; A5+2+4+16+13=40, active Hope II d1/p0, reserve Rage II. Score A2:B1, no defeat.

### 13.3 Later shuffled-copy draw/use, mixed M and evolution — complete turn plus bridge
Bridge A9: reset/refresh5, draw Resource→hand5/deck15. Main pass, no resource play/unlock. RA would cost3+tax2=5, leaving no attack2. Instead Hope attacks for2, ready3; B passes; Luck d1→4<7. Tactical spend2, no Hope award. End A resources5 (3ready), Fighters2, hand5 [Resource,Resource,Resource,Rage Fighter,Hope Fighter], deck15, discard13=40. B counts42, Luck d4/p3. Score2:1. Tax can be waited out, not guaranteed denial.
Opening B9: resources6 exhausted; Fighters3 [active Luck II d4/p3, reserve Death II d3/p0, reserve Luck I]; hand5 [Resource,Repair,Cycle,Reposition,Guard]; deck15, discard13, E1/X1/E2, pool Pursuit2. A at bridge End.
Start B advances9, resets/refresh6, expires own first Disrupt at B Start NOT A's. Draw second acquired Disrupt→hand6/deck14.
Main play Resource→hand5/resources7 ready. Buy M3→ready4: E1/X1 two preexisting roots, declared Luck/Death both Stage II, turn≥5. Fourth node, first class/mixed. Evolve Luck1→ready3: II→III, p3→0, d4 retained, health9. Because M purchased BEFORE evolution, heal OTHER-class Death d3→1. No retroactive/self-heal. Play drawn Disrupt1→ready2, hand4 [Repair,Cycle,Reposition,Guard], discard14; tax renewed. Tactical spend1, excluding node/evolution.
Combat Luck III pays2→ready0, damage5; A no Guard passes. Hope d1→6<8; no progress for defending Hope or III Luck, no Death award.
End B resources7 exhausted+Fighters3+hand4+deck14+discard14=42. Active Luck III d4/p0; reserves Death II d1/p0, Luck I. A counts40, Hope d6; scores2:1, no defeat. Both Disrupt now discarded, no recycling. M used last slot/3 resources rather than other counter; evolving before M would lose heal.

### 13.4 Finite DX→Death III boundary fixture
Independent, not complete turn; Luck/Death owner FIRST here. Begin own7 with X1, at least3 Resources, surviving reserve Death I p2, two OTHER friendly Fighters lost on separate earlier turns (opponent score2), their cards in discard. Active Luck II d4, another reserve Luck I. Ensure mandatory draws through own10. No other losses until stated; intervening attacks may pass/X1 decline.
Own7 Main evolve Death1→II p0. Own8 buy DX3 (X1/declared Death/II in play, second node); remove discarded Fighter#1→Death p1. Own9 remove Fighter#2→p2. Each DX uses that turn's shared Death allowance, no points/loss/X1, no reused fodder. Opponent9 Start resets allowance, attack3 kills active Luck II d4→7; opposing score2→3, surviving Death p2→3. Promote Luck I; Death alive. Own10 Main evolve reserve Death1→III p0, retain damage. Final route opponent score3, two Fighters removed, newly lost Luck in discard, III Death plus active Luck I. No fifth loss/free evolution. Without DX fifth required loss ends match before III.
