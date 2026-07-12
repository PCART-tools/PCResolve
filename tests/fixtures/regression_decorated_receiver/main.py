# 1.0.5 P2: Decorated callable receiver evidence.
# Uses real third-party names so PCResolve treats them as external.

import click


@click.command()
@click.option("--name", default="World")
def hello(name):
    click.echo(f"Hello, {name}!")


# Direct call on decorated callable — decorated_by from exact match
hello()

# Receiver method call — decorated_by from receiver-aware lookup
hello.main(standalone_mode=False)
