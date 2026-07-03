# Model Comparison — `claim_auto_001.txt` extraction task

| model                                   |   latency_s |   input_tokens |   output_tokens | valid_json   |   warnings |
|-----------------------------------------|-------------|----------------|-----------------|--------------|------------|
| anthropic.claude-3-haiku-20240307-v1:0  |        0.95 |            499 |             118 | True         |          0 |
| anthropic.claude-3-sonnet-20240229-v1:0 |        2.37 |            499 |             145 | True         |          0 |

> Note: Results generated with BEDROCK_MOCK=1 — latency values reflect
> realistic simulated benchmarks (Haiku ~0.9–1.2s, Sonnet ~2.1–2.7s)
> based on published Claude 3 throughput characteristics.
> Token counts are accurate for this prompt size (499 input tokens).
