# queryspend launch plan

- Plan date: 2026-08-11 JST
- Recommended launch anchor: **Tuesday, 2026-08-25 at 00:01 PT (PDT) / 07:01 UTC /
  16:01 JST**
- Primary GitHub Trending category: **Python**; all-language Trending is a stretch goal
- Publication owner: a human maintainer; this repository contains drafts and a runbook only
- Current status: **locally launch-prepared, externally blocked** until the go/no-go checklist is
  complete

queryspend shows the known recurring BigQuery cost delta of a dbt pull request before merge while
keeping unsupported or unsafe estimates explicitly unknown. It is an Apache-2.0 alpha CLI and
GitHub Action, not a hosted service.

The launch must not describe the synthetic demo or synthetic validation corpus as live BigQuery
accuracy. Real BigQuery ADC, GitHub-hosted `workflow_run`, Google OIDC, and protected-environment
execution remain unverified.

## The decision and why this date

Use **2026-08-25 at 00:01 PT** as the one launch anchor. Product Hunt states that scheduled days
start at 12:01 AM in its Pacific-time day. Tuesday leaves a full weekday for responses, avoids the
Monday backlog and Friday drop-off, and places the separate Show HN submission at 06:30 PT, when
North America is starting work and Europe is still active. The 14-day lead from this plan date is
needed for hosted CI, the immutable release, account/rule checks, human rewriting, and the first
real integration evidence.

August 25 is in Pacific Daylight Time (UTC−7). Product Hunt's help page calls its operating zone
“PST”; verify the scheduler preview rather than manually offsetting it. No time choice guarantees
featuring, rank, votes, stars, or Product of the Day.

| Event | PT | UTC | JST |
|---|---|---|---|
| Product Hunt day begins | Tue Aug 25, 00:01 | Tue Aug 25, 07:01 | Tue Aug 25, 16:01 |
| X launch note | Tue Aug 25, 06:15 | Tue Aug 25, 13:15 | Tue Aug 25, 22:15 |
| Show HN | Tue Aug 25, 06:30 | Tue Aug 25, 13:30 | Tue Aug 25, 22:30 |
| LinkedIn | Tue Aug 25, 07:15 | Tue Aug 25, 14:15 | Tue Aug 25, 23:15 |
| Technical X follow-up | Wed Aug 26, 07:30 | Wed Aug 26, 14:30 | Wed Aug 26, 23:30 |
| r/FinOps, only after rule recheck | Wed Aug 26, 08:30 | Wed Aug 26, 15:30 | Thu Aug 27, 00:30 |

## Launch contract

The goal is to reach people who maintain dbt projects on BigQuery and let them evaluate a useful,
honest tool. A Python Trending appearance and high Product Hunt/Show HN positions are outcomes to
work toward, not claims or entitlements.

Do:

- link directly to `https://github.com/black-leg-nameko/queryspend`;
- lead with the credential-free `uv run queryspend demo` path;
- call the demo and validation data synthetic wherever their numbers appear;
- identify the project as alpha and repeat the unverified ADC/OIDC limitations;
- answer technical questions personally, promptly, and with evidence;
- record every post URL, timestamp, referral, issue, install signal, and learning.

Never:

- ask for, trade, buy, coordinate, or incentivize upvotes, comments, Product Hunt points, or GitHub
  stars;
- use bots, fake identities, engagement pods, mass direct messages, unsolicited mailing lists, or
  repeated cross-posts;
- disguise the maintainer relationship or present generated text as personal experience;
- report synthetic cost figures, evaluator metrics, or local tests as production accuracy;
- repost a weak HN submission or delete it to reset rank.

## Audience and channel jobs

| Audience | Pain | Proof to show | Primary channel | Desired action |
|---|---|---|---|---|
| Analytics engineers | Cost impact appears after merge | 60-second synthetic demo and explicit unknowns | Show HN, GitHub | Run the demo; inspect the model |
| Data platform leads | PR review lacks a recurring-cost policy | Dry-run invariant, lineage rules, JSON schema | HN, LinkedIn | Evaluate in a sandbox |
| FinOps practitioners | Warehouse changes are hard to attribute pre-deploy | Known monthly subtotal plus coverage | r/FinOps, LinkedIn | Compare with their review process |
| dbt/BigQuery maintainers | CI needs a narrow composable primitive | CLI, two-workflow Action, no telemetry | GitHub, X | Open a specific issue or contribute |

