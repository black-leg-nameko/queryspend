# queryspend — MVP Product & Implementation Spec

- Date: 2026-08-11 JST
- Status: agreed for Phase 2; validation-first
- Product name: `queryspend`
- Canonical thesis: [`THESIS.md`](./THESIS.md)
- Build budget after validation: solo〜3人、1〜3週間
- Initial market/language: Global B2B、English-first。CLI、GitHub comment、error message、schema field は英語とする

## このMVPで検証する仮説

BigQuery on-demand と dbt Core/Cloud artifact を使う data team は、GitHub PR の merge 前に、変更 model と downstream lineage、materialization、明示された run frequency、base/head の BigQuery dry-run を結合した **recurring monthly cost delta** を見られれば、説明可能な cost regression check として継続利用する。

技術的に検証する中心命題は次の一つである。

> `table` / `view` の dbt SQL model に限定し、予測不能な条件を `unknown` に落とすなら、monthly delta の median error ≤15%、p90 ≤30%、cost attribution ≥80%、false blocker ≤5% を満たせる。

このMVPは「すべての warehouse cost を正確に予測する」ことを検証しない。BigQuery dry-run が返す bytes は見積もりであり、表示額は契約請求額ではない。入力・materialization・価格・frequency・参照先のいずれかが信頼条件を満たさない場合、具体額を捏造せず `unknown` と理由を返す。

## スコープ外（v2以降）

