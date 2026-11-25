from validate_technical_review import (
    validate_review_fingerprint,
    calculate_technical_fingerprint,
)


ALLOWED_REVIEW_TRANSITIONS = {
    "NOT_STARTED": {
        "NOT_STARTED",
        "IN_PROGRESS",
    },
    "IN_PROGRESS": {
        "NOT_STARTED",
        "IN_PROGRESS",
        "COMPLETED",
    },
    "COMPLETED": {
        "NOT_STARTED",
        "COMPLETED",
    },
}


def validate_historical_review_transition(
    previous_home,
    current_home,
):
    """
    Compare technical review information for the
    same reference-home version across registries.

    Protect completed reviews against unauthorized
    changes and require a previously completed
    review before Board approval.
    """

    if not isinstance(previous_home, dict):
        return ["Previous reference home must be a JSON object"]

    if not isinstance(current_home, dict):
        return ["Current reference home must be a JSON object"]

    errors = []

    home_id = current_home.get("test_home_id")
    version = current_home.get("test_home_version")
    prefix = f"{home_id}/{version}"

    # Historical comparisons must involve the
    # same reference-home identity and version.
    for field in (
        "test_home_id",
        "test_home_version",
    ):
        value = current_home.get(field)

        if (
            not isinstance(value, str)
            or not value.strip()
            or previous_home.get(field) != value
        ):
            errors.append(
                f"{prefix}: Historical review comparison "
                f"requires matching {field}"
            )

    if errors:
        return errors

    # Validate the current review documentation
    # and its technical content fingerprint.
    errors.extend(
        validate_review_fingerprint(current_home)
    )

    if errors:
        return errors

    previous_lifecycle = previous_home.get("status")
    current_lifecycle = current_home.get("status")

    previous_review = previous_home.get("review")
    current_review = current_home["review"]

    # Compatibility with the original development
    # registry before review metadata was introduced.
    if (
        "review" not in previous_home
        and previous_lifecycle == "DEVELOPMENT"
    ):
        previous_review_status = "NOT_STARTED"

    else:
        previous_errors = validate_review_fingerprint(
            previous_home
        )

        if previous_errors:
            return [
                f"Previous review: {error}"
                for error in previous_errors
            ]

        previous_review_status = previous_review[
            "review_status"
        ]

    current_review_status = current_review[
        "review_status"
    ]

    # Reject unauthorized review status transitions.
    allowed = ALLOWED_REVIEW_TRANSITIONS.get(
        previous_review_status,
        set(),
    )

    if current_review_status not in allowed:
        errors.append(
            f"{prefix}: Invalid technical review transition "
            f"from {previous_review_status} "
            f"to {current_review_status}"
        )

    # Resetting an active or completed review
    # requires returning to DEVELOPMENT.
    if (
        previous_review_status in (
            "IN_PROGRESS",
            "COMPLETED",
        )
        and current_review_status == "NOT_STARTED"
    ):
        if (
            previous_lifecycle != "UNDER_REVIEW"
            or current_lifecycle != "DEVELOPMENT"
        ):
            errors.append(
                f"{prefix}: Review reset requires "
                "returning to DEVELOPMENT from UNDER_REVIEW"
            )

    # A completed review must remain unchanged
    # while its review status remains COMPLETED.
    if (
        previous_review_status == "COMPLETED"
        and current_review_status == "COMPLETED"
    ):
        if previous_review != current_review:
            errors.append(
                f"{prefix}: Completed technical review "
                "metadata cannot be modified"
            )

        try:
            previous_fingerprint = (
                calculate_technical_fingerprint(
                    previous_home
                )
            )

            current_fingerprint = (
                calculate_technical_fingerprint(
                    current_home
                )
            )

        except (
            TypeError,
            ValueError,
            UnicodeError,
            RecursionError,
        ) as exc:
            errors.append(
                f"{prefix}: Unable to compare historical "
                f"technical fingerprints: {exc}"
            )

        else:
            if previous_fingerprint != current_fingerprint:
                errors.append(
                    f"{prefix}: Previously reviewed "
                    "technical content cannot be modified "
                    "without a new review"
                )

    # Approval must be based on a completed review
    # that existed in the previous accepted registry.
    if (
        current_lifecycle == "APPROVED"
        and previous_lifecycle != "APPROVED"
    ):
        if previous_lifecycle != "UNDER_REVIEW":
            errors.append(
                f"{prefix}: Approval requires a previous "
                "UNDER_REVIEW lifecycle status"
            )

        if previous_review_status != "COMPLETED":
            errors.append(
                f"{prefix}: Approval requires a previously "
                "completed technical review"
            )

        elif previous_review.get(
            "review_recommendation"
        ) != "RECOMMEND_APPROVAL":
            errors.append(
                f"{prefix}: Previous technical review "
                "must recommend approval"
            )

    # Approved and retired reference homes
    # cannot return to active review or development.
    if previous_lifecycle in ("APPROVED", "RETIRED"):
        if current_lifecycle not in (
            "APPROVED",
            "RETIRED",
        ):
            errors.append(
                f"{prefix}: Approved or retired technical "
                "reviews cannot be reset"
            )

    return errors