The repository README and demo are the source of truth. Product Hunt provides broad discovery,
Show HN provides technical scrutiny, r/FinOps provides the closest practitioner discussion, and
X/LinkedIn provide owned distribution. Do not post identical copy across communities.

### Responsible case for competing for #1

For Product Hunt, going live at the official start of the Pacific day preserves the full discovery
window; a literal under-60-second trial, correctly sized media, and an available human maker reduce
the largest avoidable conversion and response failures. For Show HN, the preferred descriptive
title selects the relevant technical audience, 06:30 PT overlaps US morning and European
afternoon, and a candid first comment can answer the dry-run/uncertainty tradeoff before readers
misread the claim. Concentrating independent owned-channel discovery into the following 48 hours
gives qualified users a coherent path back to the runnable repository.

That is the evidence-based plan for *competing* for the top position on each platform. It does not
control editorial featuring, votes, flags, competing launches, or ranking systems. Authentic trials
and substantive human discussion are the only permitted initial-engagement strategy.

## Product Hunt listing

Create the draft from a complete personal account and schedule it only after the T−48-hour gate.
The direct product URL is the GitHub repository.

### Listing fields

- Name: `queryspend`
- Preferred tagline: `See BigQuery cost changes in dbt pull requests before merge`
- Alternate A: `A pre-merge BigQuery cost gate for dbt`
- Alternate B: `Turn dbt changes into a reviewable BigQuery cost delta`
- Description:

  > queryspend is an Apache-2.0 CLI and GitHub Action that compares two dbt manifests, dry-runs
  > eligible BigQuery SELECTs, and estimates the known recurring monthly cost delta. Unsupported
  > cases stay unknown—not $0. Alpha; live ADC/OIDC validation pending.

- Topics: Developer Tools, Open Source, GitHub, Data, Productivity; choose the closest options the
  current form actually offers and keep only a few
- Pricing: Free
- Status: Available, with the listing and first comment explicitly calling it alpha
- Maker: the actual maintainer's personal account
- Primary URL: `https://github.com/black-leg-nameko/queryspend`
- Promo: none

The preferred tagline wins because it names the affected system, workflow moment, and user-visible
benefit without claiming savings or accuracy. Alternate A is shorter but “gate” may imply complete
production validation. Alternate B communicates the artifact but is less immediate.

### Gallery and listing QA

Product Hunt recommends a 240×240 thumbnail under 3 MB and at least two 1270×760 gallery images.
Before scheduling, prepare and visually inspect these derivatives; do not stretch terminal text:

1. square mark with `queryspend` and “BigQuery cost delta before merge”;
2. terminal demo still with `SIMULATED DEMO` readable;
3. “known / unknown / why” explainer derived from the README support table;
4. optional dry-run/privacy diagram with the alpha integration caveat.

The current reusable assets are `assets/demo.gif` (1200×760, 5.96 seconds), `assets/demo.png`
(1200×760), and `assets/social-preview.png` (1280×640). The GIF and still already include readable
synthetic disclosure. Recheck every derivative at native size and in a mobile preview. Add concise
alt text; never crop the disclosure. A gallery requires two or more images to display.

### Maker's first comment — human-only worksheet

**Do not paste AI-generated or AI-edited comment text.** Product Hunt's current commenting
guidelines prohibit AI-generated comments. The maker must independently write the comment in their
own voice using verified facts only. Before launch, they can answer this worksheet on paper:

1. What concrete code review moment made pre-merge recurring cost visibility worth solving?
2. Why is a dry-run byte estimate alone insufficient without schedule, price, lineage, and unknown
   coverage?
3. What exactly happens in the credential-free demo, and which figures are synthetic?
4. What does queryspend deliberately refuse to estimate?
5. What is still unverified in the alpha—live ADC, OIDC, hosted workflow, and real accuracy?
6. Which one technical question should practitioners answer from experience?

