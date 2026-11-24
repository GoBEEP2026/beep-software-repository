    # Completed reviews require final documentation.
    if not is_valid_review_date(review["review_date"]):
        errors.append(
            f"{prefix}: Invalid technical review date. "
            "Expected YYYY-MM-DD"
        )

    if not is_nonempty_review_string(
        review["review_findings"]
    ):
        errors.append(
            f"{prefix}: Missing technical review findings"
        )

    recommendation = review["review_recommendation"]

    if (
        not isinstance(recommendation, str)
        or recommendation not in
        VALID_REVIEW_RECOMMENDATIONS
    ):
        errors.append(
            f"{prefix}: Invalid technical review "
            "recommendation"
        )

    fingerprint = review["reviewed_content_sha256"]

    if (
        not isinstance(fingerprint, str)
        or not SHA256_PATTERN.fullmatch(fingerprint)
    ):
        errors.append(
            f"{prefix}: Missing or invalid reviewed "
            "content SHA-256 fingerprint"
        )

    # Approved and retired versions must retain
    # a recommendation supporting approval.
    if lifecycle_status in ("APPROVED", "RETIRED"):

        if recommendation != "RECOMMEND_APPROVAL":
            errors.append(
                f"{prefix}: {lifecycle_status} reference "
                "homes require RECOMMEND_APPROVAL"
            )

    return errors

def validate_review_fingerprint(home):
    """
    Verify that completed technical reviews match
    the current reference-home technical content.

    Administrative metadata changes do not affect
    the technical content fingerprint.

    A matching fingerprint does not authenticate
    the reviewer or establish Board approval.
    """

    errors = validate_review_documentation(home)

    if errors:
        return errors

    home_id = home.get("test_home_id", "UNKNOWN")
    version = home.get("test_home_version", "UNKNOWN")
    prefix = f"{home_id}/{version}"

    review = home["review"]
    review_status = review["review_status"]

    # Reviews that have not been completed do not
    # require a final technical content fingerprint.
    if review_status != "COMPLETED":
        return []

    reviewed_fingerprint = review[
        "reviewed_content_sha256"
    ]

    try:
        current_fingerprint = (
            calculate_technical_fingerprint(home)
        )

    except (
        TypeError,
        ValueError,
        UnicodeError,
        RecursionError,
    ) as exc:

        return [
            f"{prefix}: Unable to calculate technical "
            f"content fingerprint: {exc}"
        ]

    # Completed reviews must match the current
    # technical content exactly.
    if reviewed_fingerprint != current_fingerprint:

        errors.append(
            f"{prefix}: Technical content fingerprint "
            "does not match the completed review"
        )

        errors.append(
            f"{prefix}: Reviewed SHA-256: "
            f"{reviewed_fingerprint}"
        )

        errors.append(
            f"{prefix}: Current SHA-256: "
            f"{current_fingerprint}"
        )

        errors.append(
            f"{prefix}: Technical content must undergo "
            "a new review before approval. "
            "Approved and retired versions must "
            "remain immutable."
        )

    return errors
