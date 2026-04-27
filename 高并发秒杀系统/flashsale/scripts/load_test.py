from locust import HttpUser, task

class FlashSaleUser(HttpUser):
    @task
    def get_product(self):
        self.client.get("/api/v1/products/1001")

    @task(3)  # 更高频
    def create_order(self):
        self.client.post("/api/v1/orders/", json={"user_id": 1, "product_id": 1001})