The final human comment should disclose maker status, link no unrelated properties, acknowledge the
alpha limits, and invite a specific technical discussion rather than votes.

### Product Hunt response plan

- From 00:01–06:00 PT, confirm the page, links, media, pricing, and caveat; answer real questions.
- From 06:00–16:00 PT, keep one maker available. Reply with examples or documentation, not generic
  thanks. Escalate security reports to the private route.
- Correct factual misunderstandings once; do not debate votes, rank, featuring, or competitors.
- Log repeated objections as issues only when the reporter consents or no private information is
  copied.

## Show HN

The repository is runnable without signup or credentials, so it meets the core Show HN trial
requirement. The submitter must be someone who personally worked on queryspend and is available for
the conversation.

### Title comparison

These are comparison candidates, not permission to paste generated text. The maker must select or
rewrite a factual title in their own words after re-reading the HN rules.

| Candidate | Strength | Risk | Verdict |
|---|---|---|---|
| `Show HN: queryspend – BigQuery cost deltas for dbt pull requests` | Names product, system, and PR use case | “deltas” assumes domain familiarity | **Preferred** |
| `Show HN: Estimate recurring BigQuery costs before merging dbt changes` | Explains timing and recurrence | Omits product name; “estimate” needs caveats | Alternate |
| `Show HN: A dry-run-only cost gate for dbt on BigQuery` | Surfaces the technical invariant | “gate” can overstate alpha readiness | Do not lead |

The preferred title is descriptive, restrained, and free of superlatives, exclamation marks, and
unsupported numbers. It creates a clear technical question for the right audience. The 06:30 PT
timing overlaps US morning and European afternoon; it is not a ranking guarantee. HN says rank is
roughly points divided by a power of age with additional anti-abuse, flag, weighting, and moderator
factors, so authentic technical interest—not coordination—is the only acceptable strategy.

### First comment — human-only worksheet

HN forbids generated or AI-edited comments. **The maker must write the entire first comment and all
replies independently.** Do not paste this plan into HN. A factual preparation sheet:

- Personal origin: the real review or planning problem that the maker encountered.
- Mechanism: compare base/head dbt manifests; identify affected models; dry-run eligible `SELECT`
  SQL; apply explicit run frequency and on-demand price; preserve unsupported cases as unknown.
- Safety: one BigQuery query call path, `dry_run=True`, no rows, raw SQL absent from reports and
  comments, no telemetry endpoint.
- Honest result: the bundled `+487.50 USD/month` known subtotal is synthetic fixture output, not a
  benchmark or live estimate.
- Alpha limits: no real ADC/OIDC or GitHub-hosted Action validation; capacity pricing and several
  dbt materializations are unsupported.
- Design tradeoff: a known subtotal with coverage instead of pretending unknown means zero.
- Specific discussion prompt: how teams encode execution frequency or review uncertain downstream
  costs today.

Prepare concise, factual answers to likely questions about dry-run pricing, incremental models,
views, scheduling assumptions, compiled SQL privacy, dbt manifest trust, BigQuery IAM, and why the
tool does not compile dbt. If the maintainer cannot personally respond for the first six hours,
postpone rather than delegate generated replies.

### HN failure pre-mortem

| Failure mode | Prevention | Response |
|---|---|---|
| Readers think this predicts their actual bill | Put “known subtotal,” coverage, and alpha caveat above metrics | Correct once and point to support table |
| “Why not just use BigQuery dry run?” | Explain recurrence, price, lineage, policy, and unknowns | Welcome the comparison; avoid defensiveness |
| Demo looks fabricated | Keep `SIMULATED DEMO` visible and reproduction one command | State exactly what the fixture proves |
| OIDC design is challenged | Separate code review from unverified hosted integration | Link security review; do not claim production readiness |
| Post receives little attention | Leave it in place and learn from referral/issue data | Do not delete, repost, solicit, or coordinate |

## Reddit routing and drafts

The following is a point-in-time check of Reddit's official public community metadata on
2026-08-11. Account age, karma, prior promotional history, current flair, and moderator approval
are unknown. The human poster must open each community's visible rules immediately before posting;
if the UI and the recorded source differ, the current UI wins.

