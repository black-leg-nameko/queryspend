# B2B OSS Venture Thesis — `queryspend`（仮称）

- 基準日: **2026-08-11 JST**
- フェーズ: **Phase 1 / Gate A**
- 推薦: **条件付き GO — 顧客・精度 validation へ進む**
- 最終 GO / NO-GO と名称確定: **ユーザー判断待ち**
- 実装、プロダクトディレクトリ作成、公開は未着手

## 0. 最終判断

5本の調査レポートにある22候補を同じ物差しで再評価した結果、推薦は一つに絞る。

> **`warehouse-cost-pr`: dbt + BigQuery の「このPRをmergeすると毎月いくら増えるか」を、merge前に示すOSS。**

仮称の第一候補は **`queryspend`**。Hero job は、変更されたdbt modelとdownstream lineage、BigQuery dry-run、materialization、実行頻度を結合し、PRに **recurring monthly cost delta** と根拠を返すことである。汎用FinOps dashboard、SQL linter、post-run cost explorerは作らない。

推薦理由は次の四点。

1. **OSS adoption loopが製品利用そのものに埋め込まれる。** PRコメントがチーム内で自然に露出し、required check化され、repoからorg-wide有償control planeへ広がる。
2. **狭いMVPを検証できる。** BigQueryのdry-runは無料で処理bytesを見積もれる一方、dbt側の現実的な事前cost表示要求は長く残っている。[BigQuery dry-run](https://docs.cloud.google.com/bigquery/docs/running-queries)、[dbt issue #2079](https://github.com/dbt-labs/dbt-core/issues/2079)
3. **buyerと予算線が一致する。** ChampionはAnalytics Engineering、buyerはHead of Data Platform / Data FinOps。FinOps Foundationはwarehouse単位の費用だけでは価値を説明できず、query/job telemetryとdata-product unit economicsが必要だとしている。[FinOps for Data Cloud](https://www.finops.org/insights/finops-for-data-cloud-platforms/)
4. **認知と売上の両立余地がある。** “This 8-line PR adds $14,280/month” はHN/GitHub向けの証拠artifactになり、paid側は実コスト校正、組織予算、承認・監査という業務critical pathに置ける。

ただし確信度は **medium**。技術primitiveと隣接支払い市場は確認できたが、PR cost gate単体への支払意思、予測精度、10社の本番利用は未観測である。これらを90日で反証可能にすることが本thesisの中心である。

## 1. 前提と証拠の扱い

`venture-context.yaml` は存在しないため、`opportunity-thesis-scorer` の既定を次のように適用する。

- 初期チームはsolo〜3人、MVPは1〜3週間、90日以内にrevenue signalが必要。
- Global / English-first B2B。初期地域は北米・欧州を中心にし、日本は補助市場。
- 有料広告なし。GitHub、HN、PH、dbt/data community、targeted design-partner outreachを使う。
- Founderのdata engineering / FinOps経験は不明。**founder-fitは未採点 (`null`)** とし、得意stackを推測しない。
- 規制・vendorのROI主張・提案価格を観測事実と混同しない。

入力は以下の5レポートすべて。

- [AI governance / agent security](./ai-governance.md)
- [Cross-category scan](./cross-category.md)
- [Enterprise operations](./enterprise-ops.md)
- [Infrastructure economics](./infra-economics.md)
- [Security / compliance](./security-compliance.md)

元レポートのOSS score / demand scoreは比較の出発点に使うが、その順位は採用しない。特に、2026-08-11時点の競合機能、platform absorption、OSSからbuyerへ至るloop、10社/$100k ARR経路、defensibilityを追加して再評価した。

### Evidence quality

| 層 | 今回の扱い | 例 |
|---|---|---|
| Strong | 政府・標準・公式docs、GitHub issue/repoの直接観測 | BigQuery dry-run、dbt #2079、NIST、GitHub docs |
| Medium | vendor pricing、vendor customer story、業界団体survey | SELECT、Finout、Numeric、CSA、FinOps Foundation survey |
| Weak / unproven | 提案価格、ARR算術、starからの購買推測 | $1k/month、10社×$12k、launch週star予測 |

## 2. 全22候補の横断スコア

### 再評価rubric

各項目1〜5。総合は100点換算。

| Code | Factor | Weight | 問い |
|---|---|---:|---|
| E | Evidence quality | 15 | product固有の一次証拠か、隣接proxyだけか |
| C | Commercial pain | 20 | pain、WTP、buyer/champion、budget triggerが明確か |
| O | OSS adoption loop | 15 | local OSS利用が繰り返され、有償面へ自然に拡張するか |
| M | M0 channel fit | 10 | PH/HNのheadline、demo、GitHub Trendingに適合するか |
| S | Sales path | 15 | 最初の本番10社と$100k ARRへの現実的経路があるか |
| B | Buildability | 10 | 1〜3週間で信頼できる最小MVPを検証できるか |
| D | Defensibility | 10 | platform吸収・copyに耐えるデータ/workflow/standard moatがあるか |
| X | Expansion / timing | 5 | durableなplatform展開と現在の導入triggerがあるか |

`Adjusted = Σ(score / 5 × weight)`。数値は事実ではなく、各レポートの証拠を同一基準に写した判断である。

| Rank | Candidate | Source OSS / Demand | E/C/O/M/S/B/D/X | Adjusted | 判断 / 最大の反証 |
|---:|---|---:|---|---:|---|
| 1 | **warehouse-cost-pr** | 50/60 · 4.31 | 4/4/5/5/4/4/3/5 | **84** | **推薦**。BigQuery限定なら検証可能。multi-warehouse精度とnative吸収がrisk |
| 2 | inference-econ | 53/60 · 4.56 | 4/5/4/5/4/3/1/5 | **79** | Hot waveと高ACVは強いが、NVIDIA AIPerfがvLLM/SGLang等のmulti-runtime performanceをすでに標準化。cost joinだけでは薄い |
| 3 | pg-plan-replay | 47/60 · 4.19 | 4/4/4/4/3/3/4/4 | **75** | privacy-preserving wedgeは強い。upgrade event型で頻度とACVが弱く、plan diff≠latency |
| 4 | BYOCCheck | 48/60 · 4.38 | 4/5/3/3/4/4/1/5 | **74** | 高ACVだがReplicated Compatibility MatrixとDistr preflightが既に近い面を所有 |
| 5 | Agent Privilege Diff | 49/60 · 4.19 | 4/5/4/4/3/3/1/5 | **74** | 強い波とdemo。Cisco/CrowdStrike/Microsoft/NVIDIAのbundle圧力で独立moatが弱い |
| 6 | Agent IAM sidecar | 48/60 · 4.31 | 4/5/4/4/3/2/1/5 | **72** | budget/painは強いが標準未確定、多IdP correctnessが重くplatform giantsに囲まれる |
| 7 | focus-proof | 45/60 · 4.31 | 4/5/3/3/4/3/1/5 | **72** | FinOps painは強いがFOCUS/OpenCost/Microsoft/IBM/Finoutのfeature面 |
| 8 | LedgerLens | 50/60 · 4.13 | 3/5/3/3/4/2/3/5 | **71** | 会計buyerと$20k ACVは良い。Anthropic star waveはreconciliation採用の証明でなく、connector/correctnessが重い |
| 9 | TrustPatch | 50/60 · 4.25 | 4/4/4/4/3/3/2/4 | **71** | secret撤去demoは強いが移行はone-shot。GitHub/cloud native wizardに吸収されやすい |
| 10 | Actions Incident Capsule | 47/60 · 4.07* | 4/4/4/4/3/3/1/4 | **69** | incident severityは最大だが低頻度。StepSecurityに極めて近い |
| 11 | AuthzSpec | 52/60 · 4.13 | 4/4/3/4/3/4/1/4 | **68** | 元レポート首位から降格。StackHawk/Akto/Cerbosがrole/tenant authz testをすでに提供 |
| 12 | Trajectory assurance gate | 40/60 · 3.75 | 4/4/4/4/3/2/1/5 | **68** | promptfoo/DeepEval/Giskard/Microsoft/IBM/Red Hatとの正面競争 |
| 13 | Agent inventory + access graph | 45/60 · 4.06 | 4/4/3/3/3/3/1/5 | **65** | inventory需要は強いがMicrosoft/Palo Alto/Snyk/Googleがbundle、AI-BOMはcommodity |
| 14 | CryptoMap | 47/60 · 4.13 | 3/4/3/3/3/2/3/5 | **64** | durableだが2035は遠く、低starがwhitespaceでなく低関心の可能性 |
| 15 | FlowSentry | 46/60 · 3.88 | 3/4/4/4/3/2/1/4 | **64** | cross-runtimeだけが差。native OTel/observabilityが速く追随し、payload privacyも重い |
| 16 | SeatGraph | 47/60 · 4.06 | 3/5/2/2/4/2/2/4 | **63** | ROIは明快だがOSS loopが弱く、価値がconnector completenessに比例 |
| 17 | SaaSTwin | 45/60 · 3.63 | 3/3/4/4/3/2/2/4 | **62** | demoは良いがNango/Prism/WireMock/Mockoon、provider pack保守が事業の大半 |
| 18 | Generic lineage gate | 35/60 · 3.94 | 4/4/3/3/3/2/1/4 | **62** | DataHub/GX/OpenLineage/Soda/Rockyで供給飽和 |
| 19 | AIEvidence | 45/60 · 3.81 | 3/4/3/3/3/3/1/4 | **61** | regulation needはあるがdeadline後退、OWASP/Google/GRC vendorに吸収される |
| 20 | AI Evidence Lockfile | 40/60 · 3.46* | 4/3/3/3/2/2/1/4 | **55** | SPDX/CycloneDX/cdxgenのfeature面、lockfile固有WTPが欠損 |
| 21 | ErasureProof | 31/60 · 3.44 | 4/4/2/2/3/1/1/4 | **55** | 法的painは本物でもFides/Ethycaの中核機能、connector負債が価値を支配 |
| 22 | Evidence Envelope | 39/60 · 3.87* | 3/3/2/2/3/3/2/4 | **54** | evidence automationとportability WTPを混同。MSSP/auditor acceptance未証明 |

`*` は元レポートで未観測factorを除外したcomposite。

### 順位を変えた新しい反証

- **AuthzSpec:** StackHawkはmulti-profile BOLA/BFLA、tenant isolation、cross-profile evidence chainをすでに提供し、Aktoもrole別BOLA test、Cerbosもprincipal × resource × action test suiteを備える。[StackHawk business logic testing](https://docs.stackhawk.com/hawkscan/business-logic-testing/)、[Akto role-based testing](https://docs.akto.io/api-security-testing/how-to/conduct-role-based-testing)、[Cerbos policy tests](https://docs.cerbos.dev/cerbos/latest/tutorial/04_testing-policies.html)。「versioned contract」だけでは独立会社の差にならない。
- **inference-econ:** NVIDIA AIPerfはvLLM、SGLang、TensorRT-LLM、Tritonを横断したTTFT/TPS/cache/MFU metricsとconcurrency Pareto benchmarkを提供する。[AIPerf metrics](https://docs.nvidia.com/aiperf/server-metrics/ai-perf-server-metrics-reference)、[benchmark guide](https://docs.nvidia.com/aiperf/getting-started/ai-perf-comprehensive-llm-benchmarking)。billing/outcome joinは残るが、defensibilityは元評価より低い。
- **BYOCCheck:** Distrはpre-flight checks、BYOC、air-gapを提供し、Replicatedはair-gap Compatibility Matrixでnetwork egress reportを生成する。[Distr pre-flight](https://distr.sh/docs/agents/preflight-checks/)、[Replicated CMX](https://docs.replicated.com/vendor/tutorial-cmx-airgap)。readiness compilerは既存platformのfree acquisition featureになりやすい。

## 3. 上位3案と「今は作らない」理由

### 1位 — `warehouse-cost-pr` / 推薦

唯一、**継続利用されるOSS artifact、狭い技術primitive、buyerの予算、org control planeへの課金**が同じworkflowでつながる。直接WTPは未証明なので、build GOではなくvalidation GOである。

### 2位 — `inference-econ` / wait

vLLM 88k+ starsという巨大audience、FinOps buyer、3〜6社で$100k ARRという点は最強。ただしNVIDIA AIPerfがperformance layerを急速に標準化し、OpenCostがcost allocationを所有する。正確なshared GPU / cache / spot / failure原価を実装する重さに対し、残る差が「価格を掛け算するUI」へ縮む危険が高い。再開条件は、5社でAIPerf + OpenCostでは答えられないplacement decisionを3種類以上確認すること。

### 3位 — `pg-plan-replay` / wait

statistics-only、production dataを持ち出さない、version matrixという技術差は最も守りやすい。一方、導入triggerはupgrade/schema/index eventで日次critical pathではなく、$500〜1k/monthでは$100k ARRに9〜17社必要。まず既知regression 20件でprecision/recallを証明し、upgrade campaignから継続契約へ移れるかを確認すべき。

## 4. 推薦thesis

### Pain

Data warehouseの請求はmerge後に見えるが、どのdbt PRがどのmodel/downstream scheduleを通じて、毎月のBigQuery費用をいくら変えるかはmerge前に分からない。現在のworkaroundはcompiled SQLの手動dry-run、query history、dbt lineage、schedule、価格表を人が結合すること。[BigQuery pricing](https://cloud.google.com/bigquery/pricing)、[dbt #2079](https://github.com/dbt-labs/dbt-core/issues/2079)

### ICP / persona

| Role | Initial definition |
|---|---|
| ICP | BigQuery on-demand + dbt Core/Cloud、data team 5〜50人、月間BigQuery spend $10k+、model 300+、週10 PR以上のB2B SaaS / marketplace / e-commerce |
| Daily user / champion | Senior Analytics Engineer、Analytics Engineering lead、Data Platform Engineer |
| Operational buyer | Head of Data Platform、Data FinOps lead、Analytics Engineering manager |
| Economic buyer | VP Data / CTO / VP Engineering。cost mandateが強い場合はFinOps/Financeがco-buyer |
| Buying trigger | bill spike、dbt/Fusion migration、model急増、CFO cost-cut、chargeback導入、重大なfull-refresh事故 |

対象を「BigQueryを使う全社」に広げない。初期は **on-demand billing、dbt SQL model、GitHub PR** の三条件を満たす組織だけにする。

### Wedge

> **`dbt` PRに対して、changed model + downstream lineage + materialization + run frequency + BigQuery dry-runを結び、merge後のrecurring monthly cost deltaを根拠付きで返す。**

勝つ軸は「dashboardの機能数」ではなく、**merge前・monthly delta・reproducible evidence**の一点。

### Smallest MVP（1〜3週間）

Core experience:

```text
Git diff + dbt manifest
        ↓
changed nodes + downstream schedule
        ↓
base/head compiled SQL → BigQuery dry-run
        ↓
materialization-aware recurring monthly delta
        ↓
PR comment + required check + JSON artifact
```

含めるもの:

1. BigQuery **on-demand** billingのみ。
2. dbt `table` / `view` model。`incremental` は信頼できる推定ができるまで `unknown` と返す。
3. `manifest.json`、base/head compiled SQL、明示したrun frequencyを入力。
4. bytes delta、月額delta、最大contributor、confidence、計算根拠を表示。
5. GitHub Action、local CLI、machine-readable JSON、threshold policy。
6. credentialsはGitHub OIDCまたはuser runner内に留め、queryを実行せずdry-runだけ行う。

明示的なnon-goals:

- Snowflake / Databricks / Redshift対応
- flat-rate / reservation / slot autoscalingの完全推定
- post-run FinOps dashboard、chargeback、invoice reconciliation
- SQL自動最適化、AI rewrite、query router
- Python model、BigQuery ML、cross-repo lineage
- 「必ずこの金額になる」というfalse precision

### Pricing hypothesis / 課金境界

| Layer | Boundary |
|---|---|
| OSS (Apache-2.0仮説) | local CLI、BigQuery dry-run、single-repo GitHub Action、policy file、PR comment、JSON artifact。ローカル判定をpaywallにしない |
| Cloud Team — **$1,000/month** | repo/history、actual-vs-predicted calibration、budget owner、team policy、Slack、30-day evidence、3 repos |
| Enterprise — **$24k+/year** | SSO/SCIM/RBAC、approval/waiver、private runner、contract rate、multi-repo budget、long retention、audit、SLA |
| Sponsor | public warehouse adapter / benchmark corpusの維持。主要ARR経路には数えない |

主経路は **OSS → managed cloud / open-core control plane**。Sponsorはcommunity maintenance用で、$100k ARR thesisの代わりにしない。

### OSS adoption loop

```text
1 command / GitHub Action
        ↓
具体的な「+$14,280/month」PR artifact
        ↓
reviewerがrequired check化
        ↓
model・schedule・policyがrepo内で蓄積
        ↓
複数repoのhistory / ownership / waiverが必要
        ↓
paid org control plane
```

このloopではstarを見るだけの人ではなく、PRをmergeするteamが利用者になる。PR commentとbadgeはteam内distribution、公開benchmarkはGitHub/HN distribution、有償control planeはbuyer conversionを担当する。

### Moat story

**現時点で強いmoatはない。** BigQuery、dbt、SELECT、Finout、Rockyが機能を追加できる。12か月で次の複合moatを作れなければ独立会社にはならない。

1. **Calibration data:** predicted bytes/monthly deltaと実際の7/30-day costを結ぶorg固有履歴。private dataは外部共有せず、opt-inのaggregateだけをモデル改善に使う。
2. **Semantics corpus:** dbt materialization、macro、incremental strategy、scheduleによる誤差fixtureと公開benchmark。単なるdry-run wrapperから脱する。
3. **Workflow lock-in:** required checks、budget ownership、waiver、audit trail、org policyがrelease processのsystem of recordになる。
4. **Vendor-neutral schema:** `Cost Change Manifest`をopen format化し、BigQuery後にSnowflake/Databricks adapterが同じPR workflowへ参加する。
5. **Trust:** unsupported caseを `unknown` と返し、予測coverage・誤差を継続公開する。魔法のAI最適化より信頼を防御線にする。

### Riskiest assumption

> BigQuery dry-run、dbt lineage/materialization、scheduleから得たrecurring cost deltaが、PRをblockするに足る精度と説明可能性を持ち、data teamが既存dashboardとは別に$1,000/monthを払う。

### Cheapest test（7日以内）

製品を作る前に、3つの公開/synthetic dbt BigQuery projectで10 PRを作り、base/head dry-runと7-day simulated scheduleを比較する。同時に5人のAnalytics Engineering / Data Platform leadへ静的HTMLのPR commentを見せる。

Success threshold:

- monthly delta median error **≤15%**、p90 **≤30%**
- changed/downstream cost attribution **≥80%**
- false blocker **≤5%**
- 5人中3人が現行workflowにないと回答し、2人がread-only design partnerを受諾
- 少なくとも1人が **$1k/month** の価格でpaid pilot intentを示す

これを満たさなければMVP実装へ進めない。

## 5. 12-factor demand score

元レポートの数値を再検討し、直接WTPが未観測であるためWTPを5から4、BigQuery限定MVPのbuildabilityを4とした。結果は同じ **4.13/5** だが、意味は異なる。

| Factor | Score | 一行根拠 |
|---|---:|---|
| pain_severity | 4 | margin/予算を悪化させるが、すべてのPRがincidentではない |
| frequency | 5 | dbt PRとscheduled runごとにcost decisionが発生 |
| urgency | 4 | FinOps scope拡大とbill spikeがtrigger。AI securityほど常時緊急ではない |
| willingness_to_pay | 4 | SELECT/Finout等の隣接支払いはあるが、PR gate単体の契約は未観測 |
| existing_workaround | 5 | dry-run、query history、lineage、schedule、価格表の手動結合 |
| dissatisfaction_with_alternatives | 4 | dbt事前bytes要求が未実装、既存dashboardはmerge後中心 |
| buyer_clarity | 5 | Head of Data Platform / Data FinOpsとchampionが明確 |
| distribution_fit | 5 | GitHub PR、dbt ecosystem、data engineering communityに自然露出 |
| buildability | 4 | BigQuery on-demand + table/view限定なら1〜3週。multi-warehouseは対象外 |
| competition_saturation | 3 | direct OSSは弱いがSELECT/Rocky/dbt/Googleが隣接 |
| market_size | 4 | BigQuery+dbtは十分大きいが初期ICPは意図的に限定 |
| expansion_potential | 5 | cost gate→actual calibration→org budget→multi-warehouse unit economics |
| **Weighted composite** | **4.13 / 5** | severity/WTP/distribution/buildabilityを二重加重 |

- 最弱factor: `competition_saturation = 3`
- 次点risk: `pain_severity / urgency / WTP / market_size = 4`。特にWTPは隣接proxyである。
- `founder_fit = null`: skill/顧客networkが不明。
- `time_to_first_signal = 5/5`: dry-run prototypeとPR artifactは7日以内に反証可能。

## 6. 本番10社と$100k ARRへの経路

### 「本番利用」の定義

単なるinstall、star、1回のscanは本番利用に数えない。1社をproduction userと数える条件はすべて満たすこと。

1. production dbt repoのdefault branchでrequired checkとして稼働。
2. 3つ以上のproduction model / 20回以上のPRを判定。
3. 4週間以上継続し、budget thresholdまたは明示waiverが使われる。
4. 少なくとも一つのmerge decision、cost regression防止、またはaccepted waiverを記録。

### Initial sales motion

| Stage | Target | Motion |
|---|---:|---|
| Problem interviews | 15 teams | dbt/BigQueryを公表するB2B SaaS、data consultancy、FinOps practitionerへ低量・個別outreach |
| Concierge validation | 5 teams | 過去30 PRをread-only分析し、既存query-history SQLと比較 |
| Paid design partners | 3 teams | $1k/month、implementation込み、BigQuery on-demand限定 |
| Production references | 5 teams | required check 4週間、accuracy/avoided-cost case studyは顧客同意時のみ公開 |
| 起業ゲート | **10 teams** | **10 × $12k/year = $120k ARR** |

Acquisitionは三本立て。

1. **OSS inbound:** GitHub Action / dbt package、public benchmark、PR artifact。
2. **Direct design partner:** data platform leadへのtargeted outreach。大量cold blastはしない。
3. **Channel:** dbt / BigQuery consultancy、FinOps consultancyがcost reviewにrunnerを組み込む。紹介料や共同販売は顧客価値を透明にする。

HN/PHは認知チャネルであって、10社のenterprise salesを代替しない。

## 7. PH / HN / GitHub Trending仮説

### Launch artifact

- Show HN: **“This 8-line dbt PR adds $14,280/month to BigQuery — catch it before merge”**
- Product Hunt: **“See the monthly warehouse bill of every dbt PR before you merge.”**
- 30 PRのpublic reproducible benchmark、before/after PR、計算式、unsupported casesを同時公開。
- credentials不要のsample repo / BigQuery public dataset demoを用意する。

Channel fit:

| Channel | Fit | 根拠 / 条件 |
|---|---|---|
| Hacker News | High | code review、cloud bill、具体的dollar proofはHN向き。benchmarkがなければ単なるFinOps pitchになる |
| Product Hunt | Medium | buyerは存在するが専門的。interactive PR previewとpolished hosted demoが必要 |
| GitHub | High | Action、PR comment、badge、policy fileが日常workflowに残る |

### GitHub Trending target

- 推薦実装カテゴリ: **Python**。dbt artifact/macro ecosystemとの距離が短い。Gate A前なので実装決定ではない。
- 憲章の安全目標: 言語別週間 **150〜400 stars**、全言語週間 **400〜600 stars**。
- M0で両方を狙うlaunch target: **Day 2で250〜350、Day 7で500〜600 stars**。数値は目標であって予測ではない。
- 2026-08-11の調査snapshotではPython weekly tail 33 stars、all-language tail 503 starsだったが、Trendingは純粋なstar閾値ではない。launch前1〜2週に再校正する。

PH/HN 1位を保証する根拠はない。狙える理由は「費用を具体額で証明する10秒artifact」とPR内distributionであり、弱点はBigQuery/dbtという専門性である。benchmarkで驚くほど大きな実例が出なければ、PH/HN #1仮説は棄却する。

## 8. 90日validation plan

基準日を2026-08-11とする。

### Day 0–7 — technical truth（〜2026-08-18）

- 3 public/synthetic projects、10 cost-changing PR、table/viewのみ。
- base/head dry-run、schedule、monthly deltaを手作業でもよいので再現。
- PR comment mockを5人に見せる。
- Gate: median error ≤15%、attribution ≥80%、2 design partners。

### Day 8–30 — problem / workflow truth（〜2026-09-10）

- 15 interviews。意見でなく、直近のbill spike、現行SQL、PR processを見せてもらう。
- 5 consenting teamsの過去30 PRをconcierge分析。
- 少なくとも3 teamで既存toolがmerge-before recurring deltaを出せないことを確認。
- OSS alphaはBigQuery on-demand、table/view、GitHub Actionだけ。

### Day 31–60 — production behavior（〜2026-10-10）

- 3 design partnersでread-only CI。
- 100 PR以上を評価、false blocker ≤5%、setup median ≤15分。
- 2社でrequired checkを2週間継続。
- $1k/month相当のpaid pilotを2社以上。

### Day 61–90 — commercial / community truth（〜2026-11-09）

- paid pilot 3社、production definitionを満たす2社。
- 4週間のrepeat usage、合計200 PR checks。
- 25 repeat-active repos、10人以上のnon-author issue/discussion参加者、3人以上のexternal contributors。
- 1社以上でmerge decisionが変わった事実。savings額は二重計上せず、再現条件付きで記録。

## 9. Kill criteria

### 即時kill / pivot

- 10 PRのtechnical testでmedian error >20%、p90 >40%、attribution <80%、false blocker >10%。
- safeなread-only権限で必要なdry-runができず、broad production data accessを要求する。
- BigQuery/dbt/SELECT/Rockyが同等の`changed lineage × schedule × recurring monthly delta × PR gate`を提供し、1日未満のglueで置換できる。

### 30日

- 15 interviews中、直近12か月のcost regression / manual merge-before checkを具体的に示すteamが5未満。
- 5 concierge teams中、3 team以上がnative/SELECT/既存SQLで十分と判断。
- read-only design partnerが2社未満。

### 90日

- paid pilotが3社未満、または$1k/month anchorを受け入れるteamが2社未満。
- production required checkを4週間継続する企業が2社未満。
- repeat-active repos <25、non-author issue/discussion participants <10、external contributors <3。
- starsが多くても、weekly repeat usageまたはproduction decisionの証拠がなければlaunch successと見なさない。

### 起業判断

- **2027-02-11（6か月）:** production 5社未満、またはcontracted ARR $36k未満ならpivot / upstream contributionを検討。
- **2027-08-11（12か月）:** production 10社未満、またはARR $100k未満なら、このthesisでの起業はNO-GO。star数に関係なく判断する。
- 逆にlaunch週400 stars未満でも、10社/$100k ARRとMoM利用成長があれば事業は継続する。Trendingはdistribution testであり起業gateではない。

## 10. 主要リスク

| Risk | Severity | Early mitigation / test |
|---|---|---|
| Cost predictionのfalse precision | Critical | on-demand/table/viewに限定、confidenceと`unknown`、actual-vs-predicted benchmark公開 |
| Incremental/slot reservationで意味が崩れる | High | MVP対象外。実測calibrationが80% coverageに達してから追加 |
| Google/dbt/SELECT/Rockyによる吸収 | High | open manifest、cross-vendor workflow、history/ownership/waiver、6週ごとの競合監査 |
| Warehouse credential / SQL漏洩 | High | OIDC、least privilege、runner-local、query非実行、保存off default、security review |
| BigQuery-only TAM ceiling | Medium | 10社/$100kをBigQueryだけで先に証明。早すぎるmulti-warehouse化をしない |
| Cost削減が一度で終わる | Medium | PR gateとbudget policyを継続workflow化。単発audit buyerはICPから外す |
| Buyerとuserの分離 | Medium | PR artifactをchampion、org budget/waiverをbuyer向けにし、同じデータを共有 |
| OSS userがpaidに転換しない | High | paid boundaryをhistory/coordination/complianceに置き、90日でpilot conversionを測る |

## 11. プロダクト名候補と空き確認

確認時刻: **2026-08-11 11:55 JST**。すべて小文字ケバブケース（単語一つのためhyphenなし）。

確認方法:

- GitHub handle: `GET https://api.github.com/users/<name>` が404
- exact public repo: GitHub repository searchでcase-insensitive exact nameが0件
- domain: Verisign `.com` RDAP / Google Registry `.dev` RDAPが404

| Rank | Name | 発音 / 意味 | GitHub handle | Exact public repo | `.com` | `.dev` | 判断 |
|---:|---|---|---|---:|---|---|---|
| 1 | **`queryspend`** | クエリ・スペンド。何の費用か即座に分かる | 404 | 0 | RDAP 404 | RDAP 404 | **推薦**。検索意図と製品価値が一致 |
| 2 | `querydelta` | クエリ・デルタ。PR差分を強く表す | 404 | 0 | RDAP 404 | RDAP 404 | 明快。ただし一般的なcode symbolとして検索noiseあり |
| 3 | `waredelta` | ウェア・デルタ。warehouse cost差分 | 404 | 0 | RDAP 404 | RDAP 404 | 独自性は高いが“ware”の意味説明が必要 |
| 4 | `sqlspend` | エスキューエル・スペンド | 404 | 0 | RDAP 404 | RDAP 404 | 発音容易。将来SQL以外へ広げる時に狭い |
| 5 | `queryfare` | クエリ・フェア。queryの運賃 | 404 | 0 | RDAP 404 | RDAP 404 | 覚えやすいがenterprise seriousnessはやや弱い |

「空き」の意味には限界がある。

- GitHub repo名はglobal uniqueではない。handle 404とexact public repo 0件は、商標・private repo・将来取得を保証しない。
- RDAP 404は現時点で登録recordを確認できなかったという意味。registrarのpremium/reserved判定、購入可能性、価格を保証しない。
- npm/PyPI、各SNS、各国商標、法人名は未確認。名称確定前にregistrar checkout、package registry、USPTO/EUIPO/J-PlatPat、一般web検索を再確認する。
- 空きは秒単位で変わり得るため、ユーザーが名称を確定した直後に取得する。

## 12. Gate A — ユーザー判断

推薦は **`warehouse-cost-pr` thesisを条件付きGO**、名称は **`queryspend`**。

次フェーズへ進むには、ユーザーが次の二点を明示的に確定する必要がある。

1. **GO / NO-GO:** 7日technical + customer validationへ進むか。
2. **Product name:** `queryspend`、または上記候補から一つ。

GO後も直ちにfull productを実装せず、最初に7日testのthresholdを通す。承認前は`<product>/`を作らず、SPEC / prototypeへ進まない。
