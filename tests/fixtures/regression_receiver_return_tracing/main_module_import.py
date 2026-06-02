import factory

app = factory.create_app()
client = app.test_client()
client.get("/x")
