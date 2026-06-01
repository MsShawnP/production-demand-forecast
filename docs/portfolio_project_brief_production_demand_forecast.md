# Portfolio Project Brief: Production Demand Forecast

**Working title:** *"You'll Run Out in Week 9. The Time to Fix It Was Week 3."*

**Repo (recommended):** `production-demand-forecast`

**Status:** Brainstorm / Brief stage
**Tier:** Curated backlog #4 (high-value, all-tier — the prevention half of the short-ship workstream)
**Priority:** Build after SKU Rationalization and Competitive Shelf Intelligence. Pairs directly with The 150 Cases (#6) — that piece quantifies the cost of short-ships; this one prevents them.

---

### 1. The Pain

Specialty food brands at $10M–$30M almost never own their production. They use co-packers — contract manufacturers with finite capacity, long lead times, minimum run sizes, and changeover constraints. The brand has variable, growing, seasonal demand. The co-packer has a fixed schedule booked weeks out.

The gap between those two realities is where short-ships are born.

The brand plans production reactively: inventory gets low, someone notices, a production run gets ordered. But the co-packer's lead time is 8–12 weeks. By the time inventory is visibly low, the brand is already going to run out — the production decision deadline passed weeks ago and nobody was looking. So the product goes out of stock at the retailer.

And then the doom loop starts.

**The short-ship doom loop:**
1. The product goes out of stock at the retailer (short-ship).
2. Empty shelves suppress velocity — consumers buy a competitor, the brand's units-per-store-per-week craters.
3. That suppressed velocity corrupts the demand forecast — the POS data shows low sales, but it's low because the product wasn't *available*, not because demand was low.
4. The brand forecasts off the corrupted (low) velocity and under-produces.
5. Under-production guarantees the next short-ship.
6. Return to step 1, now worse.

The loop is self-reinforcing and most brands never see the mechanism — they just experience "we keep running out and our forecasts keep being wrong." The forecast is wrong *because* they keep running out. The stockouts are poisoning the very data the forecast is built on.

**Who feels it:**
- **$3M–$10M:** The founder does production planning in their head or a single spreadsheet. They've already been burned by a stockout — lost a Whole Foods reorder, got a nasty note from a buyer. There's no forward view; there's memory of the last disaster.
- **$10M–$15M:** The ops lead juggles co-packer schedules reactively and lives in firefighting mode. Every week is "what are we about to run out of?" There's no rolling forecast, no S&OP process, no view past the next production run.
- **$15M–$20M:** The COO or VP Ops needs a real sales-and-operations planning process and doesn't have one. Production is still reactive. The board is asking why fill rates are inconsistent and the honest answer is "we can't see far enough ahead."

**How it compounds:** Each short-ship makes the next forecast worse (the doom loop). Worse forecasts cause more short-ships. Meanwhile growth makes it harder — a brand adding retailers and SKUs is adding demand variability faster than its reactive planning can absorb. The brand that's growing fastest is often the one short-shipping worst, because growth outruns the spreadsheet.

#### The Status Quo

A spreadsheet that shows current inventory and maybe a reorder point. Production gets ordered when inventory hits the reorder point — but the reorder point doesn't account for the co-packer's lead time, current bookings, or a demand forecast that's been corrupted by past stockouts. There's no forward view that says "given projected demand and what's already scheduled, here's the date you run out and here's the deadline to prevent it."

---

### 2. Why This Piece

**It breaks the doom loop — the practice's central strategic theme.** The short-ship doom loop runs through the whole portfolio. The 150 Cases quantifies what short-ships cost. This piece is the prevention: forecast true demand, compare it to capacity, surface the gap before it becomes a stockout. It's the piece that turns "we keep running out" into "we saw it coming and acted."

**The "true demand" correction is the analytical differentiator.** A naive forecast built on observed velocity perpetuates the doom loop — it forecasts low because past stockouts suppressed the data. This piece corrects observed velocity for out-of-stock periods to estimate *true* demand, then forecasts off that. That single correction is what separates a forecast that breaks the loop from one that feeds it.

**It connects demand to capacity — the gap nobody models.** Most demand forecasts stop at "here's projected demand." This piece goes one step further: it lays projected demand against co-packer capacity, lead times, and minimum run sizes, and computes the actual stockout date and the production decision deadline. The output isn't a forecast — it's a decision: "book a run by week 3 or run out in week 9."

**All-tier.** Every co-packer-dependent brand faces this. The $5M brand with one co-packer and 15 SKUs and the $20M brand with three co-packers and 90 SKUs have the same structural problem at different scale.

**Compounds with the portfolio:**
- **The 150 Cases (#6):** Quantifies short-ship cost. This prevents the short-ships it quantifies. The two are the cost-and-prevention pair of the short-ship workstream.
- **Velocity Decision Tool (#1):** Module 2 (Replenishment → Production) is the seed; this is the full rolling-forecast expansion.
- **Co-Packer / Production Capacity Model (#22):** Capacity is an input here; the deeper capacity-stress modeling is its own piece.
- **Competitive Shelf Intelligence (#7):** OOS detection from that piece feeds the "true demand" correction here — knowing exactly when and where the product was out of stock makes the velocity correction precise.

---

### 3. The Analysis — What It Reveals

The heart of the piece. Five moves:

**Move 1 — Correct observed velocity for stockouts (true demand). The circuit breaker.**
Observed velocity during an OOS period understates true demand — you can't sell what isn't on the shelf. The analysis identifies OOS periods (anomalous multi-day blocks of near-zero POS where historical velocity was positive, or flagged directly from inventory data and competitive shelf monitoring) and substitutes the corrupted zero periods with an estimated true baseline — a rolling median of the surrounding healthy weeks, adjusted for trailing seasonal trend.

```
Raw POS:      120 → 115 →  0  →  0  → 130    (corrupted baseline)
True Demand:  120 → 115 → 122 → 125 → 130    (reconstructed)
```

This is the move that breaks the doom-loop circuit. And it's deliberately simple by design: running a complex forecasting model over a zero-sales stockout window just teaches the model to predict zero. The value is in recognizing the corruption and reconstructing a clean baseline, not in algorithmic sophistication.

**Move 2 — Build the rolling forecast.**
An 8–12 week forward demand forecast by SKU, built on true demand, incorporating seasonality, trend, known promotions, and planned retailer expansions. Rolling — it updates as new data arrives. Not a static annual budget; a live forward view.

**Move 3 — Layer in co-packer capacity and constraints.**
Current production bookings, lead times by SKU, minimum run sizes, changeover requirements, and any shared-line constraints (SKUs that compete for the same production line). This is the supply side that demand forecasts usually ignore.

**Move 4 — Compute the gap and the decision deadline.**
For each SKU: projected demand vs. (current inventory + scheduled production). Where demand exceeds supply, compute the projected stockout date. Then, working back through the lead time, compute the *production decision deadline* — the last date a run can be ordered to prevent the stockout. The killer output: "SKU X stocks out week 9; order a run by week 3 to prevent it."

**The shared-line conflict.** In CPG you rarely just run out of a SKU — you run out of *line time*. If SKU A and SKU B share a production line and both have a decision deadline in week 3, the co-packer physically cannot run both concurrently. The system must surface this as a critical conflict, not two independent deadlines. Detecting that two deadlines collide on the same line — and flagging that one of them has to move earlier — is where the model crosses from "demand forecast" into "real production planning."

**Move 5 — Scenario modeling.**
What if the promo lifts demand 30%? What if the new retailer launches on time and adds 200 doors? What if the co-packer's lead time slips two weeks? The brand sees how the stockout dates and decision deadlines move under different scenarios, so it can plan against the realistic case instead of the optimistic one.

#### The Output

- **The S&OP live-action view:** a forward-looking per-SKU view — projected true demand, current inventory, scheduled production, projected stockout date, and production decision deadline. SKUs with a decision deadline less than 14 days away flag bright red, turning the tool from passive reporting into an active fire-prevention warning system. Shared-line conflicts flag as critical. Plus the scenario layer for promos and expansions.
- **The Master Production Schedule (MPS) export:** a cleanly formatted workbook the VP of Ops attaches directly to co-packer purchase orders in the weekly alignment meeting. The forecast becomes the operational document, not just an analysis.

#### The Margin Math

For a $25M brand:

| Value Driver | Mechanism | Annual Recovery |
|--------------|-----------|:---------------:|
| Short-ship revenue recovery | Eliminates short-ship deductions, OTIF fines, and lost-sale revenue | $50K–$300K |
| Working capital optimization | Forward visibility replaces panic-buying safety stock | $40K–$120K |
| Expedite fee elimination | Normal-schedule production instead of 15–30% rush premiums | $20K–$80K |
| **Total operational value** | **Protects core velocity, stabilizes supply chain cost** | **$110K–$500K** |

**The pendulum, both ends.** Reactive planning doesn't just cause stockouts — it causes overcorrection. After a brutal out-of-stock, a founder panic-orders an enormous run of the missing SKU, tying up working capital in safety stock that sits in the 3PL creeping toward expiration. This piece solves *both* ends of the swing: it prevents the stockout AND prevents the overcorrection, because forward visibility replaces fear-driven ordering.

**The doom-loop tax (the uncounted one).** The largest value isn't in the table because brands never attribute it to the real cause: every prevented stockout protects velocity, which protects the forecast, which prevents the next stockout. Breaking the loop is worth more than any single prevented short-ship — it's the difference between velocity that compounds up and velocity that erodes down.

#### Before / After

- **Before:** Ops lead checks inventory weekly. Notices SKU X is getting low. Orders a production run. Co-packer says "earliest slot is 9 weeks out." SKU X runs out in 4 weeks. Short-ships Walmart. Velocity craters. Next forecast (built on the cratered velocity) says "make less of SKU X." The loop tightens.

- **After:** Ops lead opens the rolling forecast Monday. Sees SKU X projected to stock out week 9, with a production decision deadline of week 3 — three weeks from now. Books the run on the normal schedule, no expedite premium. SKU X stays in stock. Velocity holds. The forecast stays clean. The loop is broken.

#### Who Else Sees This?

- **Primary:** COO / VP Ops / ops lead — owns production planning. CEO — owns the growth plan that drives demand.
- **Secondary:** CFO (inventory is working capital; the forecast affects cash), co-packer (a brand that forecasts well is a better partner and gets better treatment), sales (so promotional plans get into the forecast before they blow up capacity).
- **How it gets shared:** Ops lead uses it weekly as the planning tool. CEO sees the scenario layer and understands, for the first time, that the aggressive growth plan requires production capacity the current co-packer can't deliver — a strategic conversation that wasn't possible before.

---

### 4. Technical Notes (kept light)

The piece joins demand-side data (velocity/POS, with OOS correction), the brand's inventory position, and supply-side data (co-packer bookings, lead times, run sizes). The analytical substance is in the true-demand correction and the demand-vs-capacity gap logic, not in the tooling. It runs on the Cinderhaven Data Platform alongside the velocity and order data, delivered as a forward-looking interactive view plus an exportable planning workbook. Forecasting method can stay pragmatic — a defensible time-series approach with seasonality, not an exotic model; the value is in the OOS correction and the capacity overlay, not in forecast-method sophistication. Specific stack choices follow established portfolio patterns and aren't worth over-specifying at brief stage.

---

### 5. Skills Demonstrated

- **The OOS-correction insight** — recognizing that observed velocity is corrupted by stockouts and correcting for it. This is the analytical move that proves the practitioner understands the doom loop mechanically, not just rhetorically.
- **Demand-supply integration** — connecting a demand forecast to real production constraints (lead time, run size, capacity). Most forecasts stop at demand; this closes the loop to supply.
- **S&OP process design** — turning a forecast into a decision framework (stockout date + decision deadline). The practice's core positioning: decision infrastructure, not reports.
- **Scenario modeling** — promos, expansions, lead-time slippage. Showing the CEO how the growth plan collides with capacity.

---

### 6. Foot-in-the-Door Offering

- **Offering name:** Demand–Capacity Planning Setup
- **Format:** Fixed-fee 3–4 week engagement, with an optional ongoing S&OP support retainer
- **Price range:** $20K–$30K setup; retainer $2K–$5K/month if they want ongoing forecast maintenance
- **What the client gets:**
  1. True-demand forecast by SKU (OOS-corrected)
  2. Rolling 8–12 week forward view
  3. Co-packer capacity integration — bookings, lead times, run sizes
  4. Stockout date + production decision deadline per SKU
  5. Scenario layer for promos and retailer expansions
  6. The planning workbook/view the ops team uses going forward
- **Why this piece sells it:** The "you'll run out in week 9, the deadline was week 3" output is visceral. Any ops lead who's been burned by a stockout immediately wants this forward view on their real SKUs. And the retainer is genuinely justified — the forecast needs maintaining as demand and bookings change weekly.

#### Client Lift

- **What the client provides:** Velocity/POS history, current inventory by SKU, and co-packer details (current bookings, lead times, minimum run sizes). The co-packer data is often the gap — it lives in emails and the ops lead's head, not a system. Part of the engagement's value is structuring it for the first time.

#### The DIY Defense

- **The OOS correction is non-obvious and rarely done.** Most brands forecast off observed velocity and never realize the stockouts are poisoning the data. Recognizing and correcting for it requires understanding the doom loop mechanically — which is exactly the insight a spreadsheet-bound ops lead lacks.
- **Connecting demand to capacity requires both datasets in one place.** Demand lives in POS/velocity; capacity lives with the co-packer. Joining them into a single forward view — with lead times working backward to decision deadlines — is the work nobody internally has done.
- **The forward view has to be maintained.** A static forecast is wrong by next week. Keeping it rolling — updating as bookings and velocity change — is ongoing work that justifies the retainer and that internal teams rarely sustain.

---

### 7. Competitor / Existing Content Scan

- **What exists:**
  - **Demand planning / S&OP software** (Netstock, Inventory Planner, Cogsy, Streamline) — real tools, but most are built for general inventory planning and don't natively handle the co-packer-constraint model or the OOS-correction problem. The good ones are $1K–$5K/month and require setup most small brands never finish.
  - **ERP demand modules** (NetSuite, etc.) — exist, rarely configured well, don't correct for OOS-suppressed velocity.
  - **Generic forecasting content** — "how to forecast demand" articles. Don't address the doom loop or the capacity constraint.
  - **3PL / co-packer dashboards** — show inventory, not a corrected forward forecast against capacity.
- **What's missing:** A forecast built for the co-packer-dependent specialty food brand that (a) corrects for stockout-suppressed velocity and (b) lays demand against production capacity to produce decision deadlines. Nobody frames it around breaking the doom loop.
- **Your angle:** The OOS correction + the demand-vs-capacity decision deadline + the doom-loop framing, for the $5M–$30M brand drowning in reactive production planning.

---

### 8. Cinderhaven Integration

Cinderhaven's top SKU (an Artisan Sauce) went out of stock at Walmart for 11 days in February — the same event surfaced in the Competitive Shelf Intelligence piece. The analysis shows the doom loop in action:

- **Naive forecast** (built on observed velocity): projects demand of ~4.2 units/store/week and says "current production is adequate."
- **True-demand forecast** (OOS-corrected): the February stockout suppressed observed velocity; corrected true demand is ~5.0 units/store/week — 18% higher.
- **Capacity overlay:** Cinderhaven's co-packer is booked solid through April with a 9-week lead time.
- **The gap:** at true demand, the SKU stocks out again in mid-May. The production decision deadline to prevent it is early March — weeks away.
- **Without the forecast:** Cinderhaven runs the naive number, under-produces, and short-ships the same SKU again in May — the doom loop completing its second cycle.
- **With the forecast:** the May stockout is visible in February, the run gets booked on the normal schedule, the loop breaks.

Headline: **the brand's own stockout was about to cause its next stockout — and the naive forecast couldn't see it because the stockout had poisoned the data.**

Runs on the existing Cinderhaven Data Platform — velocity, orders, inventory marts, plus a co-packer capacity layer (synthetic). Consistent with the short-ship figures in The 150 Cases and the OOS event in Competitive Shelf Intelligence.

---

### 9. Tactical Notes

- **The doom loop is the narrative spine.** Don't present this as "a demand forecasting tool" — present it as "the reason your forecasts are wrong is that your stockouts are poisoning them, and here's how to break the cycle." The mechanism is the insight; the forecast is the fix.
- **Lead with the decision deadline, not the forecast.** "Projected demand for SKU X is 5,000 units" is a forecast. "You'll run out in week 9 and the deadline to prevent it is week 3" is a decision. The decision deadline is what makes an ops lead act.
- **The co-packer data is the hard input.** Lead times, bookings, and minimum run sizes usually aren't in any system — they're in the ops lead's head and the co-packer's emails. Acknowledge this and treat structuring it as part of the value.
- **Keep the forecasting method pragmatic.** The temptation is to reach for sophisticated forecasting models. Resist it. A defensible seasonal time-series forecast is plenty — the differentiated value is the OOS correction and the capacity overlay, not the forecast algorithm. A fancy model on poisoned data is still poisoned.
- **The scenario layer is where the CEO conversation happens.** Showing that the aggressive growth plan requires capacity the co-packer can't deliver turns this from an ops tool into a strategic one. "Your Q4 promo plus the new Target launch breaks your co-packer in week 6" is a board-level finding.

#### The Credibility Marker

Knowing that observed POS velocity during a stockout understates true demand — and knowing how to correct for it using pre/post-stockout velocity and seasonal baseline rather than just interpolating. The deeper marker: understanding that this correction is what *breaks* the doom loop, because forecasting off uncorrected velocity is the mechanism that *perpetuates* it. Articulating that a brand's stockouts are corrupting the very forecast meant to prevent them — and showing the correction — is the practitioner signal. Generic "demand forecasting is hard" is not.

Secondary markers:
- Understanding co-packer minimum run sizes and how they force overproduction of slow SKUs and underproduction of fast ones
- Knowing that lead time, not inventory level, is the binding constraint — the reorder point is meaningless if it doesn't account for the co-packer's calendar
- Recognizing shared-line constraints (two SKUs that can't be produced simultaneously) as a hidden capacity limit

#### Data Paranoia / Security

Co-packer terms, lead times, and capacity are competitively sensitive (they reveal the brand's supply chain). Velocity and inventory data are sensitive. Cinderhaven's numbers are synthetic; engagement uses NDA; analysis runs on the brand's own data with nothing retained.

---

### 10. Open Questions

- [x] ~~**How sophisticated should the OOS correction be?**~~ Resolved: rolling-median baseline of the 3 weeks pre- and post-stockout, adjusted for seasonal index. Simple, defensible, documented clearly to show competence. (A complex model over a zero-sales window just learns to predict zero.)
- [x] ~~**How much capacity modeling vs. #22?**~~ Resolved: limit to standard operational constraints — lead times, MOQs/minimum run sizes, and shared-line conflicts. Defer deeper throughput/ingredient-matrix optimization to Co-Packer Capacity Model (#22).
- [x] ~~**Forecast horizon.**~~ Resolved: 12-week rolling window — safely covers the maximum 8–12 week lead time needed to trigger a run.
- [ ] **Single co-packer or multi-co-packer?** MVP: single co-packer. v2: multi-co-packer with differing lead times and capabilities.

---

### 11. Build Estimate

- **Effort level:** Medium. The analytical logic (OOS correction, rolling forecast, capacity gap, decision deadlines) is the work. Runs on the existing platform.
- **Time estimate:** ~3 weeks. The OOS-correction logic and the demand-vs-capacity gap calculation are the long poles; the forecast and the views follow established patterns.

#### Out of Scope

- **Deep co-packer capacity optimization.** Routing production across lines/co-packers to optimize cost and throughput is #22's territory. This piece uses capacity as a constraint, not an optimization target.
- **Automated production ordering.** The forecast surfaces the decision and the deadline; it doesn't place the order with the co-packer.
- **Ingredient/raw material planning.** Demand → finished goods is in scope. Finished goods → ingredient requirements (MRP) is a deeper layer, out of scope for the portfolio piece.
- **Exotic forecasting methods.** Pragmatic seasonal time-series only. ML forecasting is not the differentiator and not worth the build.

---

### Relationship to Existing Inventory

| Project | Relationship |
|---------|-------------|
| The 150 Cases You Didn't Ship (#6, built) | **The cost-and-prevention pair.** 150 Cases quantifies what short-ships cost; this prevents them. Same short-ship workstream, opposite ends. |
| Velocity Decision Tool (#1, built) | Module 2 (Replenishment → Production) is the seed; this is the full rolling-forecast expansion. |
| Competitive Shelf Intelligence (#7, briefed) | OOS detection from that piece feeds the true-demand correction here — precise stockout timing makes the velocity correction sharper. |
| Co-Packer / Production Capacity Model (#22, curated backlog) | Capacity is an input here; deep capacity-stress modeling is its own piece. |
| EDI Short-Ship (rolled into short-ship cost project) | Part of the same short-ship workstream this piece anchors the prevention side of. |
| Brainstorm forecasting cluster (#88–90, time-series; #108 new SKU velocity vs forecast) | Absorbed — the rolling forecast and OOS correction are these ideas realized. |
| Brainstorm #147 Production capacity stress testing (26) | Adjacent — informs the capacity overlay; deeper version is #22. |
| Umbrella (#3, built) | Maps to a decision in the ten-decision framework — production/fulfillment readiness. |

---

*Brief complete when open questions are resolved.*
