function confirmDelete(message) {
  return window.confirm(message || "Are you sure?");
}

document.querySelectorAll("[data-copy-target]").forEach((button) => {
  button.addEventListener("click", async () => {
    const target = document.querySelector(button.dataset.copyTarget);
    if (!target) return;

    try {
      await navigator.clipboard.writeText(target.value);
      button.textContent = "Copied";
    } catch {
      target.select();
      document.execCommand("copy");
      button.textContent = "Copied";
    }
  });
});