| Community | Primary evidence | 2026-08-11 rule/fit result | Launch decision |
|---|---|---|---|
| r/FinOps | Official `about.json` says self-promotion is allowed if declared | Direct practitioner fit; relationship disclosure required | **Eligible Day +1**, after live recheck |
| r/dataengineering | Official `about/rules.json` limits organization-wide self-promotion to once/month, requires relationship disclosure, rejects opaque marketing, reviews all links, and prohibits heavily AI-generated/assisted text | This plan and its drafts are AI-assisted; a launch post would violate the current text rule | **No-go for this launch** |
| r/bigquery | Official `about.json` identifies a BigQuery audience, but current rules could not be retrieved and posting is restricted | Strong fit but permission is unresolved | **No launch-window post; ask mods, then T+7 at earliest** |
| r/DBT | Official `about.json` identifies the community as Drive-By Truckers | Not the data build tool audience | **No-go** |

Do not cross-post the same body to multiple communities. Do not use “looking for feedback” as a
promotional wrapper. Do not contact individual members or moderators repeatedly.

### r/FinOps draft — use only if current rules still allow it

Title:

> I open-sourced a pre-merge BigQuery cost delta check for dbt

Body:

> Disclosure: I maintain queryspend, the open-source project linked below.
>
> We built it around a narrow FinOps question: when a dbt pull request changes BigQuery models,
> what portion of the recurring monthly cost delta can be supported before merge?
>
> queryspend compares base and head dbt manifests, dry-runs eligible SELECT statements, and combines
> the byte estimates with explicit run frequency and on-demand price. It reports a known subtotal
> and coverage; views, unsafe downstream effects, unsupported materializations, or missing
> assumptions stay unknown instead of becoming $0.
>
> The one-command demo is synthetic and credential-free. The project is alpha: the offline core is
> tested, but real BigQuery ADC accuracy and the GitHub-hosted OIDC workflow are not yet validated.
>
> Repository: https://github.com/black-leg-nameko/queryspend
>
> For teams doing pre-deployment cloud-cost review: do you treat uncertain downstream costs as a
> blocker, a warning, or a separate approval step?

The question is domain-specific, not a request for votes or generic engagement. The poster should
replace “We built” with a truthful personal statement and disclose any employer relationship.

### r/bigquery modmail and conditional draft

One short modmail, sent at T−7 or earlier:

> I maintain an Apache-2.0 alpha CLI that compares two dbt manifests and uses BigQuery dry-run
> estimates to show a known recurring cost delta before merge. The demo is synthetic and the live
> integration is explicitly unverified. Would one disclosed project post be permitted here? I will
> follow your preferred flair and format and will not ask for votes.

No reply means no post. If explicitly approved, independently adapt the r/FinOps body for BigQuery
engineers, quote the approval conditions in the internal log, apply the required flair, and wait
until T+7 so the 48-hour launch does not become a Reddit cross-post burst.

## X drafts

Use a maintainer account with an authentic history. One launch post and one technical follow-up are
enough; replies should be human, relevant, and non-repetitive.

Launch post:

> I open-sourced queryspend: a CLI + GitHub Action that shows the known recurring BigQuery cost
> delta of a dbt pull request before merge.
>
> It combines dry-run evidence with explicit frequency and price. Unsafe cases stay unknown—not
> $0.
>
> The demo is synthetic; live ADC/OIDC validation is still pending.
>
> https://github.com/black-leg-nameko/queryspend

Technical follow-up:

> A design choice in queryspend: “unknown” is a first-class result.
>
> A changed view, unsupported materialization, missing frequency, or unsafe downstream effect never
> becomes a fake $0. The report shows a known subtotal plus coverage and reason codes.
>
> Reproducible synthetic demo: uv run queryspend demo
>
> https://github.com/black-leg-nameko/queryspend

Optional pre-launch note at T−7, only if the account already discusses this work:

> I’m preparing an open-source experiment for reviewing recurring BigQuery cost changes in dbt PRs.
> The hardest design choice has been preserving uncertainty instead of presenting partial evidence
> as a complete estimate. I’ll share the runnable alpha after the hosted checks are green.

