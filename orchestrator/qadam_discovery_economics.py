"""Unknown expectancy is a bounded paper experiment, never a positive estimate."""

RETURN_CLASS = "unestimated_discovery_experiment"
SOURCE_METHOD = "bounded_loss_discovery_experiment"
MAX_NOTIONAL_USD = 250.0
MAX_LOSS_USD = 5.0


def is_unestimated_discovery(setup: dict) -> bool:
    return bool(
        setup.get("evidence_class") == "experimental_unvalidated"
        and setup.get("experimental_tier") == "discovery_micro"
        and setup.get("expected_return_class") == RETURN_CLASS
        and setup.get("expected_net_return") is None
        and not setup.get("edge_id")
    )
