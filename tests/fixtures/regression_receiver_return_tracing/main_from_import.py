from factory import create_app

app = create_app()
client = app.test_client()
client.get("/")