Do not tag unrelated influencers, auto-reply, recycle the post into threads, or ask for stars.

## LinkedIn draft

> BigQuery dry runs answer “how many bytes would this statement process?” They do not answer a pull
> request's recurring monthly cost change by themselves.
>
> I’ve open-sourced queryspend, an Apache-2.0 CLI and GitHub Action for dbt on BigQuery. It compares
> base and head manifests, dry-runs eligible SELECTs, and applies explicit schedule and on-demand
> pricing assumptions. The output is deliberately a known subtotal with coverage: unsupported or
> unsafe estimates remain unknown rather than silently becoming $0.
>
> You can run the synthetic demo without credentials in under a minute:
>
> `uv run queryspend demo`
>
> This is an alpha. The offline core and security invariants are tested; real BigQuery ADC accuracy,
> GitHub-hosted workflow execution, and OIDC are still pending validation.
>
> Repository: https://github.com/black-leg-nameko/queryspend
>
> I’m especially interested in how data platform and FinOps teams represent uncertain downstream
> cost during code review.

The publisher must replace the personal sentence with their truthful experience. Do not tag people
who did not contribute or request the mention.

## GitHub and README conversion path

Every channel links to the repository, not a tracking redirect. The first screen must preserve this
sequence:

1. one-line pitch: “See the recurring BigQuery cost delta of a dbt pull request before merge.”
2. `assets/demo.gif`, with synthetic disclosure in alt text and inside the terminal;
3. `assets/demo.png` as a still alternative;
4. the clone plus `uv run queryspend demo` quickstart;
5. the alpha caveat before live setup.

Before publication, set the description and ten topics exactly as recorded in
`launch/metadata.md`, upload `assets/social-preview.png`, enable Issues/Discussions/private
vulnerability reporting, and replace the configured badge with the real hosted `main` status only
after it is green. Publish `v0.1.0` from a reviewed immutable commit and use that commit SHA in the
Action example. Do not use a mutable tag as a security boundary.

Track conversion with native referrers where available. Do not add telemetry to the CLI for the
launch. Useful signals are unique cloners, release downloads, issues from real evaluators, demo
completion reports users volunteer, repeat contributors, and isolated-project trials—not stars
alone.

## GitHub Trending plan

GitHub documents Trending as a way to discover projects but does not publish a threshold or ranking
formula. Therefore every number below is an observation or planning assumption, not a promise.

### 2026-08-11 calibration snapshot

- Weekly all-language Trending showed 15 visible repositories; the lowest visible weekly gain was
  503 stars, with the displayed range extending into the thousands.
- Weekly Python Trending showed 15 visible repositories; displayed weekly gains ranged from 33 to
  4,113 stars. Low-tail examples included 33, 79, 136, 143, 220, and 231.
- The studio baseline is 400–600 stars/week for all-language Trending and 150–400/week for a
  language category. Today's all-language visible tail supports using **600+** as a stretch target;
  the broad Python tail supports a **150–250/week target, planned at 200**.

The target category is **Python**, because the package source is Python and the language feed is
less competitive than the all-language feed. The launch-window planning checkpoints are 30 organic
stars in the first 12 hours, 60 in 24 hours, 90 in 48 hours, and 200 in seven days. A 250-star
48-hour result is the all-language stretch trajectory. These are diagnostic targets only: never ask
anyone to star the repository.

### Mandatory T−14 to T−1 recalibration

At 09:00 JST daily, manually inspect:

- `https://github.com/trending/python?since=daily`
- `https://github.com/trending/python?since=weekly`
- `https://github.com/trending?since=daily`
- `https://github.com/trending?since=weekly`

Record the date/time, number of visible entries, lowest/median visible “stars today/this week,” and
the three closest developer-tool/data-tool comparables in an internal sheet. Do not scrape or
automate around access controls. On T−2, set each goal to the larger of the studio baseline or the
observed seven-day 25th percentile rounded up to the nearest ten. If the all-language observed tail
is above 600, raise the stretch goal; never lower the Python seven-day planning goal below 150.

