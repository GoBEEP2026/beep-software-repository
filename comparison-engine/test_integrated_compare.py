from integrated_compare import compare_walls


def run_tests():
    walls_a = [
        {
            "id": "Wall-001",
            "area": "200",
            "azimuth": "0",
            "nominal_r_value": "15",
            "assembly_r_value": None
        },
        {
            "id": "Wall-002",
            "area": "180",
            "azimuth": "180",
            "nominal_r_value": "13",
            "assembly_r_value": None
        }
    ]

    walls_b = [
        {
            "id": "VendorB-South",
            "area": "180",
            "azimuth": "180",
            "nominal_r_value": "13",
            "assembly_r_value": None
        },
        {
            "id": "VendorB-North",
            "area": "200",
            "azimuth": "0",
            "nominal_r_value": "19",
            "assembly_r_value": None
        }
    ]

    result = compare_walls(walls_a, walls_b)

    assert result["matched"] == 2, result
    assert len(result["differences"]) == 1, result

    difference = result["differences"][0]

    assert difference["field"] == "nominal_r_value"
    assert difference["value_a"] == "15"
    assert difference["value_b"] == "19"

    assert result["ambiguous"] == [], result
    assert result["unmatched_a"] == [], result
    assert result["unmatched_b"] == [], result

    print("PASS: Two walls matched across different IDs.")
    print("PASS: North wall insulation difference detected.")
    print("PASS: No unmatched or ambiguous walls.")


if __name__ == "__main__":
    run_tests()
