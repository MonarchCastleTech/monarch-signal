# Monarch Signal

An editorial economic outlook from Monarch Castle Technologies: current developments, observed market data, and written short-, medium- and long-term expectations.

Public product: https://monarchcastle.com/monarch-signal/
Standalone mirror: https://monarchcastletech.github.io/monarch-signal/

The reader does not enter a prompt, choose assumptions or adjust a simulation. The page publishes one current outlook, a three-horizon forecast timeline, developments that could change the outlook, other economic themes, and a chronological source-linked news record.

## Run

Python 3.11+ and Node 20+. No third-party runtime packages.

```sh
python -m unittest discover -s tests -v
python pipeline/refresh.py
npm run build
npm run preview
```

Open http://localhost:4178. Set `OPENROUTER_API_KEY` in the process environment for AI. The committed snapshot builds offline. `--no-ai` publishes the transparent topic-based editorial baseline.

## Free AI and secrets

Only `:free` models and the `openrouter/free` fallback router are requested. There is no paid fallback, search plugin or paid endpoint. Free-model availability and quotas apply. Identical evidence bundles reuse the validated analysis. A provider error or invalid response falls back to a source-linked editorial baseline. The actual model, generation time, cost field and origin are preserved in the downloadable snapshot.

Set the repository Actions secret `OPENROUTER_API_KEY` for automation. The key is used only by the runner; it is never embedded in frontend code or deployed data. Public headlines are sent to the selected OpenRouter provider. There is no visitor submission endpoint. Provider retention terms apply.

## Sources

| Layer | Source | Method |
| --- | --- | --- |
| News | BBC World/Business, DW World, Al Jazeera, ECB press | RSS titles, links and original publication times, trailing 72 hours |
| Brent | EIA via FRED `DCOILBRENTEU` | USD/barrel observations |
| US 10-year | Federal Reserve via FRED `DGS10` | Dated yields, percent |
| USD/TRY | ECB 90-day euro reference rates | Same-date TRY/EUR divided by USD/EUR |

GitHub Actions refreshes hourly, validates and commits the snapshot, builds and deploys GitHub Pages. The main Monarch website imports `web/` and `data/` from this repository in its existing hourly build. GitHub schedules may run late. Market data is published with source dates, not presented as live quotes.

Failed news feeds retain only dated items still inside the 72-hour window. Failed market feeds retain original observation dates and are labelled. A seven-day market-data staleness threshold and a six-hour publication warning protect freshness claims. A total source failure preserves the last release rather than fabricating values.

## Analytical boundaries

The barometer measures headline activity: each unique matching title contributes `exp(-ageHours/36)`, multiplied by 1.5 for an exact stress-word match. Pressure is `min(100, sum(weights)/12*100)`. It is not an event probability. Publisher-domain counts do not prove independent corroboration. Metaphors, source selection and topic overlap remain limitations.

The lead energy theme is selected when at least two energy headlines are available; otherwise the most active theme leads. AI receives source IDs, topic names and a conditional editorial baseline. Citation IDs, language, theme relevance and all three horizon IDs are checked before accepting a generated outlook. Original publication times, not generated dates, determine chronology. Valid citations do not guarantee every model assertion is correct.

Forecasts are conditional editorial judgments. No fitted price targets, calibrated probabilities or claimed backtest accuracy are published. The short horizon is the first two weeks; medium is two weeks to three months; long is three to twelve months. A future evaluation layer should archive resolution criteria and test forecasts out of sample before probability claims are introduced.

## Files

- `pipeline/refresh.py`: ingest, deduplication, health, scoring, free-only AI and atomic writes.
- `pipeline/topics.json`: topic dictionary and editorial baseline forecasts.
- `web/`: static editorial interface and SVG market charts, without visitor inputs.
- `data/snapshot.json`: sources, observations, editorial, AI provenance and daily history.
- `tests/`: freshness, deduplication, missing observations, same-day cross-rates, citation/language validation and free-only routing.
- `.github/workflows/`: scheduled publication and pull-request checks.
- `.openai/hosting.json`: optional private Sites mirror identity.

Original software: MIT. External content, data, fonts and marks retain upstream rights. See `THIRD_PARTY_NOTICES.md` before redistribution.
