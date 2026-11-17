from math import isclose


def numeric_equal(a, b, tolerance=0.01):
    """Compare numeric values within an absolute tolerance."""
    try:
        return isclose(
            float(a),
            float(b),
            rel_tol=0,
            abs_tol=tolerance
        )
    except (TypeError, ValueError):
        return False


def same_geometry(a, b, area_tolerance=0.01):
    """
    Match walls using geometry, not insulation or IDs.
    Only use fields available in both records.
    """
    required = ("area", "azimuth")

    if any(a.get(k) is None or b.get(k) is None
           for k in required):
        return False

    return (
        numeric_equal(
            a["area"], b["area"], area_tolerance
        )
        and numeric_equal(
            float(a["azimuth"]) % 360,
            float(b["azimuth"]) % 360,
            0.01
        )
    )


def match_components(components_a, components_b):
    """
    Match components using physical characteristics.

    Unique geometry matches are accepted.
    Ambiguous matches are flagged for review.
    Unmatched components are reported.
    """
    matches = []
    ambiguous = []
    unmatched_a = []
    used_b = set()

    for index_a, component_a in enumerate(components_a):
        candidates = [
            index_b
            for index_b, component_b in enumerate(components_b)
            if index_b not in used_b
            and same_geometry(component_a, component_b)
        ]

        if len(candidates) == 1:
            index_b = candidates[0]
            used_b.add(index_b)

            matches.append({
                "vendor_a_index": index_a,
                "vendor_b_index": index_b,
                "vendor_a_id": component_a.get("id"),
                "vendor_b_id": components_b[index_b].get("id"),
                "status": "MATCHED"
            })

        elif len(candidates) > 1:
            ambiguous.append({
                "vendor_a_index": index_a,
                "candidate_b_indices": candidates,
                "status": "REVIEW_REQUIRED"
            })

        else:
            unmatched_a.append(index_a)

    unmatched_b = [
        index
        for index in range(len(components_b))
        if index not in used_b
    ]

    return {
        "matches": matches,
        "ambiguous": ambiguous,
        "unmatched_a": unmatched_a,
        "unmatched_b": unmatched_b
    }
