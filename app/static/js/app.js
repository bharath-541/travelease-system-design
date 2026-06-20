document.addEventListener("DOMContentLoaded", () => {
  const tabs = document.querySelectorAll("[data-travel-type]");
  const hiddenType = document.querySelector("#travel-type");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((item) => {
        item.classList.remove("is-active");
        item.setAttribute("aria-selected", "false");
      });
      tab.classList.add("is-active");
      tab.setAttribute("aria-selected", "true");
      if (hiddenType) hiddenType.value = tab.dataset.travelType;
    });
  });

  const timer = document.querySelector("[data-expiry]");
  if (timer) {
    const output = timer.querySelector("[data-countdown]");
    const expiry = new Date(timer.dataset.expiry);
    const updateTimer = () => {
      const remaining = Math.max(0, expiry.getTime() - Date.now());
      const minutes = Math.floor(remaining / 60000);
      const seconds = Math.floor((remaining % 60000) / 1000);
      output.textContent = `${minutes}:${seconds.toString().padStart(2, "0")}`;
      if (remaining <= 0) {
        timer.classList.add("is-expired");
        output.textContent = "Expired";
      }
    };
    updateTimer();
    window.setInterval(updateTimer, 1000);
  }
});
