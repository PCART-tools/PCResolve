def consume_known(values):
    for item in values:
        item.strip()


def invoke_known():
    consume_known(["alpha", "beta"])


def consume_forwarded(values):
    for item in values:
        item.strip()


def forward_known(values):
    consume_forwarded(values)


def invoke_forwarded():
    forward_known(["gamma"])


def consume_unknown(values):
    for item in values:
        item.strip()


def consume_unresolved_iterator(table):
    for _, row in table.iterrows():
        values = row["field"].split(",")
        for item in values:
            item.strip()
