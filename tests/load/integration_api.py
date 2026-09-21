from locust import HttpUser, task, between

class IntegrationAPIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers |= {"Content-Type": "application/json"}

    @task(2)
    def get_incremental(self):
        self.client.get("/api/v1/integrations/clients/")

    @task(2)
    def upsert_unico(self):
        self.client.post("/api/v1/integrations/clients/", json={"external_id": "loc-1", "nome": "Locust"})
