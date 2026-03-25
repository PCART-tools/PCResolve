from a import make_client, call_api

get_user = make_client("https://api.example.com")
resp1 = get_user("/users/1")
resp2 = call_api("GET", "https://api.example.com/users/1")