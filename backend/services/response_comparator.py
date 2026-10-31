
def compare_json(response_a, response_b):

    added = []
    missing = []
    changed = []
    type_mismatches = []

    def compare_values(value_a, value_b, path="root"):

        # Check whether data types are different
        if type(value_a) is not type(value_b):
            type_mismatches.append({
                "field": path,
                "old_type": type(value_a).__name__,
                "new_type": type(value_b).__name__
            })
            return

        # Compare dictionaries
        if isinstance(value_a, dict):

            keys_a = set(value_a.keys())
            keys_b = set(value_b.keys())

            for key in keys_a - keys_b:
                missing.append(f"{path}.{key}")

            for key in keys_b - keys_a:
                added.append(f"{path}.{key}")

            for key in keys_a & keys_b:
                compare_values(
                    value_a[key],
                    value_b[key],
                    f"{path}.{key}"
                )

        # Compare lists
        elif isinstance(value_a, list):

            common_length = min(len(value_a), len(value_b))

            for index in range(common_length):
                compare_values(
                    value_a[index],
                    value_b[index],
                    f"{path}[{index}]"
                )

            for index in range(common_length, len(value_a)):
                missing.append(f"{path}[{index}]")

            for index in range(common_length, len(value_b)):
                added.append(f"{path}[{index}]")

        # Compare individual values
        elif value_a != value_b:

            changed.append({
                "field": path,
                "old_value": value_a,
                "new_value": value_b
            })

    compare_values(response_a, response_b)

    total_changes = (
        len(added)
        + len(missing)
        + len(changed)
        + len(type_mismatches)
    )

    return {
        "identical": total_changes == 0,
        "summary": {
            "added_fields": len(added),
            "missing_fields": len(missing),
            "changed_values": len(changed),
            "type_mismatches": len(type_mismatches)
        },
        "added": added,
        "missing": missing,
        "changed": changed,
        "type_mismatches": type_mismatches
    }
