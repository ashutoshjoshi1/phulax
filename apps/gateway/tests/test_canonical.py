"""Day 6 exit criterion, verbatim: equivalent inputs produce the same
canonical hash. Property-based over key order and number forms."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from phulax_gateway.canonical import args_meta, canonical_hash, canonicalize

json_scalars = (
    st.none()
    | st.booleans()
    | st.integers(min_value=-(10**9), max_value=10**9)
    | st.floats(allow_nan=False, allow_infinity=False, width=32)
    | st.text(max_size=20)
)
json_values = st.recursive(
    json_scalars,
    lambda children: (
        st.lists(children, max_size=4) | st.dictionaries(st.text(max_size=8), children, max_size=4)
    ),
    max_leaves=12,
)


def _reorder(value):
    """Same data, reversed key insertion order at every level."""
    if isinstance(value, dict):
        return {k: _reorder(value[k]) for k in reversed(list(value))}
    if isinstance(value, list):
        return [_reorder(v) for v in value]
    return value


def test_equivalent_inputs_same_canonical_hash():
    # the doc's own example: {"amount": 25.0, "id": "x"} vs {"id":"x","amount":25.00}
    a = canonical_hash(
        tool_name="issue_refund", environment="staging", arguments={"amount": 25.0, "id": "x"}
    )
    b = canonical_hash(
        tool_name="issue_refund", environment="staging", arguments={"id": "x", "amount": 25.00}
    )
    assert a == b


@given(json_values)
def test_key_order_never_changes_canonical_form(value):
    assert canonicalize(value) == canonicalize(_reorder(value))


@given(st.integers(min_value=-(10**6), max_value=10**6))
def test_integral_float_and_int_are_the_same_request(n):
    assert canonicalize({"amount": n}) == canonicalize({"amount": float(n)})


def test_different_arguments_different_hash():
    base = dict(tool_name="issue_refund", environment="staging")
    assert canonical_hash(**base, arguments={"amount": 25}) != canonical_hash(
        **base, arguments={"amount": 2500}
    )


def test_environment_is_part_of_the_hash():
    args = {"amount": 25}
    staging = canonical_hash(tool_name="t", environment="staging", arguments=args)
    production = canonical_hash(tool_name="t", environment="production", arguments=args)
    assert staging != production


def test_nan_has_no_canonical_form():
    with pytest.raises(ValueError):
        canonicalize({"amount": float("nan")})


def test_args_meta_records_shape_not_values():
    meta = args_meta({"order_id": "ORD-1001", "amount": 25.0, "notify": True, "tags": []})
    assert meta == {
        "order_id": "string",
        "amount": "number",
        "notify": "boolean",
        "tags": "array",
    }
    assert "ORD-1001" not in str(meta)
