from locust import HttpUser, task, between

class LicenseAPIUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers |= {"Content-Type": "application/json"}

    @task(4)
    def consulta_em_dia(self):
        self.client.post("/api/v1/licenses/check", json={"system_code": "SISTEMA_X", "document": "123"})

    @task(1)
    def consulta_dentro_carencia(self):
        self.client.post("/api/v1/licenses/check", json={"system_code": "SISTEMA_X", "document": "002"})