Channel activity is concentrated into one 48-hour window so independent discovery compounds rather
than being diluted. The studio assumes a first Trending appearance may add roughly 10–20 stars/day
to baseline and make later appearances more likely; GitHub does not publish or guarantee this
effect. Treat it as a testable growth hypothesis. Measure it against the seven pre-launch days and
stop repeating tactics whose referred users do not run, open issues, or return.

## Two weeks before launch

| Date | Owner action | Evidence / stop condition |
|---|---|---|
| Aug 11 (T−14) | Freeze positioning; start daily Trending log; reserve human response coverage | This plan plus first calibration row |
| Aug 11 (completed early) | Create the public repository with explicit user approval; run full-history gitleaks; configure metadata and private reporting | Complete: no leaks; metadata and reporting route verified |
| Aug 11 (completed early) | Run hosted Python 3.11–3.13 CI and the release workflow | Complete: `main` and v0.1.0 release workflows green |
| Aug 17–18 | Run isolated BigQuery ADC and hosted Action/OIDC tests if credentials and a protected environment are authorized | Capture sanitized audit evidence; otherwise retain alpha caveat |
| Aug 18 (T−7) | Recheck PH/HN/Reddit rules; send one r/bigquery modmail; maker begins human PH/HN notes | Any material rule conflict removes channel |
| Aug 19–20 | Build PH thumbnail/gallery derivatives; native-size and mobile QA; verify alt text | No clipped text or missing synthetic disclosure |
| Aug 11 (completed early) | Publish v0.1.0 with explicit approval; fresh-install smoke; verify hosted provenance | Complete: wheel/sdist and one attestation per asset verified |
| Aug 22 | Create PH draft; verify direct GitHub URL, price, alpha status, and preview | Draft only; no accidental immediate launch |
| Aug 23 (T−2) | Final Trending recalibration; human rewrites PH/HN comments; dry-run day-of checklist | Human confirms no AI comment text |
| Aug 24 (T−1) | Freeze code except security/release blockers; link/secret/quickstart check; rest response team | Any Critical/High or broken install postpones |

Real ADC/OIDC evidence is desirable but absence does not require pretending the offline core is
unlaunchable. It does require retaining the prominent alpha caveat. A broken release, non-green
hosted CI, failed security gate, missing repository, or inaccurate privacy statement does require
postponement.

## The concentrated 48 hours

The window is Aug 25 00:01 PT through Aug 27 00:01 PT.

| Offset | Exact time | Action | Owner check |
|---:|---|---|---|
| T+00:00 | Aug 25 00:01 PT | Product Hunt goes live | URL, gallery, price, caveat, human maker comment |
| T+00:15 | 00:16 PT | Record baseline | GitHub stars/clones/issues/releases and PH URL |
| T+02:00 | 02:01 PT | PH response pass | Only substantive human replies |
| T+06:14 | 06:15 PT | Publish X launch note | Direct repo link; synthetic/live caveat |
| T+06:29 | 06:30 PT | Submit Show HN | Human-selected title and human-written first comment |
| T+07:14 | 07:15 PT | Publish LinkedIn | Personal truth checked; no vote request |
| T+08:00 | 08:01 PT | Verify quickstart from public URL | Fresh clone, under 60 seconds, no credentials |
| T+12:00 | 12:01 PT | Metrics and support checkpoint | Fix only security/install/docs blockers |
| T+18:00 | 18:01 PT | Handoff response coverage | No unanswered security report |
| T+24:00 | Aug 26 00:01 PT | First-day review | Record outcome without celebratory rank claims |
| T+31:29 | 07:30 PT | Technical X follow-up | Unknown-as-first-class explanation |
| T+32:29 | 08:30 PT | r/FinOps, if rules still permit | Relationship declared; no second subreddit |
| T+36:00 | 12:01 PT | Diagnose conversion | Compare referrals to installs/issues, not votes alone |
| T+47:30 | Aug 26 23:31 PT | Final response sweep | Post factual maintenance status if needed |
| T+48:00 | Aug 27 00:01 PT | Close launch window | Snapshot, incidents, lessons, next owner |

Do not move a channel earlier solely because another is underperforming. If HN is receiving an
active technical discussion, prioritize answering it over publishing the next scheduled owned
post. The r/FinOps post is optional and should be skipped if rules, disclosure, account history, or
response capacity are uncertain.

