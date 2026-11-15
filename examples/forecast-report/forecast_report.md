# Commercial forecast versus outcome report

## Observation provenance

```json
[
  {
    "commercially_successful": true,
    "evaluation": {
      "errors": {
        "cac": {
          "absolute_error": 20.0,
          "percentage_error": 0.09090909090909091,
          "signed_error": -20.0
        },
        "contribution_margin": {
          "absolute_error": 0.019999999999999907,
          "percentage_error": 0.029411764705882214,
          "signed_error": 0.019999999999999907
        },
        "conversion_rate": {
          "absolute_error": 0.020000000000000004,
          "percentage_error": 0.25000000000000006,
          "signed_error": 0.020000000000000004
        },
        "demand": {
          "absolute_error": 10.0,
          "percentage_error": 0.1111111111111111,
          "signed_error": 10.0
        },
        "gross_margin": {
          "absolute_error": 0.020000000000000018,
          "percentage_error": 0.025641025641025664,
          "signed_error": 0.020000000000000018
        },
        "implementation_cost": {
          "absolute_error": 2000.0,
          "percentage_error": 0.11764705882352941,
          "signed_error": -2000.0
        },
        "revenue": {
          "absolute_error": 1000.0,
          "percentage_error": 0.09090909090909091,
          "signed_error": 1000.0
        },
        "time_to_first_revenue_months": {
          "absolute_error": 1.0,
          "percentage_error": 0.2,
          "signed_error": -1.0
        },
        "time_to_launch_months": {
          "absolute_error": 1.0,
          "percentage_error": 0.25,
          "signed_error": -1.0
        }
      },
      "interval_coverage": 1.0,
      "interval_outcomes": {
        "revenue": true
      },
      "intervals_evaluated": 1
    },
    "evidence_source_ids": [
      "synthetic-outcome-source-1"
    ],
    "experiment_id": null,
    "measured_at": "2024-01-15T00:00:00+00:00",
    "opportunity_id": "synthetic-success",
    "outcome_id": null,
    "prediction_id": null,
    "recommendation": "BUILD",
    "run_id": "synthetic-run-1"
  },
  {
    "commercially_successful": false,
    "evaluation": {
      "errors": {
        "cac": {
          "absolute_error": 350.0,
          "percentage_error": 0.7,
          "signed_error": -350.0
        },
        "revenue": {
          "absolute_error": 3000.0,
          "percentage_error": 1.5,
          "signed_error": 3000.0
        }
      },
      "interval_coverage": 0.0,
      "interval_outcomes": {
        "revenue": false
      },
      "intervals_evaluated": 1
    },
    "evidence_source_ids": [
      "synthetic-outcome-source-2"
    ],
    "experiment_id": null,
    "measured_at": "2024-02-15T00:00:00+00:00",
    "opportunity_id": "synthetic-failure",
    "outcome_id": null,
    "prediction_id": null,
    "recommendation": "MORE_EVIDENCE",
    "run_id": "synthetic-run-2"
  }
]
```

## By run

```json
{
  "synthetic-run-1": {
    "currency": "USD",
    "errors_by_metric": {
      "cac": {
        "count": 1,
        "forecast_bias": -20.0,
        "interval_coverage": null,
        "mean_absolute_error": 20.0,
        "mean_percentage_error": 0.09090909090909091
      },
      "contribution_margin": {
        "count": 1,
        "forecast_bias": 0.019999999999999907,
        "interval_coverage": null,
        "mean_absolute_error": 0.019999999999999907,
        "mean_percentage_error": 0.029411764705882214
      },
      "conversion_rate": {
        "count": 1,
        "forecast_bias": 0.020000000000000004,
        "interval_coverage": null,
        "mean_absolute_error": 0.020000000000000004,
        "mean_percentage_error": 0.25000000000000006
      },
      "demand": {
        "count": 1,
        "forecast_bias": 10.0,
        "interval_coverage": null,
        "mean_absolute_error": 10.0,
        "mean_percentage_error": 0.1111111111111111
      },
      "gross_margin": {
        "count": 1,
        "forecast_bias": 0.020000000000000018,
        "interval_coverage": null,
        "mean_absolute_error": 0.020000000000000018,
        "mean_percentage_error": 0.025641025641025664
      },
      "implementation_cost": {
        "count": 1,
        "forecast_bias": -2000.0,
        "interval_coverage": null,
        "mean_absolute_error": 2000.0,
        "mean_percentage_error": 0.11764705882352941
      },
      "revenue": {
        "count": 1,
        "forecast_bias": 1000.0,
        "interval_coverage": 1.0,
        "mean_absolute_error": 1000.0,
        "mean_percentage_error": 0.09090909090909091
      },
      "time_to_first_revenue_months": {
        "count": 1,
        "forecast_bias": -1.0,
        "interval_coverage": null,
        "mean_absolute_error": 1.0,
        "mean_percentage_error": 0.2
      },
      "time_to_launch_months": {
        "count": 1,
        "forecast_bias": -1.0,
        "interval_coverage": null,
        "mean_absolute_error": 1.0,
        "mean_percentage_error": 0.25
      }
    },
    "interval_coverage": 1.0,
    "metric_count": 9,
    "observation_count": 1,
    "period_months": 1
  },
  "synthetic-run-2": {
    "currency": "USD",
    "errors_by_metric": {
      "cac": {
        "count": 1,
        "forecast_bias": -350.0,
        "interval_coverage": null,
        "mean_absolute_error": 350.0,
        "mean_percentage_error": 0.7
      },
      "revenue": {
        "count": 1,
        "forecast_bias": 3000.0,
        "interval_coverage": 0.0,
        "mean_absolute_error": 3000.0,
        "mean_percentage_error": 1.5
      }
    },
    "interval_coverage": 0.0,
    "metric_count": 2,
    "observation_count": 1,
    "period_months": 1
  }
}
```

