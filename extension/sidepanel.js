const button = document.querySelector("#health-check");
const status = document.querySelector("#status");

button.addEventListener("click", async () => {
  status.textContent = "Checking…";
  button.disabled = true;
  try {
    const response = await fetch("http://localhost:8000/health");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    status.textContent = data.status === "ok"
      ? "Connected to VANTIQ API."
      : "API responded, but health status is not OK.";
  } catch (error) {
    status.textContent = "Backend unavailable. Start the Docker Compose services.";
  } finally {
    button.disabled = false;
  }
});
