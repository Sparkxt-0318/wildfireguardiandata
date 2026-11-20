# Prior art: multi-temporal and sequential fire detection (track 51, live)

A short note so that nothing in `results/LIVE_RESULTS.md` reads as a "first". Searched 2026-11-20 (Consensus
paper search plus known references); not a systematic review.

## Using a pixel's own history (multi-temporal background)
- **RST / RST-FIRES** (Tramutoli and co-workers): each pixel is compared with its own multi-year statistics at the same
  time and month; RST-FIRES for MSG-SEVIRI was described and field-validated by
  [Filizzola et al. 2016](https://consensus.app/papers/details/w:b2ec0189-72d7-4404-94d1-5b93c930672b/) (Remote Sensing of
  Environment) and ported to rapid-scan geostationary data by
  [Falconieri et al. 2026](https://consensus.app/papers/details/w:c8157b65-ed6a-44f9-aa05-4c1c0e7c7470/).
- **GOES Early Fire Detection (GOES-EFD)**: Koltunov & Ustin (2007, RSE 110) predicted each pixel's thermal signal from
  its own multi-temporal series ("non-linear multitemporal prediction"); Koltunov et al. (2016, RSE 184) built and
  validated GOES-EFD on GOES-West imagery for early detection in California. Our background model (own history at the
  same clock time + same-frame neighbours) is in this family.
- **Diurnal-cycle models**: [Hally et al. 2018](https://consensus.app/papers/details/w:381e65f0-221f-453e-9055-6cfcf8b38ffe/)
  (multi-temporal detection for next-generation geostationary data);
  [Udahemuka et al. 2020](https://consensus.app/papers/details/w:9e1a8d86-6c60-4242-bbf2-020fb0bcfbdc/) (background
  temperature by data assimilation).
- **Spatio-temporal contextual tests on Himawari-8/9**:
  [Xie et al. 2018](https://consensus.app/papers/details/w:0899fe7e-9bd4-4f35-8f9f-ec9b66f821f5/),
  [Jang et al. 2019](https://consensus.app/papers/details/w:9fdcb9b1-ca58-4f02-b754-6c583e34a823/) (South Korea),
  [Engel et al. 2021](https://consensus.app/papers/details/w:6e3e71ac-83e9-4a37-9643-fb217a7db16f/),
  [Q. Zhang et al. 2023](https://consensus.app/papers/details/w:87e5c9f3-23a2-43fa-b7fc-739ec945ff2a/) (early-stage
  detection combining spatial, temporal and spectral information),
  [Liu et al. 2026](https://consensus.app/papers/details/w:290da1b0-e623-41f3-a6ba-4ec86e03c273/) (instantaneous plus
  historical contextual differences).
- **Learned models on geostationary time series**:
  [Zhao & Ban 2022](https://consensus.app/papers/details/w:64a0f601-83bb-46fd-8884-de709dc9fd78/) (GOES-R time series, GRU,
  early detection), [Kang et al. 2022](https://consensus.app/papers/details/w:7dfa63f3-d18e-413d-9700-1336a9224eef/)
  (reduced detection latency), [Vanunu et al. 2026](https://consensus.app/papers/details/w:e77cb6c2-57b3-4ed9-b2b1-61daf773e793/)
  (gradient boosting against GOES FDC).

## Sequential (accumulating) tests
- CUSUM is Page's (1954) test; reviews: [Xie et al. 2021](https://consensus.app/papers/details/w:7e273f8e-2b91-4950-9446-1bab52259ffc/).
  Window-limited CUSUM: [Xie et al. 2023](https://consensus.app/papers/details/w:8deaa880-44b8-4079-90b6-ab058894ebeb/).
  For signals that appear and disappear, a modified CUSUM is optimal and finite-moving-average detectors come close
  ([Tartakovsky et al. 2021](https://consensus.app/papers/details/w:9c61b56b-4572-473a-8440-8c8c428efaaf/)).
- Persistence over several geostationary frames is already used by operational and research products (e.g. temporal
  filtering in GOES FDC codes 30–35; multi-image confirmation in several Himawari methods above). Accumulating weak
  evidence over frames is therefore not new; what this track does is apply a per-pixel CUSUM with a threshold set from
  placebo series at a stated false-alert budget, and measure the lead against the operational product with strictly
  causal replay.

## Validation context
- Operational product accuracy against Landsat: [Hall et al. 2019](https://consensus.app/papers/details/w:f8804d21-686e-4e8c-b00a-99c5bdd8eb03/),
  [Hall et al. 2023](https://consensus.app/papers/details/w:de0f959e-02cb-4ffd-925d-9212473d9629/). Review:
  [Wooster et al. 2021](https://consensus.app/papers/details/w:7c1414a1-353e-4bf9-8c31-95fec92fb9f9/). Hourly GOES fire
  progression: [Liu et al. 2024](https://consensus.app/papers/details/w:161d9b23-3bc7-4016-9b6e-7cb85d610167/).

## What we do not claim
Not the first multi-temporal, first sequential, first two-satellite or first early geostationary detector. The claims
in results are limited to the numbers measured here (n, intervals, source files), on this protocol's fires and placebos.
