import factory as f

app = f.create_app()
client = app.test_client()
client.get("/alias")
