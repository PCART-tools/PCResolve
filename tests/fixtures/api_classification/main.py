from local_lib import (
    fetch_data,
    LocalClient,
    MixedClient,
    ThirdPartyClient,
    wrapper,
    get_alias,
    fetcher,
)

# 1 — locally defined function
local_call = fetch_data("http://a.com")

# 2 — alias to third-party function
alias_call = get_alias("http://b.com")

# 3 — functools.partial wrapping third-party
partial_call = fetcher("http://c.com")

# 4 — locally defined class method
client = LocalClient()
local_method_call = client.get("http://d.com")

# 5 — inherited from local base class → method still local
m_client = MixedClient()
local_inherited_call = m_client.get("http://d2.com")

# 6 — inherited from third-party base class
tp = ThirdPartyClient()
thirdparty_inherited_call = tp.get("http://e.com")

# 7 — nested local call (return flow)
nested_call = wrapper("http://f.com")
