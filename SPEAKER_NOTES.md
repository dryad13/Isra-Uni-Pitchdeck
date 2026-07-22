# OMR Console — Speaker Notes

**Audience:** Mixed (leadership · exam ops · light IT · faculty/council for add-on)  
**Length:** ~22–28 minutes + Q&A  
**Deck:** `index.html` — **N** toggles on-slide notes · **←/→** navigate · **P** print/PDF

---

## Talk tracks (30–45 seconds per slide)

### Act 1 — Why

1. **Title** — Welcome. Clarify **OMR = bubble sheets**, not OCR/text. Product name: OMR Console for Isra University.
2. **Problem** — Vendor OMR (ABBYY) means cost and dependency. We need offline control of exam data on campus.
3. **Solution** — One pipeline: Scan → Auto-read → Verify → Score → Export on a Windows PC beside the Canon.
4. **Outcomes** — Offline, ~100/batch, ≤1.5 s/page target, Secure Score, CSV/Excel, university-owned stack.

### Act 2 — What

5. **Product tour** — Five nav items. Operator lives in **Run exam**.
6. **Who uses it** — Operators (daily), academic admins (keys/roster), QA/IT (calibrator).
7. **Sheet families** — 150Q and 60Q; roll from 6-digit bubbles only.

### Act 3 — Workflow

8. **Step 1** — Programs + sessions with cumulative global Q numbering.
9. **Step 2** — Key via CSV, grid, or sheet; coverage map; block scan until complete.
10. **Step 3** — Canon → `C:\OMR_Dropzone\` auto-ingest; live progress.
11. **Results** — Only blanks / multi / ambiguous rolls need humans.
12. **Verification** — Crop + override; Sheet Q ↔ Global Q.
13. **Audit** — Per-question read vs key for trust and disputes.
14. **Reports** — Operational Secure Score / % export — *not* the analytics add-on.
15. **Roster** — Upload rolls; unknowns go to review.
16. **Tools** — Calibrator + Accuracy Lab (QA/IT only — keep brief).

### Act 4 — Trust

17. **Pipeline** — Align → Roll → Bubbles → Flag. No code deep-dive.
18. **Security** — `127.0.0.1:8080`, SQLite on disk, no cloud telemetry.
19. **Deploy** — Windows + Canon DR-M140 + backup story.
20. **Quality** — Anomaly crops, queue, Accuracy Lab.

### Act 5 — Add-on (optional)

**Framing line:** “Core product gets you scored results. This add-on turns those results into academic insight.”

21. **Opener** — Badge ADD-ON. Faculty + Academic Council. Does **not** block go-live.
22. **Item analysis** — % correct, blank/multi, distractors; flag weak items (e.g. Q34).
23. **Trends** — Section/semester Secure Score tracking.
24. **Council exports** — PDF/Excel packs for review meetings.

### Act 6 — Close

25. **Live demo agenda** — Core only (see script below).
26. **Roadmap** — Core · QA polish · Analytics as phased add-on.
27. **Ask** — Go-live · training · Canon readiness · *optional* analytics interest.

Appendix slides (Secure Score, ABBYY matrix, analytics glossary) — use only in Q&A.

---

## 5-minute live demo script (core only)

1. Launch OMR Console (`START.vbs` from demo pack or `OMR.exe`).
2. **Run exam** → select (or create) program + session → show global Q range.
3. **Answer key** → show coverage map (or load a small CSV).
4. Drop 2–3 sample scans into `C:\OMR_Dropzone\` *or* use Upload.
5. Watch progress on Step 3.
6. **Results** → open one flagged sheet → confirm an override.
7. **Reports** → show Secure Score table → mention CSV/Excel export.
8. Stop. Do **not** demo analytics (mockups only).

---

## 2-minute add-on pitch script

> After results are in the system, faculty still ask: which questions failed the cohort, and how are sections trending across the semester?
>
> The **Result Analytics Dashboard** is an **optional add-on**. It does not replace Reports. It adds:
> 1. Per-question item analysis  
> 2. Section / semester trend tracking  
> 3. Exportable briefs for faculty and Academic Council  
>
> We can pilot it **after** core go-live. Today we’re only asking whether there’s interest — not blocking exam processing.

---

## Anticipated Q&A

| Question | Answer |
|----------|--------|
| Is this OCR? | No — **OMR** reads filled bubbles on Isra answer sheets. |
| Does it need internet? | No after install. Localhost only. |
| Accuracy? | Validated with Accuracy Lab / fixtures; target ≥90% auto-read before overrides; humans clear exceptions. |
| vs ABBYY? | Same job (scan → score → export) with university-owned offline stack and Isra templates. |
| Multi-campus? | Designed per workstation; each site runs its own local instance. |
| Backup? | Nightly `omr.db` backup scripts documented in deployment docs. |
| When does analytics ship? | Phased **add-on** after core go-live; mockups shown today are concept previews. |
| Who gets analytics access? | Faculty / Academic Council — not the daily scan operator. |
| Secure Score vs %? | Secure Score excludes blank/multi from the denominator so blanks aren’t punished as wrong. |

---

## Presenter checklist

- [ ] Open `index.html` in Edge, F11 fullscreen  
- [ ] Demo PC powered; Canon profile pointed at dropzone (if live demo)  
- [ ] Sample sheets / demo data ready  
- [ ] Print PDF backup (`P` → Save as PDF) on USB  
- [ ] Know who in the room cares about add-on (faculty/council) vs core (ops/leadership)
