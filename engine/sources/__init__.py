"""
Data sources, one module per institution.

Each module has pure `parse_*` functions (bytes in, pandas out, tested offline
against saved responses in tests/fixtures) and a `fetch()` that downloads and
parses. `fetch()` returns a DataFrame indexed by date whose columns are
catalogue ids such as "USD.2Y", so nothing downstream knows or cares which
institution a number came from. If a source dies, swap it in its own module.
"""