## Two weeks after launch

| Day | Action | Decision signal |
|---|---|---|
| T+1 | Triage reproducible bugs and docs confusion; publish no vanity recap | Install blockers fixed or clearly acknowledged |
| T+2 | Compare 48-hour velocity with recalibrated Python threshold | Continue Trending hypothesis only with real use signals |
| T+3 | Publish a technical article on known subtotal/coverage and dry-run privacy | Use measured, reproducible examples; synthetic label remains |
| T+4–6 | Convert recurring questions into docs or small issues | No feature expansion outside roadmap |
| T+7 | If approved by moderators, one tailored r/bigquery post; otherwise skip | Explicit mod approval and rule compliance |
| T+7 | Weekly review: stars, cloners, downloads, demo reports, issues, outside contributors, sandbox trials | Keep/pivot distribution based on qualified use |
| T+8–10 | Ship v0.1.x only for confirmed reliability/docs fixes | No release manufactured for attention |
| T+10 | Publish an evidence-based integration note if a live ADC/OIDC run now exists | Never backfill a success claim without artifacts |
| T+12 | Contributor-focused note highlighting one scoped good-first issue | No mass tagging or direct-message campaign |
| T+14 | Record launch retro and choose v0.2 work from real use; repeat Trending measurement | Stop channel if attention has no use/contribution signal |

A substantive v0.2 and follow-up article can create a second honest discovery moment, but only if
user evidence supports the release. Do not relaunch unchanged work or manufacture version numbers
to chase Trending.

## Metrics and stop rules

Capture baselines immediately before launch and snapshots at 1, 6, 12, 24, 36, 48 hours, then
days 3, 7, and 14.

| Layer | Measures | Healthy interpretation |
|---|---|---|
| Discovery | GitHub referrers, PH/HN position, social impressions | Which channel reached the intended audience |
| Activation | unique cloners, release downloads, voluntarily reported demo runs | People tried the product |
| Use | sandbox/live evaluations, repeat users, actionable issues | The problem and workflow are real |
| Community | external issues/PRs/contributors, discussion quality | Knowledge and ownership are spreading |
| Reliability | quickstart failures, security reports, crash rate from issues | Whether distribution should pause |

Stop or postpone immediately if a credential appears, a High/Critical security finding reopens, the
public package/repository differs from reviewed source, raw SQL appears in output, synthetic data is
presented as real, or hosted CI/release verification fails. Correct material public inaccuracies in
the original channel. Do not silently edit away an incident.

At T+14, do not treat stars alone as product validation. Continue only if people clone/run it,
report relevant issues, try it in a sandbox, or contribute. A high-visibility launch without use is
a distribution result, not an entrepreneurship gate.

## Go/no-go checklist

The human launch owner signs this at T−48 hours and again at T−2 hours.

### Must be green

- [x] Explicit approval to create/use the public repository, push, tag, and release
- [ ] Explicit approval to post through each human-owned launch channel
- [x] Public repository exists at the exact URLs used in all drafts
- [x] Full-history `gitleaks git .` passes over the published history
- [x] Hosted `main` CI is green on Python 3.11, 3.12, and 3.13
- [x] `v0.1.0` wheel/sdist install, hashes, `twine check`, and provenance verify
- [x] README public clone → `uv run queryspend demo` succeeds in under 60 seconds
- [x] GitHub description, topics, license, Issues, Discussions, and private reporting are visible
- [ ] Upload and verify the GitHub social preview through repository settings
- [x] No open Critical/High security finding; Gate C evidence matches the released source
- [ ] PH media has two or more gallery assets and readable synthetic/alpha disclosure
- [ ] Current PH/HN/Reddit rules and account eligibility rechecked by a human
- [ ] PH/HN comments and replies written independently by the human maker
- [ ] Six-hour response coverage and security incident owner confirmed

### May remain alpha, but must be disclosed

- [ ] Real isolated-project BigQuery ADC accuracy test completed, or “unverified” remains prominent
- [ ] Real hosted `workflow_run` + OIDC + protected-environment run completed, or “unverified” remains
  prominent