- Snowflake、Databricks、Redshift、Athena、および BigQuery 以外の warehouse adapter
- BigQuery capacity / reservation / slot autoscaling、flat-rate、contract discount の推定
- `incremental`、`ephemeral`、Python model、seed、snapshot、BigQuery ML、stored procedure、script、DML/DDL model
- dbt Cloud API、job schedule API、GitHub App、複数 repo、cross-repo lineage
- actual invoice reconciliation、post-run FinOps dashboard、chargeback、cost allocation、履歴 UI
- SQL lint、自動最適化、AI rewrite、query routing、merge waiver workflow
- storage cost、streaming、data transfer、BI Engine、external data source の料金推定
- free tier、credits、tax、currency conversion を PR 単位へ配賦すること
- Web UI / mobile app。MVPにはユーザー向け Web UI がないため `DESIGN.md` は不要。将来 UI を実装する場合は、実装前に [awesome-design-md](https://github.com/voltagent/awesome-design-md) からポジションに適合する `DESIGN.md` を選択・適応インストールし、Gate B で desktop と 375px の両方を検収する。見た目の token は本 SPEC では規定しない

## 1. 問題、ユーザー、成功条件

### 1.1 Problem / evidence

BigQuery の請求と query history は merge 後の cost を示すが、どの dbt PR が定期実行を通じて月次 cost をいくら変えるかを merge 前に説明しない。現行 workaround は compiled SQL の dry-run、dbt lineage、schedule、価格表を人が結合する作業である。BigQuery dry-run は query を実行せず概算 processed bytes を返し、on-demand の cost estimate に使える。一方で外部 table や clustered table など見積もりに制約があるため、本製品の差は「数字を出すこと」ではなく「数字を出せない条件を明示すること」にある。

根拠と競合評価は `THESIS.md` および `research/b2b-venture-2026/infra-economics.md` の `warehouse-cost-pr` 節を正本とする。

Implementation contractの一次資料は [BigQuery dry-run](https://docs.cloud.google.com/bigquery/docs/running-queries#dry-run)、[BigQuery pricing](https://cloud.google.com/bigquery/pricing)、[BigQuery IAM](https://docs.cloud.google.com/bigquery/docs/access-control)、[dbt artifact schemas](https://schemas.getdbt.com/)、[Google Cloud Workload Identity Federation for deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines)、[GitHub OIDC for Google Cloud](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-google-cloud-platform) とする。実装時にAPI/role/schemaの現行仕様を再確認する。

### 1.2 Persona

| Role | MVPでの仕事 |
|---|---|
| Primary user | Senior Analytics Engineer / Data Platform Engineer。PR author または reviewer として cost regression を merge 前に判断する |
| Champion | Analytics Engineering lead。check を repo に導入し threshold と frequency を管理する |
| Operational buyer | Head of Data Platform / Data FinOps lead。繰り返し利用と avoided regression を評価する |
| ICP | BigQuery on-demand + dbt Core/Cloud artifact + GitHub、data team 5〜50人、model 300+、週10 PR以上 |

### 1.3 Job to be done

「dbt model の変更を review するとき、merge 後の毎月の BigQuery analysis cost が増減する見込みと、その根拠・不確実性を PR 内で確認し、危険な変更だけを止めたい。」

### 1.4 Activation と MVP success

**Activation event:** production repo の PR で、少なくとも1つの affected `table` modelについて base/head dry-run、explicit frequency、explicit price を用いた `known` estimate が生成され、CLI または GitHub check に表示されること。

**7日 technical gate:** 最低3 project、10 cost-changing PRで次をすべて満たす。満たさなければ launchable core の実装へ進まず、計算モデルを修正または thesis を pivot する。

- monthly delta absolute percentage error: median ≤15%
- 同 error: p90 ≤30%
- cost-weighted attribution ≥80%
- false blocker ≤5%。10 PRだけで測る場合は false blocker 0件が必要
- unsupported/unknown を全件理由付きで報告し、既知値として集計しない

**Day 60 / 90 outcome:** 90日指標は §15 の versioned artifact から再計算できなければならない。star や install は production usage の代替にしない。

## 2. スコープ管理

### 2.1 Must / Should / Won't

| Priority | Scope |
|---|---|
| Must | credential-free demo、dbt manifest v10〜v12 normalizer、base/head semantic diff、changed + downstream graph、BigQuery on-demand dry-run、`table`/`view` materialization rules、explicit monthly frequency / price、confidence / evidence、threshold policy、terminal / Markdown / JSON の同一判定、single-repo GitHub Action、OIDC / ADC、validation evaluator、fixtures、tests |
| Should | `config.meta.queryspend.runs_per_month` の frequency fallback、base/head manifest が異なる supported versionでも normalize、same-run deterministic caching、`NO_COLOR` / non-TTY対応、partial provider failureでも完全な diagnostics artifact を保存 |
| Won't | §「スコープ外」の全項目、anonymous telemetry の自動送信、SQL全文を含む report、`pull_request_target` workflow、service-account key の推奨、unsupported case を dollar へ外挿する fallback |

Should は Must の acceptance criteria と7日 gateを損なう場合に切る。Must を削って multi-warehouse や UI を足してはならない。

### 2.2 Default assumptions

- Python 3.11+ の local-first OSS CLI。HTTP service は作らない
- package/import/command はすべて `queryspend`
- pricing currency は USD のみ
- calendar month は入力値 `runs_per_month` をそのまま使う。cron や `runs_per_day × 30` の暗黙換算をしない
- repository root の `.queryspend.yml` を自動検出する。存在しなくても bytes-only check は動き、欠けた price/frequency は `unknown` になる
- local auth は Application Default Credentials、CI は GitHub OIDC / Google Workload Identity Federation を第一選択とする
- `venture-context.yaml` は未作成。将来作成しても、本SPECより広い scope や緩い privacy/security を許可しない

## 3. Core flow

### 3.1 One flow that proves value

1. User は base branch と PR head を別々に `dbt compile` し、各 `manifest.json` を得る。dbt Cloud では同等 artifact を download する。
2. User は modelごとの `runs_per_month` と BigQuery on-demand `price_per_tib_usd` を `.queryspend.yml` または dbt `meta` に記載する。
3. `queryspend check --base <manifest> --head <manifest>` を実行する。
4. queryspend は model の semantic fingerprint を比較し、changed model と base/head 両 graph の downstream model を列挙する。
5. supported side の compiled SQL を `dry_run=true` / `use_query_cache=false` で BigQuery へ送り、SQLを実行せず bytes と参照 metadata を取得する。
6. materialization、frequency、price、minimum billing approximation を結合し、model別 delta、known subtotal、coverage、confidence、reason codes を作る。
7. pure policy evaluator が `pass | warn | block | unknown` を決める。
8. 同じ report object を terminal、GitHub PR comment / check summary、JSON artifact に render する。

### 3.2 dbt artifact の作り方は製品境界の外

MVP Action は `dbt compile`、package install、macro execution、dbt Cloud API download を実行しない。caller が base/head manifest を用意する。理由は、PR内の任意 macro を cloud credential 付き runner で実行しないことと、dbt Core/Cloud双方を artifact contract で扱うためである。

README の real-project example は、PR branchをcheckoutしてartifactを作るunprivileged `pull_request` workflowと、default branch上のtrusted `workflow_run` workflowを分離する。後者だけがOIDCを取得し、source repository/event/head SHAを検証してからmanifestをdataとして読む。trusted workflowはmanifest/compiled SQLをshellやPythonとして実行せず、full SHA pinしたqueryspend Actionへ渡すだけにする。同一workflow内のjob分離だけでは、PRがworkflow自体を書き換えられるためsecurity boundaryとみなさない。

## 4. Technical architecture

### 4.1 Required stack

- Runtime: Python 3.11+
- CLI: Typer
- Validation/config: Pydantic v2 + PyYAML
- BigQuery: `google-cloud-bigquery`
- Auth: Google Application Default Credentials。GitHubでは `google-github-actions/auth` が生成する短命 credential file
- Packaging: `pyproject.toml`、wheel、`pipx run queryspend`
- Quality: pytest、pytest-cov、Hypothesis、mypy strict対象をcore package、Ruff
- Money arithmetic: `decimal.Decimal`。binary float で金額計算しない
- JSON schema: repository内に report/config/observation/validation の各 v1 schemaを同梱する

### 4.2 Module ownership

```text
queryspend/
  cli.py                  # argument parsing only
  config.py               # YAML/env -> normalized config
  dbt_artifacts.py        # manifest version detection/normalization
  graph.py                # semantic diff and descendants
  providers/base.py       # Provider protocol
  providers/bigquery.py   # sole MVP provider; dry-run only
  estimator.py            # materialization/frequency/price math
  confidence.py           # deterministic evidence rules
  policy.py               # pure threshold decision
  models.py               # request/report Pydantic models
  renderers/{terminal,markdown,json}.py
  validation.py           # benchmark metric calculation
  demo.py                 # recorded, clearly synthetic fixture path
```

CLI、Action、Python API は `evaluate(EvaluationRequest) -> QuerySpendReport` を必ず共有する。rendererやActionに独自のcost計算・policy分岐を置かない。

### 4.3 Public extension points

MVPで実装する adapter は BigQuery のみだが、次を公開 Protocol として固定する。

- `ArtifactNormalizer.normalize(path) -> NormalizedManifest`
- `WarehouseProvider.dry_run(request) -> DryRunEvidence`
- `Policy.evaluate(report, config) -> PolicyDecision`
- `Renderer.render(report) -> str | bytes`

外部 plugin discovery、entry point loading、別warehouse implementation は v1では行わない。protocol、fixture、JSON schemaを公開することが拡張点であり、未実装 provider を選択した場合は `unsupported_provider` とする。

## 5. CLI / Python API / GitHub Action contract

### 5.1 Commands

#### `queryspend demo`

```text
queryspend demo [--format terminal|json] [--output PATH]
```

- network、credential、config不要
- bundled synthetic manifest と recorded dry-run response を使う
- headingに `SIMULATED DEMO — not a live BigQuery estimate` を常時表示する
- clean machineで `pipx run queryspend demo` が60秒以内に完了する

#### `queryspend check`

```text
queryspend check \
  --base path/to/base/manifest.json \
  --head path/to/head/manifest.json \
  [--config .queryspend.yml] \
  [--output queryspend-report.json] \
  [--format terminal|json] \
  [--no-progress]
```

- `--base` と `--head` は必須。環境変数や git checkout から暗黙生成しない
- `--config` 未指定時は current directory から親へ git rootまで `.queryspend.yml` を検索する
- `--output` default は `queryspend-report.json`
- human output は stdout、progress は TTYのstderrのみ。`--format json` のstdoutにはJSON以外を出さない
- report file は成功、partial unknown、policy block の全場合でatomic writeする。auth/input global failureでは可能な範囲のdiagnostic reportを出す

#### `queryspend render`

```text
queryspend render --input queryspend-report.json --format terminal|markdown|json
```

provider accessなしで既存reportを再描画する。GitHub Action はMarkdown rendererをこの経路と同じlibrary callで使う。

#### `queryspend validate`

```text
queryspend validate \
  --predictions 'validation/predictions/*.json' \
  --observations validation/observations.jsonl \
  --output validation-report.json
```

§15の指標を機械計算する。thresholdはこのSPECの値をbuilt-in profile `technical-gate-v1` として固定し、CLI optionで都合よく緩和できない。研究用途の別profileは別名で出力し、gate合否に使わない。

### 5.2 Exit codes

| Code | Meaning | GitHub check conclusion |
|---:|---|---|
| 0 | evaluation completed; `pass`、`warn`、またはdefault non-blocking `unknown` | success。summaryに状態を文字で表示 |
| 2 | CLI usage、config、manifest schema/shape invalid | failure |
| 3 | policy decision `block` | failure |
| 4 | authentication/authorization failure | failure |
| 5 | BigQuery/provider global failure after retry | failure |
| 6 | internal invariant / unexpected exception | failure、stack traceはdebug logのみ |

Per-model BigQuery error は原則そのmodelを `unknown` にしてevaluationを継続する。全eligible modelがprovider errorになった場合のみ code 5。`unknown_behavior: block` を明示した場合、その policy block は code 3でありprovider failureと区別する。

### 5.3 Python API

```python
from queryspend import EvaluationRequest, evaluate

report = evaluate(EvaluationRequest(
    base_manifest="base/manifest.json",
    head_manifest="head/manifest.json",
    config=".queryspend.yml",
))
```

- APIはCLIと同じnormalized config、provider、report schema、policyを使用する
- recoverable unknown/unsupported は exception ではなくreport diagnosticsになる
- invalid input、auth、global provider error は型付き exceptionとpartial reportを持つ
- HTTP API、daemon、upload endpointはMVPに含めない

### 5.4 GitHub Action

Action inputsはCLIに1対1で対応する。

| Action input | Required | Default | CLI equivalent |
|---|---:|---|---|
| `base_manifest` | yes | — | `--base` |
| `head_manifest` | yes | — | `--head` |
| `config` | no | `.queryspend.yml` | `--config` |
| `report_path` | no | `queryspend-report.json` | `--output` |
| `comment` | no | `true` for same-repo PR | Markdown renderer |

Action outputs:

- `decision`: `pass | warn | block | unknown`
- `known_monthly_delta_usd`: decimal stringまたは空文字
- `confidence`: aggregate confidence
- `report_path`: JSON artifact path

Check nameは `queryspend/cost`。commentには `<!-- queryspend-report:v1 -->` markerを付け、同botの既存commentをupdateして重複させない。fork PR、read-only token、comment permission failureではjob summaryとartifactを残し、cost evaluation自体を失敗させない。

## 6. Configuration schema

Canonical file: `.queryspend.yml`。unknown key は typo 防止のため error。schema versionは必須。

```yaml
version: 1

warehouse:
  provider: bigquery
  billing_model: on_demand
  billing_project: analytics-ci
  location: US
  price_per_tib_usd: "6.25"   # example only; user-owned current gross rate

frequencies:
  default_runs_per_month: null
  models:
    model.analytics.fct_orders: "720"
    model.analytics.dim_customer: "30"

policy:
  max_monthly_delta_usd: "500.00"
  max_monthly_delta_bytes: null
  action: block                  # warn | block
  minimum_confidence: high       # high | medium | low
  unknown_behavior: warn         # warn | block | ignore

privacy:
  include_model_names: true
  include_relation_names: false
```

### 6.1 Field rules

| Field | Rule / default |
|---|---|
| `version` | integer `1` only |
| `warehouse.provider` | default `bigquery`;他値はunsupported error |
| `billing_model` | default `on_demand`;他値はglobal unsupported。capacity利用者へ金額を出さない |
| `billing_project` | defaultはADC quota projectまたはBigQuery client project。解決不能ならconfig error |
| `location` | optional。未設定ならquery/clientが一意に決められる場合だけ使用。複数location・mismatchはmodel unknown |
| `price_per_tib_usd` | optional positive Decimal string。未設定時はbytesを返すがUSDはunknown。queryspendはlive priceをfetchせず、built-in価格を本番defaultにしない |
| `default_runs_per_month` | default `null`。0以上のDecimal string。暗黙推定しない |
| `models` | dbt `unique_id` -> 0以上のDecimal string。head値を優先し、deleted modelにはbase値を使う |
| `max_monthly_delta_usd` | optional。price/frequencyがknownなmodelだけ判定対象 |
| `max_monthly_delta_bytes` | optional integer。priceなしでもbytes-run deltaを判定可 |
| `action` | default `warn`。threshold超過時の動作 |
| `minimum_confidence` | default `high`。このlevel未満の数値だけでblockしない |
| `unknown_behavior` | default `warn`。`ignore`でもJSONからunknownを削除しない |
| privacy fields | SQL本文を含めるoptionは存在しない |

Frequency priority:

1. `.queryspend.yml` の exact model `unique_id`
2. head/base nodeの `config.meta.queryspend.runs_per_month`
3. `default_runs_per_month`
4. missing → `unknown_frequency`

複数sourceで値が異なる場合は優先順位を適用し、`frequency_overridden` evidenceを記録する。NaN、Infinity、負値、numeric YAML floatは拒否し、quoted decimalを案内する。

### 6.2 Zero-config behavior

configなしでもmanifest diffとdry-run bytesは動く。price/frequencyを推測しないため、recurring USDは `unknown` になり、checkはdefaultでblockしない。これは「動くdefault」と「false precisionを出さない」の両立である。60秒quickstartは完全offlineの `queryspend demo` が担う。

## 7. Input artifact contract

### 7.1 Supported dbt manifest

- dbt manifest schema v10、v11、v12
- dbt Core生成物と、dbt Cloudからdownloadした同schema artifactを同等に扱う
- `metadata.dbt_schema_version` でversionを判定し、未記載・未知versionはconfig/input errorにせず `unsupported_manifest_version` global diagnostic + code 2
- base/headが別supported versionでも内部v1へnormalizeする
- `metadata.adapter_type` が存在する場合は `bigquery` 必須。不一致はglobal unsupported

各model nodeに必要なfield:

- `unique_id`, `resource_type`, `package_name`, `name`
- `config.materialized`, optional `config.meta`
- `depends_on.nodes` またはmanifest `parent_map`
- `compiled_code`（旧schemaで同義fieldがある場合normalizerで変換）
- `database`, `schema`, `alias`
- `checksum`

`compiled_code` がない artifact（例: parse-only）はnode-level `missing_compiled_sql`。raw source fileを探してcompileしない。

### 7.2 In-scope nodes

- `resource_type == model`
- materialization `table` または `view`
- root project model。installed package modelはlineage traversalには使うが、MVPではcost contributorにしない
- enabled nodeのみ

tests、sources、seeds、snapshots、exposures、metricsはlineage evidenceとして参照できるがcost evaluationしない。

### 7.3 Semantic change detection

各nodeのfingerprintは、次をcanonical JSON化してSHA-256する。

- normalized `compiled_code` hash（SQL本文はfingerprint artifactへ保存しない）
- `checksum`
- `config.materialized`
- `database`, `schema`, `alias`
- sorted direct model/source dependencies

changed条件:

- headにのみ存在: `added`
- baseにのみ存在: `deleted`
- 同一unique_idでfingerprintが違う: `modified`
- materializationが変わった: `materialization_changed`。MVPではestimate全体をunknownにする

affected setは、changed nodeと、base graphまたはhead graphのどちらかでそのdescendantになるmodelのunion。順序はtopological、同rankは`unique_id` lexicalでdeterministicにする。cycleはinvalid artifact。renameは自動推測せずdelete + addとして表示する。

## 8. BigQuery dry-run contract

### 8.1 Hard safety invariant

すべてのAPI requestで `dry_run=True` と `use_query_cache=False` を設定する。query resultをfetchしない。load、extract、copy、DDL、DML、script、routine invocationの実行経路を実装しない。このinvariantに反するcode pathはtest failureでありrelease blocker。

SQL textはcost計算のためuserのBigQuery projectへ送られるが、queryspend maintainerのserverへ送られない。

### 8.2 Request / response evidence

各side/modelごとに次を取得する。

- `total_bytes_processed`
- BigQuery location
- statement type（利用可能な場合）
- distinct referenced tables（利用可能な場合。reportにはcountのみdefault保存）
- referenced tableのtype / clustering metadata（権限がある場合にmetadata APIで取得し、data rowは取得しない）
- provider request timestamp、latency、sanitized error code
- SQL SHA-256

SQLが単一のquery statementでない、BigQueryがqueryとしてvalidateしない、external/federated tableで0 bytes lower-boundになる可能性がある場合は数値をknownにしない。

### 8.3 Retry / concurrency

- default concurrency 4、model orderに関係なくfinal reportはdeterministic sort
- 429と5xxのみ exponential backoff + jitterで最大3attempt
- 400 syntax/location errorはretryしない
- 401/403はauth/permission class。global credential問題はcode 4、特定datasetだけならnode unknownとして継続
- per-request timeout 30秒、global timeout 10分
- 同一run内で `(billing_project, location, sql_sha256)` をmemory cacheする。cross-run persistent cacheはMVP外

## 9. Calculation model

### 9.1 Terms

- `raw_bytes_side`: BigQuery dry-run `total_bytes_processed`
- `table_count_side`: distinct referenced table count。取得不能ならnull
- `estimated_billed_bytes_side`: on-demand minimum billingを近似した値
- `runs_side`: explicit `runs_per_month`
- `price`: explicit `price_per_tib_usd`
- `TiB = 2^40 bytes`, `MiB = 2^20 bytes`

### 9.2 Minimum billing approximation

BigQuery on-demandはquery単位と参照table単位にminimumがある。MVPの近似は次とする。

```text
if raw_bytes == 0 and table_count == 0:
    estimated_billed_bytes = 0
elif table_count is known:
    estimated_billed_bytes = ceil_to_MiB(max(raw_bytes, 10 MiB, table_count * 10 MiB))
else:
    estimated_billed_bytes = ceil_to_MiB(max(raw_bytes, 10 MiB))
    add reason referenced_table_count_unknown
```

この近似は請求再現を保証しない。clustered tableではdry-runが上限になり得る。external/federated sourceは0 bytes lower-boundになり得るためunknownにする。free tierはorg全体で共有されPRへ配賦できないため差し引かない。

### 9.3 Materialization rules

| Case | Rule |
|---|---|
| `table` -> `table` | base/head compiled SELECTをそれぞれdry-runし、build1回のbytes差を計算 |
| added `table` | base bytes/runs = 0。headがknownならpositive estimate |
| deleted `table` | head bytes/runs = 0。baseがknownならnegative estimate |
| `view` unchanged | view creation自体のanalysis costは0。direct recurring deltaは0 |
| added/deleted/modified `view` | direct build costは0だがconsumer scan impactは`unknown_view_consumer_cost`。known totalをcompleteとしない |
| table↔view | `unknown_materialization_transition`。0やfull deltaへ推測しない |
| downstream model with unchanged SQL | lineage evidenceには載せる。upstream output size/view semanticsの変化をdry-runが再現できないため`unknown_downstream_data_shape`; 0 deltaとしてcomplete集計しない |
| incremental/ephemeral/other | `unsupported_materialization` |

downstreamを表示することと、downstream costを推定できたと主張することを分離する。MVPのBigQuery dry-runはhead relationを作成しないため、変更viewや変更tableの将来output sizeを既存production relation上で再現できない。

### 9.4 Per-node formula

両sideがknownな `table` model:

```text
base_monthly_bytes = estimated_billed_bytes_base * runs_base
head_monthly_bytes = estimated_billed_bytes_head * runs_head
monthly_bytes_delta = head_monthly_bytes - base_monthly_bytes
monthly_cost_delta_usd = monthly_bytes_delta / 2^40 * price_per_tib_usd
```

金額は内部Decimal、JSONでは小数点以下6桁のdecimal string、human outputではUSD centsへround-half-evenする。負値はsaving estimate、正値はincrease estimate、0はno known direct change。合計前にmodel別roundをしない。

`known_monthly_delta_usd` はknown modelだけのsubtotalである。unknownが1件でもcost-bearing affected setに存在すれば `summary.complete=false` とし、UIは `Known subtotal` と表示して `Total` と呼ばない。

### 9.5 Attribution

各contributorは次を持つ。

- dbt unique_id / optional display name
- change type、affected reason (`changed | downstream`)
- base/head materialization、runs、dry-run bytes、estimated billed bytes
- monthly bytes/cost delta（known時のみ）
- confidence、status、reason codes
- evidence hashes。SQL本文なし

最大contributorはabsolute known monthly cost deltaでsortし、同値はunique_id。正負を相殺するnet subtotalに加え、gross increaseとgross decreaseを別表示する。

## 10. Confidence、unknown、unsupported、error

### 10.1 Status vocabulary

| Status | Meaning | Numeric contribution |
|---|---|---|
| `known` | supported inputsから計算できた。ただしestimateでありinvoiceではない | subtotalへ含む |
| `unknown` | scope内に見えるが、信頼条件不足で数値を主張できない | 含めない |
| `unsupported` | 明示的にMVP外のprovider/materialization/query/data source | 含めない |
| `error` | auth、artifact、provider、internal failure | 含めない。globalならnonzero exit |

0 bytes、0 USD、negative costは `unknown` の代用品にしない。JSONのunknown numeric fieldは`null`。

### 10.2 Deterministic confidence

Confidenceは確率ではなくevidence completeness label。

**High:** supported table、必要sideのcompiled SQL、explicit model frequency、explicit user price、dry-run成功、statement/query source supported、referenced table count known、location一意、downstream-onlyでない。

**Medium:** added/deleted tableで一方のsideのみ存在する、またはreferenced table countが取得不能だがraw bytesはnonzero。minimum approximation reasonを必ず付ける。

**Low:** known numeric estimateはあるがclustered-table upper-bound等のprovider caveatが検出された。default policyはlowだけでblockしない。

**Unknown:** frequency/price/SQL欠落、view consumer、downstream data shape、external source、unsupported materialization、dry-run failureなど。

aggregate confidenceはknown contributorの最小値。known contributorがなければ`unknown`。

### 10.3 Required reason codes

最低限、次をstable enumにする。

```text
missing_compiled_sql
unknown_frequency
unknown_price
unsupported_manifest_version
unsupported_adapter
unsupported_materialization
unknown_materialization_transition
unknown_view_consumer_cost
unknown_downstream_data_shape
external_source_estimate_unavailable
referenced_table_count_unknown
location_mismatch
dry_run_syntax_error
permission_denied
rate_limit_exhausted
provider_timeout
no_changed_models
```

reasonにはsafeなremediation textを対応させる。BigQuery error message中のSQL断片、literal、relation名はdefault logへ転記しない。

## 11. Policy semantics

Policy evaluatorはproviderやrendererから独立したpure function。

1. threshold未設定: `warn` if unknown exists, otherwise `pass`
2. known eligible deltaがthreshold超過し、超過を成立させるcontributorが`minimum_confidence`以上:
   - `action: block` → `block`
   - `action: warn` → `warn`
3. known subtotalはthreshold以下だがunknownが存在:
   - `unknown_behavior: warn` → `unknown`（exit 0）
   - `block` → `block`（messageは`blocked by unknown policy`で金額超過と区別）
   - `ignore` → `pass`だがunknown countを表示
4. confidence不足のestimateがthresholdを超える: `warn`。blockしない
5. negative deltaはpositive thresholdを消費しない。gross increase thresholdはpositive contributors合計へ適用し、savingとの相殺でblockを回避させない

USD thresholdとbytes thresholdの両方が設定され、どちらかがblock条件ならblock。decisionには評価したthreshold、actual known value、confidence、unknown countを保存する。

## 12. Output contracts and accessibility

### 12.1 Terminal

先頭6行以内に次を出す。

```text
QUERYSPEND — ESTIMATE, NOT AN INVOICE
Decision: WARN (unknown downstream impact)
Known monthly increase: +$412.38/month
Coverage: 3 known / 5 affected; 2 unknown
Confidence: medium
Largest known contributor: model.analytics.fct_orders (+$390.10/month)
```

- statusを色だけで伝えない。`PASS/WARN/BLOCK/UNKNOWN` labelと説明を併記
- positive/negative sign、USD/month、bytes/monthのunitを省略しない
- `NO_COLOR`、non-TTY、`TERM=dumb`ではANSIを出さない
- ASCIIでも意味が保たれ、emojiをsemantic markerに使わない
- tableは120 column以内を目標にし、長いunique_idはmiddle truncateしてfull valueをJSONへ残す
- contributorはdefault上位10件、残件数を表示。`--format json`で全件を得る
- progress spinnerはstderr/TTYのみ。screen readerやCI logでは`Dry-running 3/8: <model>`のplain lineを使う

### 12.2 GitHub PR comment / job summary

- heading、decision、known subtotal、coverage、confidence、thresholdを最初に置く
- `<details>`にmodel evidenceとreason codeを置き、最重要判断をcollapseしない
- Markdown tableは `Model | Change | Monthly delta | Confidence | Status` の5列以内
- `+`/`-`、text label、数値を併記し、red/greenやiconだけに依存しない
- unknownは `Unknown — <reason>` と表示し `$0` にしない
- raw SQL、SQL snippet、literal、credential、full BigQuery errorは表示しない
- commentが長すぎる場合は上位10件 + unknown全reasonのcountを表示し、full JSON artifact pathを示す

### 12.3 JSON Cost Change Manifest v1

Top-level shape:

```json
{
  "schema": "https://queryspend.dev/schemas/report/v1.json",
  "schema_version": 1,
  "run": {
    "id": "uuid",
    "started_at": "RFC3339",
    "duration_ms": 1234,
    "queryspend_version": "0.1.0"
  },
  "inputs": {
    "base_manifest_sha256": "...",
    "head_manifest_sha256": "...",
    "dbt_manifest_versions": [11, 12],
    "provider": "bigquery",
    "billing_model": "on_demand",
    "location": "US",
    "price_per_tib_usd": "6.250000"
  },
  "summary": {
    "affected_models": 5,
    "known_models": 3,
    "unknown_models": 2,
    "complete": false,
    "known_monthly_bytes_delta": "72567767433216.000000",
    "known_monthly_delta_usd": "412.380000",
    "gross_monthly_increase_usd": "430.000000",
    "gross_monthly_decrease_usd": "-17.620000",
    "confidence": "medium"
  },
  "policy": {
    "decision": "warn",
    "reason": "unknown_models_present",
    "thresholds": {}
  },
  "models": [],
  "diagnostics": [],
  "privacy": {"sql_included": false}
}
```

Rules:

- byte count before multiplicationはinteger。fractional monthly byteはDecimal string
- moneyはDecimal stringまたはnull
- model objectは§9.5のfieldとbase/head evidenceを持つ
- enum未知値をconsumerが無視できるforward-compatible設計にするが、required field欠落はschema failure
- raw SQLを保存するfieldはschemaに存在しない
- schema v1変更はadditiveのみ。breaking changeはv2 URLとmajor versionを使う
- 同じnormalized input、config、mock provider responseから、timestamp/run id以外はbyte-for-byte deterministic

## 13. Security、auth、privacy、compliance

### 13.1 BigQuery least privilege

推奨専用principal:

- billing/job project: `roles/bigquery.jobUser`（`bigquery.jobs.create`）
- referenced dataset/table/view: dataset-level `roles/bigquery.dataViewer`。project-wide grantをdefault docsにしない
- routineを参照する場合は必要routineへのData Viewer。connection、reservation、billing account権限は付与しない
- `roles/editor`、`roles/owner`、BigQuery Admin、long-lived JSON keyをquickstartで要求しない

組織がより狭いcustom roleを使う場合は少なくとも実際のdry-runに必要な `bigquery.jobs.create` と参照resource metadata/data query permissionを含める。permission不足は必要permissionとresource classだけを表示し、SQLを表示しない。

### 13.2 GitHub OIDC

- Google Workload Identity Federation + dedicated service accountを推奨
- workflow permissionsは `contents: read`, `id-token: write`。commentするsame-repo PRのみ `pull-requests: write`
- provider attribute conditionをrepository ID / owner IDとevent/refへ制限する。pool全identityを無条件trustしない
- auth actionとqueryspend Actionはrelease tagだけでなくfull commit SHA pinの例をREADMEに載せる
- `pull_request_target`でPR code/artifactを処理しない
- default exampleはunprivileged `pull_request` artifact producer → default-branch `workflow_run` evaluatorの二workflow構成。evaluatorはupstream runが対象workflow名・conclusion success・期待repository/eventであることを検証する
- privileged evaluatorはdownloadしたmanifest/SQLを実行・source・importせず、YAML/JSON dataとしてsize limit付きでparseし、BigQuery dry-runにだけ渡す
- fork PRはdefaultでcloud authとcommentをskipし、maintainer承認後のsame-repo branchまたはmanual safe workflowを案内する
- service-account key fallbackはlocal userが明示的にADCへ設定済みの場合のみ利用可能とし、Action inputやconfigにsecret fieldを設けない

### 13.3 SQL / secret privacy

- SQLはrunner memoryとuser BigQuery API間だけ。maintainer endpoint、telemetry、crash reportへ送信しない
- report/log/commentにはSQL全文・snippet・literalを含めない。`sql_sha256`のみ
- relation nameはdefault false、model nameはdefault true。model名も機密ならprivacy optionでstable per-run hashへ置換可能
- environment variableをdumpしない。ADC credential path/content、GitHub token、OIDC tokenをlogしない
- temp fileは必要最小限、owner-only permission。reportはSQLを含まない
- BigQuery errorをallowlist codeへnormalizeし、provider raw messageはdefault破棄。debugでもSQL/literalをredactする
- analytics/telemetryはdefault off。MVPはnetwork telemetry codeを持たない
- customer artifactやvalidation observationに個人情報を含めない。repo/model identifiersは顧客同意なく公開benchmarkへ使用しない

### 13.4 Untrusted input

manifestとconfigをuntrusted inputとして扱う。

- YAML safe loaderのみ。object construction tag禁止
- path traversal、symlink escapeを避ける。Actionはworkspace配下のexplicit pathのみ読む
- manifest size default 100 MiB、node数100,000、compiled SQL 1 modelあたり2 MiBを上限とし、超過は明示error
- SQLは常にdry-run。queryspend自身がshellへSQLやmodel名を連結しない
- Markdown/terminal renderingでHTML、control character、ANSI escape、GitHub command injectionをescapeする

## 14. User stories and acceptance criteria

### US-1: Credentialなしで価値を理解する

As an analytics engineer, I want a one-command demo so that I can judge the output before granting warehouse access.

- Given Python 3.11+ とinternet package accessだけがある clean machine、When `pipx run queryspend demo`、Then 60秒以内にsimulated PR cost reportが表示される
- Given demo output、Then `SIMULATED DEMO` と `not a live estimate` が画面上部にあり、実測と誤認できない
- Given credential/network unavailable after install、Then demoはbundled dataだけで成功する

### US-2: base/head artifactからchanged/lineageを特定する

As a PR author, I want queryspend to identify changed and downstream models so that the report explains scope.

- Given supported base/head manifestでcompiled SQLが変わったmodel、When check、Then change type `modified` とfingerprint evidenceが出る
- Given added/deleted model、Then各々`added`/`deleted`になる
- Given changed modelのdescendantがbaseまたはhead graphにのみ存在、Then affected setに1回だけ含まれ、`downstream` reasonが付く
- Given no semantic changes、Then decision `pass`、reason `no_changed_models`、0 affected、BigQuery call 0件
- Given graph cycle、Then code 2で終了しcycle pathをSQLなしで示す

### US-3: BigQueryを実行せずdry-runする

As a security-conscious platform engineer, I want estimates without executing queries.

- Given any supported model、When provider is invoked、Then every request has `dry_run=true` and `use_query_cache=false`
- Given integration test project audit logs、Then queryspendからresult-producing query、DDL、DML、load、extract、copy jobが0件
- Given valid SQL、Then response bytes、location、latency、SQL hashがevidenceに残り、query result rowは取得されない
- Given external source 0-byte lower bound、Then numeric cost is null and reason `external_source_estimate_unavailable`

### US-4: recurring monthly deltaを誠実に計算する

As a reviewer, I want monthly estimates with assumptions so that I can distinguish evidence from guesswork.

- Given table model、both dry-runs、explicit monthly frequency、explicit price、When check、Then §9 formulaと一致するbytes/cost deltaをDecimalで返す
- Given price missing、Then dry-run bytesは表示しUSD fieldはnull、reason `unknown_price`
- Given frequency missing、Then per-run bytesは表示しmonthly fieldはnull、reason `unknown_frequency`
- Given modified view、Then direct view build $0をtotal cost changeと主張せず`unknown_view_consumer_cost`
- Given unchanged downstream SQL、Then future data shapeを0 deltaと推測せず`unknown_downstream_data_shape`
- Given any unknown contributor、Then summary label is `Known subtotal`, `complete=false`
- Given gross increaseとsavingが同時にある、Then gross valuesとnet known subtotalの算術が一致する

### US-5: thresholdで安全に判定する

As an analytics lead, I want a deterministic budget policy so that high-confidence regressions can block merge.

- Given eligible high-confidence gross increaseがUSD threshold超過し`action:block`、Then decision block、exit 3
- Given low-confidence estimateだけが超過、Then default decision warn、exit 0
- Given unknownがあるがknown subtotalはthreshold以下、Then default decision unknown/warn、exit 0
- Given `unknown_behavior:block`、Then block reasonは金額超過ではなくunknown policyと明記する
- Given saving contributor、Then positive thresholdから相殺しない
- Given same report/config、Then CLI、Python API、Actionは同一decisionを返す

### US-6: GitHub PRで可読な結果を得る

As a reviewer, I want one stable PR comment and check so that cost evidence stays in the review flow.

- Given same PRで再実行、Then marker付きcommentをupdateしduplicateを作らない
- Given fork/read-only token、Then comment failureでcost evaluationをfailureにせずjob summaryとJSONを残す
- Given block、Then check `queryspend/cost`はfailureでthreshold、known increase、confidence、reasonを表示
- Given unknown、Then `$0`やgreen-only表示をせず `UNKNOWN` labelと理由を表示
- Given long report、Then最重要summaryはcollapseせず、table 5列以内、full artifactへのpathを示す

### US-7: machine-readable artifactを利用する

As a tool integrator, I want a stable JSON schema so that I can automate checks without parsing prose.

- Given completed/partial/block evaluation、Then v1 schema-valid JSONがatomic writeされる
- Given JSON、Then raw SQL、credential、provider raw errorは含まれない
- Given same normalized inputs/mock evidence、Then run id/timestamp以外はdeterministic
- Given schema v1 consumer、Then unknown additive fieldを無視してrequired decision/model fieldsを読める

### US-8: least privilegeで認証する

As a platform owner, I want OIDC and narrow BigQuery roles so that no long-lived key or write access is required.

- Given GitHub OIDC config、Then service-account JSON keyなしでADCが解決する
- Given only project Job User + referenced dataset Data Viewer、Then supported dry-run completes
- Given missing permission、Then code 4またはnode unknownとなり、必要permission classをSQLなしで示す
- Given docs/workflow example、Then `pull_request_target`、Editor/Owner/Admin role、unpinned third-party Actionを含まない

### US-9: validation metricsを再現する

As the venture team, I want prediction and observation artifacts so that the 7/90-day decision is auditable.

- Given predictionsと§15 observation、When `queryspend validate`、Then eligible/excluded count、median APE、p90 APE、attribution、false blockerを返す
- Given actual delta 0、Then APEへdivision-by-zeroで含めず、absolute errorとfalse blocker母集団へ含める
- Given10 PRでfalse blocker1件、Then false blocker 10%でgate fail
- Given unknown prediction、Then error metricから黙って除外せずcoverage/attributionの未達へ反映する
- Given metric threshold未達、Then validation decision failと各failed criterionを出す

## 15. Validation-first protocol and instrumentation

### 15.1 Seven-day technical truth

Minimum corpus:

- 3 public/synthetic dbt BigQuery projects
- 10 PR scenarios、各scenarioはone principal cost changeを持つ
- `table`/`view`、partition filter add/remove、column projection、join expansion、added/deleted table、view consumer unknownを含む
- positive/negative/zero actual deltaを含む
- benchmark query/data version、region、price、frequency、observation timestampをfreezeする

queryspendはproduction queryを自動実行しない。validation ownerが隔離projectでbase/headを実際にscheduled runし、BigQuery job statisticsからtruth artifactを作る。

Observation JSONL per PR/model:

```json
{
  "schema_version": 1,
  "case_id": "retail-remove-partition-filter",
  "model_unique_id": "model.retail.fct_orders",
  "policy_threshold_usd": "100.000000",
  "actual_monthly_delta_usd": "640.000000",
  "actual_monthly_bytes_delta": "112589990684262.400000",
  "actual_runs_per_month": "30",
  "ground_truth_attributed": true,
  "source": "bigquery_job_statistics",
  "observation_window_days": 7
}
```

### 15.2 Exact metric definitions

**Eligible APE case:** actual monthly deltaがnonzeroで、absolute actual delta ≥ `$10.00`、observationがcomplete。小さいcaseを捨てた件数とabsolute errorを別表示する。

```text
APE_i = abs(predicted_i - actual_i) / abs(actual_i) * 100
median error = median(APE_i)
p90 error = nearest-rank percentile(APE_i, 90)
```

Prediction unknownはAPEから除外するが成功扱いにせず、attribution denominatorには残す。APE eligible known caseが8件未満ならsample不足でgate fail。

**Cost-weighted attribution:** ground truth modelのabsolute actual monthly deltaをweightとし、同じmodel unique_idにknown predictionがあり、nonzeroのsignが一致したweightの合計 / 全ground-truth weight。unknown、wrong model、wrong signはnumerator 0。

**False blocker:** actual gross increaseがpolicy threshold以下のPRに対し、queryspendがmoney/bytes threshold理由で`block`した件数 / actual non-block PR数。`unknown_behavior:block`による意図的blockとoperational errorは別metricとして報告しmoney false blockerに混ぜない。

**Coverage:** known cost-bearing ground-truth model数 / 全cost-bearing ground-truth model数。unknown/unsupportedを分母から除外しない。

### 15.3 Required local events

外部送信はしない。report/validation artifactに次のevent相当fieldを記録し、design partnerがopt-inでartifactを共有した場合のみ集計する。

| Event | Trigger | Required properties |
|---|---|---|
| `check_started` | inputs validated | run_id、manifest versions、affected count |
| `dry_run_completed` | model side completed | provider、status、latency_ms、bytes bucket、reason code。SQLなし |
| `check_completed` | report finalized | duration、known/unknown count、decision、confidence |
| `policy_blocked` | decision block | threshold type、known value、reason、confidence |
| `comment_published` | comment update success | same/fork repo flag、update/create、no repo name |
| `validation_evaluated` | validate command | corpus size、all metric values、gate decision |

No stable machine identifier、user email、SQL、repo URLをanonymous eventとして生成しない。90日集計に必要なrepo/customer mappingはdesign partner registry側で同意のもと管理し、本OSS coreのtelemetryに入れない。

### 15.4 Day 60 / Day 90 metric definitions

| Metric | Definition | Evidence |
|---|---|---|
| Evaluated PR | distinct repo + PR number + head SHAでcompleted report 1件。rerunは重複除外 | shared report index |
| Setup time | install開始から最初のreal PR `check_completed`まで。self-report開始時刻 + artifact | onboarding log + report |
| Required check adoption | branch protectionで`queryspend/cost` requiredのrepo | owner screenshot/API export、同意時のみ |
| Repeat-active repo | 28日windowの異なる2週に各1 PR以上、合計4 PR以上 | deduplicated reports |
| Production user | default branch required、3 production model/20 PR、4週間、threshold/waiver、merge decision evidenceの全条件 | partner checklist |
| False blocker | §15.2、100 PR以上でも継続計測 | observation join |

Targets:

- Day 31–60: 3 design partners、100 PR、false blocker≤5%、setup median≤15分、2社でrequired check 2週間、paid pilot intent 2社
- Day 61–90: paid pilot 3社、production definition達成2社、合計200 PR、repeat-active repo 25、non-author issue/discussion participant 10、external contributor 3、merge decision changed 1社

## 16. States and edge cases

### 16.1 Surface states

| Surface | Loading | Empty / first run | Success | Partial / unknown | Error / permission | Offline |
|---|---|---|---|---|---|---|
| `demo` CLI | no spinner required | bundled scenario always exists | simulated report | n/a | corrupt package → code 6 | works after install |
| `check` terminal | TTY stderr progress | no changes → pass + reason、0 API calls | summary + contributors | known subtotal + unknown reasons | typed error + remediation + report path | provider unavailable → retry then code 5; no stale estimate |
| JSON output | n/a | schema-valid empty models | schema-valid | null numeric + diagnostics | partial diagnostic when possible | same as provider error |
| GitHub Action | step log plain progress | success check `No cost-affecting model changes` | check/comment update | success/warn or policy block | failure with safe remediation | failure; never reuse previous PR result as current |
| `validate` | plain file count | zero predictions/observations → code 2 | metrics + gate | excluded/unknown counts explicit | schema mismatch with file/line | local files only |

### 16.2 Edge cases

- base/head同じpathまたはhash: no-change pass、warning `identical_inputs`
- manifest schema supportedだが`compiled_code`なし: affected node unknown、全対象欠落ならcode 2 remediation `run dbt compile`
- model rename: delete + add。rename confidenceを推測しない
- frequency 0: intentionally disabled schedule。monthly build cost 0としてknown、sourceをevidence化
- frequency changed only in config: model semantic diffがなくてもfrequency diffはcost change。base/head別frequencyをMVP configで表せないため、v1は単一current frequencyを両sideへ適用し`frequency_change_not_modeled`。frequency change PR自体はunsupported
- price 0、negative、NaN、Infinity: config error。free tierを0 priceで表現しない
- huge positive/negative Decimal: overflowせずschema上限超過をconfig error
- duplicate unique_id、missing graph node、cycle: artifact error
- package dependency model changed: graph impactは表示し、root project policy対象外ならunknown reason
- multiple BigQuery locations in one SQL、location mismatch: node unknown
- authorized view/routine、wildcard/external table、remote function: providerが安全に分類できない場合unknown
- partition/clustering metadata変化がhead artifactにあるがproduction tableへ未反映: output-size/storage effectはunknown
- SQL comment/literalにsecretがある: BigQueryへは送られるがreport/logへ出さない。queryspendはsecret scannerではない
- BigQuery 429/5xx partial failure: successful models保持、failed model unknown、retry exhaustion reason
- Ctrl-C/cancel: temp outputをrenameせず、exit 130、credential cleanupを妨げない
- two Action runs concurrently: comment markerでlatest head SHAだけupdate。古いSHA runはcomment上書きせずjob summaryのみ
- GitHub API rate limit/comment too long: evaluation decisionを維持し、job summary + artifactへfallback
- JSON output path existing: temp file + fsync + atomic replace。既存fileを途中状態にしない

## 17. Demo and fixture strategy

### 17.1 Credential-free demo

架空の `northstar_retail` dbt projectを同梱する。

- PR: `fct_orders` のpartition filterを削除
- base: 1.2 TiB/run、head: 4.8 TiB/run
- frequency: 30 runs/month
- price: explicit fixture value。値は「fixture price」でありcurrent list priceと主張しない
- changed table 1、downstream table 2、modified view 1
- output: large known contributor 1、saving 1、view/downstream unknown 2、policy warn/blockの根拠が一画面で分かる

Recorded responseには `fixture=true` を持たせ、live reportと混同できない。README screenshot/GIFもdemo labelをcropしない。

### 17.2 Validation corpus

3 project:

1. `northstar_retail`: partition filter、column projection、added/deleted table
2. `harbor_marketplace`: join fanout、source scan増減、clustered upper-bound
3. `lumen_saas`: view change、downstream unknown、materialization transition unsupported

10 PR scenarioはbase/head manifest、config、recorded dry-run、live validation script instructions、observation template、expected reason/decision goldenを持つ。synthetic table生成SQLはvalidation repo内に置けるが、queryspend本体は自動実行しない。demo値をaccuracy benchmarkへ流用しない。

## 18. Testing and release gates

### 18.1 Unit / property tests

- manifest v10/v11/v12 normalize golden
- fingerprintがkey order/whitespace normalizationにdeterministic、semantic SQL changeで変化
- graph union descendants、add/delete、cycle、100k node limit
- §9 formula、MiB/TiB conversion、rounding、gross/net、0/negative、very large Decimal
- all confidence/status/reason transitions
- policy truth table全組合せ。unknown default non-blockを必ずtest
- terminal/Markdown escaping、`NO_COLOR`、control chars、long IDs
- report JSON schema、no field containing raw SQL
- validation APE/p90 nearest-rank/attribution/false-blocker/zero denominator

### 18.2 Provider contract tests

Fake providerで次を再現する。

- success、0 bytes、table count null、cluster caveat
- 400、401、403 dataset-specific、429 retry、500 retry、timeout
- assert every request `dry_run=True`, `use_query_cache=False`
- exception/log snapshotにSQL/literalがない

### 18.3 Live BigQuery integration

maintainer-owned isolated on-demand project + public/synthetic datasetでnightly/manual実行する。

- ADC user auth と GitHub OIDC の両方
- least-privilege roleでdry-run成功
- audit logでwrite/data-modifying job 0
- known queryの`total_bytes_processed`がrecorded contractと許容範囲内
- permission/location/external source case

live testはPR from forkで走らせない。credentialなしPR CIはfake/golden testsのみ。

### 18.4 Non-functional acceptance

- 100 affected model、mock provider latency除外でcore evaluation p95 <5秒
- BigQuery call concurrency default 4、global timeout 10分
- clean install demo <60秒
- setup median≤15分はDay 60 product metricでありunit performanceと混同しない
- core package statement coverage ≥90%、policy/estimator/confidence 100% branch coverage
- supported Python全version、Linux/macOS。WindowsはCLI unit test範囲、GitHub ActionはLinuxのみ
- dependency lock/SBOM、secret scan、High以上security finding 0がGate C条件

### 18.5 Release acceptance checklist

- [ ] 7日technical gate全指標を`validation-report.json`でpass
- [ ] `queryspend demo`がcredentialなし60秒以内
- [ ] manifest v10–v12 contract test pass
- [ ] SQL実行pathなし、dry-run invariant test pass
- [ ] table/view/unknown/materialization transition golden pass
- [ ] CLI/API/Action decision parity pass
- [ ] terminal、Markdown、JSON accessibility/privacy review pass
- [ ] OIDC least-privilege live test pass、long-lived keyなし
- [ ] desktop/mobile screenshot gateはN/A（Web UIなし）。CLI logとGitHub comment goldenをreview
- [ ] unsupported/unknown一覧とaccuracy methodologyをREADMEに公開

## 19. Implementation and verification sequence

### Stage V — 7日 validation prototype

1. v1 normalized models/report/observation schemaとDecimal formulaを固定
2. 3 project / 10 PR fixtureを作成
3. minimal BigQuery dry-run providerとmanual base/head evaluatorを作る
4. 隔離projectで7日observationを収集
5. `queryspend validate`でexact metricsを算出
6. threshold全passならStage 1へ。未達なら原因別に `unknown` scopeを狭め再試験し、median>20%、p90>40%、attribution<80%、false blocker>10%ならTHESISのimmediate kill/pivotを適用

### Stage 1 — launchable OSS core（1〜3週間）

1. artifact normalizer + graph + config
2. provider hardening + estimator + confidence + policy
3. CLI/JSON/terminal + credential-free demo
4. GitHub Action + Markdown renderer + idempotent comment
5. security/privacy limits、golden/live tests、quickstart

Stage Vのために作ったunsafe shortcut、hard-coded fixture price、raw SQL loggingをStage 1へ持ち込まない。

### Verification commands expected from builder

```text
queryspend demo
queryspend check --base fixtures/northstar/base/manifest.json \
                 --head fixtures/northstar/head/manifest.json \
                 --config fixtures/northstar/queryspend.yml \
                 --output /tmp/queryspend-report.json
queryspend render --input /tmp/queryspend-report.json --format markdown
queryspend validate --predictions 'validation/predictions/*.json' \
                    --observations validation/observations.jsonl \
                    --output /tmp/validation-report.json
pytest
ruff check .
mypy queryspend
```

Gate B evidenceはterminal execution log、GitHub Action run log、PR comment golden/live screenshot相当を保存する。Web UI screenshotは不要。

## 20. Open questions with non-blocking defaults

| Question | Default decision for MVP |
|---|---|
| License | Apache-2.0。THESISのOSS境界に合わせる |
| Built-in BigQuery list priceを持つか | 持たない。user explicit priceがないUSDはunknown。demoだけfixture price |
| dbt manifest version範囲 | v10〜v12。未知versionをbest-effort parseしない |
| dbt Cloud scheduleを読むか | 読まない。artifactのみ、frequency explicit |
| modified viewのconsumer cost | unknown。temporary relation作成やSQL inliningをしない |
| downstream unchanged SQLを0と扱うか | 扱わない。data shape impact unknown |
| unknownでrequired checkをfailするか | defaultはwarn/exit 0。ownerの明示configのみblock |
| reportにrelation/model名を出すか | model名true、relation名false。SQLは常にfalse |
| anonymous telemetry | なし。opt-in共有artifactでvalidation |
| GitHub fork PR | auth/comment skip。`pull_request_target`は使用禁止 |

## 21. Definition of done

MVPがdoneと言えるのは、次をすべて満たすときだけである。

1. 7日technical gateをversioned observation/prediction artifactから再現し、4閾値をpassする。
2. BigQuery on-demand + dbt artifact + GitHub PRの一つのflowが、demo、CLI、Action、JSONで動く。
3. `table` estimateと`view`/downstream/unsupportedの境界が実装・docs・golden testで一致する。
4. unknownを0や確定額として表示せず、defaultではfalse blockerを生まない。
5. OIDC/ADC、least privilege、dry-run-only、SQL非保存をlive testとsecurity reviewで確認する。
6. 60秒以内のcredential-free quickstartと、real repo導入15分以内を測定できる。
7. 90日production/repeat usage指標をreport/partner evidenceから重複なく集計できる。

この条件を満たさずにwarehouse追加、Web UI、AI optimization、paid control planeへ進まない。