## By opportunity

```json
{
  "synthetic-failure": {
    "currency": "USD",
    "errors_by_metric": {
      "cac": {
        "count": 1,
        "forecast_bias": -350.0,
        "interval_coverage": null,
        "mean_absolute_error": 350.0,
        "mean_percentage_error": 0.7
      },
      "revenue": {
        "count": 1,
        "forecast_bias": 3000.0,
        "interval_coverage": 0.0,
        "mean_absolute_error": 3000.0,
        "mean_percentage_error": 1.5
      }
    },
    "interval_coverage": 0.0,
    "metric_count": 2,
    "observation_count": 1,
    "period_months": 1
  },
  "synthetic-success": {
    "currency": "USD",
    "errors_by_metric": {
      "cac": {
        "count": 1,
        "forecast_bias": -20.0,
        "interval_coverage": null,
        "mean_absolute_error": 20.0,
        "mean_percentage_error": 0.09090909090909091
      },
      "contribution_margin": {
        "count": 1,
        "forecast_bias": 0.019999999999999907,
        "interval_coverage": null,
        "mean_absolute_error": 0.019999999999999907,
        "mean_percentage_error": 0.029411764705882214
      },
      "conversion_rate": {
        "count": 1,
        "forecast_bias": 0.020000000000000004,
        "interval_coverage": null,
        "mean_absolute_error": 0.020000000000000004,
        "mean_percentage_error": 0.25000000000000006
      },
      "demand": {
        "count": 1,
        "forecast_bias": 10.0,
        "interval_coverage": null,
        "mean_absolute_error": 10.0,
        "mean_percentage_error": 0.1111111111111111
      },
      "gross_margin": {
        "count": 1,
        "forecast_bias": 0.020000000000000018,
        "interval_coverage": null,
        "mean_absolute_error": 0.020000000000000018,
        "mean_percentage_error": 0.025641025641025664
      },
      "implementation_cost": {
        "count": 1,
        "forecast_bias": -2000.0,
        "interval_coverage": null,
        "mean_absolute_error": 2000.0,
        "mean_percentage_error": 0.11764705882352941
      },
      "revenue": {
        "count": 1,
        "forecast_bias": 1000.0,
        "interval_coverage": 1.0,
        "mean_absolute_error": 1000.0,
        "mean_percentage_error": 0.09090909090909091
      },
      "time_to_first_revenue_months": {
        "count": 1,
        "forecast_bias": -1.0,
        "interval_coverage": null,
        "mean_absolute_error": 1.0,
        "mean_percentage_error": 0.2
      },
      "time_to_launch_months": {
        "count": 1,
        "forecast_bias": -1.0,
        "interval_coverage": null,
        "mean_absolute_error": 1.0,
        "mean_percentage_error": 0.25
      }
    },
    "interval_coverage": 1.0,
    "metric_count": 9,
    "observation_count": 1,
    "period_months": 1
  }
}
```

## Portfolio

```json
{
  "portfolio": {
    "currency": "USD",
    "errors_by_metric": {
      "cac": {
        "count": 2,
        "forecast_bias": -185.0,
        "interval_coverage": null,
        "mean_absolute_error": 185.0,
        "mean_percentage_error": 0.39545454545454545
      },
      "contribution_margin": {
        "count": 1,
        "forecast_bias": 0.019999999999999907,
        "interval_coverage": null,
        "mean_absolute_error": 0.019999999999999907,
        "mean_percentage_error": 0.029411764705882214
      },
      "conversion_rate": {
        "count": 1,
        "forecast_bias": 0.020000000000000004,
        "interval_coverage": null,
        "mean_absolute_error": 0.020000000000000004,
        "mean_percentage_error": 0.25000000000000006
      },
      "demand": {
        "count": 1,
        "forecast_bias": 10.0,
        "interval_coverage": null,
        "mean_absolute_error": 10.0,
        "mean_percentage_error": 0.1111111111111111
      },
      "gross_margin": {
        "count": 1,
        "forecast_bias": 0.020000000000000018,
        "interval_coverage": null,
        "mean_absolute_error": 0.020000000000000018,
        "mean_percentage_error": 0.025641025641025664
      },
      "implementation_cost": {
        "count": 1,
        "forecast_bias": -2000.0,
        "interval_coverage": null,
        "mean_absolute_error": 2000.0,
        "mean_percentage_error": 0.11764705882352941
      },
      "revenue": {
        "count": 2,
        "forecast_bias": 2000.0,
        "interval_coverage": 0.5,
        "mean_absolute_error": 2000.0,
        "mean_percentage_error": 0.7954545454545454
      },
      "time_to_first_revenue_months": {
        "count": 1,
        "forecast_bias": -1.0,
        "interval_coverage": null,
        "mean_absolute_error": 1.0,
        "mean_percentage_error": 0.2
      },
      "time_to_launch_months": {
        "count": 1,
        "forecast_bias": -1.0,
        "interval_coverage": null,
        "mean_absolute_error": 1.0,
        "mean_percentage_error": 0.25
      }
    },
    "interval_coverage": 0.5,
    "metric_count": 11,
    "observation_count": 2,
    "period_months": 1
  }
}
```

## Decision outcomes

```json
{
  "BUILD": {
    "observed": 1,
    "success_rate": 1.0,
    "successful": 1
  },
  "MORE_EVIDENCE": {
    "observed": 1,
    "success_rate": 0.0,
    "successful": 0
  }
}
```
