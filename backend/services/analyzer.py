
import json


def analyze_response(status_code, response_time_ms, headers, body):

    critical_issues = []
    warnings = []
    recommendations = []

    critical_suggestions = []
    warning_suggestions = []

    # Normalize response header names
    normalized_headers = {
        str(key).lower(): value
        for key, value in headers.items()
    }

    # 1. Analyze HTTP status code

    if status_code >= 500:

        critical_issues.append(
            "Server-side HTTP error detected"
        )

        critical_suggestions.append(
            "Check backend logs, server exceptions and server availability."
        )

    elif status_code >= 400:

        warnings.append(
            "Client-side HTTP error detected"
        )

        warning_suggestions.append(
            "Check the request URL, parameters, headers and body."
        )

    elif status_code >= 300:

        warnings.append(
            "Redirection response detected"
        )

        warning_suggestions.append(
            "Check the redirect location and expected API behavior."
        )

    elif status_code >= 200:

        pass

    else:

        warnings.append(
            "Unexpected HTTP status code detected"
        )

    # 2. Analyze response time

    if response_time_ms > 3000:

        warnings.append(
            "Slow API response detected"
        )

        warning_suggestions.append(
            "Investigate server processing time and network latency."
        )

    elif response_time_ms > 1000:

        warnings.append(
            "API response is slower than expected"
        )

        warning_suggestions.append(
            "Monitor performance and consider optimizing the endpoint."
        )

    # 3. Analyze Content-Type header

    content_type = normalized_headers.get(
        "content-type", ""
    )

    is_json = "application/json" in content_type.lower()

    if not content_type:

        recommendations.append(
            "Content-Type header is missing."
        )

    # 4. Validate JSON response

    json_valid = None

    if is_json:

        try:

            json.loads(body)
            json_valid = True

        except (json.JSONDecodeError, TypeError):

            json_valid = False

            critical_issues.append(
                "Invalid JSON response detected"
            )

            critical_suggestions.append(
                "Check the response body for malformed JSON syntax."
            )

    # 5. Check security-related response headers

    if "x-content-type-options" not in normalized_headers:

        recommendations.append(
            "Consider adding X-Content-Type-Options: nosniff "
            "where appropriate."
        )

    # 6. Calculate API Health Score

    score = 100

    # HTTP status evaluation

    if status_code >= 500:
        score -= 50

    elif status_code >= 400:
        score -= 30

    elif status_code >= 300:
        score -= 10

    # Response time evaluation

    if response_time_ms > 3000:
        score -= 25

    elif response_time_ms > 1000:
        score -= 10

    # JSON validation

    if json_valid is False:
        score -= 20

    # Keep score between 0 and 100

    score = max(0, min(100, score))

    # 7. Determine health category

    if score >= 85:
        health = "Healthy"

    elif score >= 60:
        health = "Needs Attention"

    else:
        health = "Critical"

    # 8. Maintain backward compatibility

    issues = critical_issues + warnings

    suggestions = (
        critical_suggestions
        + warning_suggestions
        + recommendations
    )

    # 9. Return diagnostic results

    return {
        "health": health,
        "health_score": score,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "json_valid": json_valid,

        "critical_issues": critical_issues,
        "warnings": warnings,
        "recommendations": recommendations,

        "issues": issues,
        "suggestions": suggestions
    }
