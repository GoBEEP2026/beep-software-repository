from component_matcher import match_components


def run_tests():
    vendor_a = [
        {
            "id": "Wall-001",
            "area": "200",
            "azimuth": "0",
            "nominal_r_value": "15"
        },
        {
            "id": "Wall-002",
            "area": "180",
            "azimuth": "180",
            "nominal_r_value": "13"
        }
    ]

    vendor_b = [
        {
            "id": "ExteriorWall-B",
            "area": "180",
            "azimuth": "180",
            "nominal_r_value": "13"
        },
        {
            "id": "ExteriorWall-A",
            "area": "200",
            "azimuth": "0",
            "nominal_r_value": "19"
        }
    ]

    result = match_components(vendor_a, vendor_b)

    assert len(result["matches"]) == 2, result
    assert len(result["ambiguous"]) == 0, result
    assert len(result["unmatched_a"]) == 0, result
    assert len(result["unmatched_b"]) == 0, result

    north_match = next(
        m for m in result["matches"]
        if m["vendor_a_id"] == "Wall-001"
    )

    assert north_match["vendor_b_id"] == "ExteriorWall-A"

    a = vendor_a[north_match["vendor_a_index"]]
    b = vendor_b[north_match["vendor_b_index"]]

    assert a["nominal_r_value"] != b["nominal_r_value"]

    print("PASS: Different IDs and reordered walls matched.")
    print("PASS: Insulation difference identified.")

    # Test unmatched wall
    result = match_components(vendor_a, vendor_b[:1])

    assert len(result["matches"]) == 1, result
    assert len(result["unmatched_a"]) == 1, result

    print("PASS: Missing wall identified.")

    # Test ambiguous geometry
    duplicate_b = [
        vendor_b[1],
        {
            **vendor_b[1],
            "id": "AnotherWall"
        }
    ]

    result = match_components(
        [vendor_a[0]], duplicate_b
    )

    assert len(result["ambiguous"]) == 1, result
    assert len(result["matches"]) == 0, result

    print("PASS: Ambiguous wall matching flagged.")


if __name__ == "__main__":
    run_tests()