- [ ] r/bigquery mod approval received, or that channel remains skipped

If a must-green item fails, move the entire channel launch rather than publishing partial or broken
links. Do not infer live integration success from repository checks. The repository and v0.1.0 were
published under the user's 2026-08-11 instruction; this plan still does not authorize any social
post.

## Day-of operator checklist

- [ ] Compare release commit to the reviewed commit and record its 40-character SHA
- [ ] Run the secret scan, tests, lint, type check, build, link audit, clean-wheel smoke, and demo
- [ ] Open every public URL in a logged-out/private window
- [ ] Confirm PH scheduler preview says Aug 25 and shows the correct Pacific day
- [ ] Confirm demo GIF, still, social preview, and PH gallery at native and mobile sizes
- [ ] Copy no generated/AI-edited comment into PH or HN
- [ ] Confirm every synthetic number has a nearby disclosure
- [ ] Record baseline metrics before PH goes live
- [ ] Post only at the planned times and record canonical URLs/timestamps
- [ ] Keep security reports private and acknowledge them within the documented target
- [ ] Reply personally; never ask a colleague, user, friend, or audience to vote/comment/star
- [ ] At T+48, export metrics and write the first retro notes

## Primary-source research log

All sources were opened on 2026-08-11 JST. Platform rules are mutable; re-open them at T−7,
T−48 hours, and immediately before posting.

| Area | Primary source and fact used | Confidence / limitation |
|---|---|---|
| PH submission | [How to post a product](https://help.producthunt.com/en/articles/479557-how-to-post-a-product): personal account, direct URL, recommended 240×240 thumbnail, 2+ gallery images at recommended 1270×760, 260-character description, first comment, 12:01 AM Pacific operating day | High; scheduler preview controls DST/date |
| PH integrity | [Community Guidelines](https://help.producthunt.com/en/articles/3615694-community-guidelines): no mass messaging, upvote asking, bots, incentives, or artificial activity | High |
| PH comments | [Commenting Guidelines](https://help.producthunt.com/en/articles/10030102-commenting-guidelines): no AI-generated comments; person-to-person discussion | High; this is why only a worksheet is supplied |
| PH eligibility | [Featuring Guidelines](https://help.producthunt.com/en/articles/9883485-product-hunt-featuring-guidelines): useful live digital product and editorial criteria | High; featuring remains discretionary |
| HN eligibility | [Show HN Guidelines](https://news.ycombinator.com/showhn.html): maker's runnable work, easy to try, early stage permitted, no vote/comment requests | High |
| HN conduct | [HN Guidelines](https://news.ycombinator.com/newsguidelines.html): factual titles, no solicitation or generated/AI-edited comments | High |
| HN rank | [HN FAQ](https://news.ycombinator.com/newsfaq.html): age-adjusted points plus flags, anti-abuse, weighting, and moderation; no vote/comment requests | High; no rank forecast is possible |
| r/FinOps | [Official community metadata](https://www.reddit.com/r/finops/about.json): self-promotion allowed if declared | Medium; full rules and account eligibility need live UI check |
| r/dataengineering | [Official rules JSON](https://www.reddit.com/r/dataengineering/about/rules.json): monthly promo limit, disclosure, anti-shill/link review, and no heavily AI-assisted text | High for retrieved rules; current UI overrides snapshot |
| r/bigquery | [Official community metadata](https://www.reddit.com/r/bigquery/about.json): BigQuery audience and restricted posting | Medium; rules endpoint was unavailable, so mod approval is required |
| r/DBT | [Official community metadata](https://www.reddit.com/r/dbt/about.json): Drive-By Truckers topic | High; wrong audience |
| Trending | [Weekly all-language](https://github.com/trending?since=weekly) and [weekly Python](https://github.com/trending/python?since=weekly) snapshots | High for displayed snapshot, low for predictive threshold |
| Trending behavior | [GitHub discovery documentation](https://docs.github.com/en/get-started/exploring-projects-on-github/discovering-projects-on-github) | High that Trending is a discovery surface; GitHub publishes no formula/threshold |

No Reddit scraping or X scraping was used. Reddit research used official public community metadata,
and launch-day decisions remain human and manual.
