(function () {
  "use strict";

  const navToggle = document.querySelector("[data-nav-toggle]");
  const nav = document.querySelector("[data-nav]");
  if (navToggle && nav) {
    navToggle.addEventListener("click", function () {
      const open = nav.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
  }

  const fileInput = document.querySelector("[data-file-input]");
  const dropArea = document.querySelector("[data-drop-area]");
  const uploadForm = document.querySelector("[data-upload-form]");
  const fileNameLabel = document.querySelector("[data-file-name]");
  const uploadButton = document.querySelector("[data-upload-submit]");
  function showFile(file) {
    if (!fileNameLabel || !file) return;
    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    fileNameLabel.textContent = file.name + " · " + sizeMb + " MB";
    fileNameLabel.classList.add("has-file");
  }
  if (fileInput) {
    fileInput.addEventListener("change", function () {
      if (fileInput.files && fileInput.files[0]) showFile(fileInput.files[0]);
    });
  }
  if (dropArea && fileInput) {
    ["dragenter", "dragover"].forEach(function (name) {
      dropArea.addEventListener(name, function (event) {
        event.preventDefault();
        dropArea.classList.add("is-dragging");
      });
    });
    ["dragleave", "drop"].forEach(function (name) {
      dropArea.addEventListener(name, function (event) {
        event.preventDefault();
        dropArea.classList.remove("is-dragging");
      });
    });
    dropArea.addEventListener("drop", function (event) {
      const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
      if (!file) return;
      const transfer = new DataTransfer();
      transfer.items.add(file);
      fileInput.files = transfer.files;
      showFile(file);
    });
  }
  if (uploadForm && uploadButton) {
    uploadForm.addEventListener("submit", function (event) {
      const file = fileInput && fileInput.files && fileInput.files[0];
      if (!file) {
        event.preventDefault();
        window.alert("Choose a CSV or XLSX file first.");
        return;
      }
      const allowed = /\.(csv|xlsx)$/i.test(file.name);
      if (!allowed) {
        event.preventDefault();
        window.alert("Only CSV and XLSX files are supported.");
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        event.preventDefault();
        window.alert("This file is larger than 50 MB. Split it into smaller batches.");
        return;
      }
      uploadButton.disabled = true;
      uploadButton.textContent = "Queueing batch…";
    });
  }

  const jobPanel = document.querySelector("[data-job-poll]");
  if (jobPanel && jobPanel.dataset.finished !== "true") {
    const statusUrl = jobPanel.dataset.statusUrl;
    const percentEl = document.getElementById("job-percent");
    const fillEl = document.getElementById("job-progress-fill");
    const phaseEl = document.getElementById("job-phase");
    const progressText = document.getElementById("job-progress-text");
    const statusPill = document.getElementById("job-status-pill");
    const logEl = document.getElementById("job-log");
    const smtpEl = document.getElementById("smtp-status");
    let polling = false;
    let timer = null;

    async function pollJob() {
      if (polling) return;
      polling = true;
      try {
        const response = await fetch(statusUrl, { credentials: "same-origin", headers: { "Accept": "application/json" } });
        if (!response.ok) throw new Error("Status request failed");
        const data = await response.json();
        const percent = Math.max(0, Math.min(100, Number(data.percent || 0)));
        if (percentEl) percentEl.innerHTML = percent + "<small>%</small>";
        if (fillEl) fillEl.style.width = percent + "%";
        if (phaseEl) phaseEl.textContent = String(data.phase || data.status || "working").replace(/_/g, " ").replace(/\b\w/g, function (letter) { return letter.toUpperCase(); });
        if (progressText) progressText.textContent = (data.completed || 0) + " of " + (data.total || "…") + " rows processed";
        if (statusPill) {
          statusPill.className = "status-pill status-" + data.status;
          statusPill.textContent = String(data.status || "queued").replace(/^\w/, function (letter) { return letter.toUpperCase(); });
        }
        if (logEl && data.last_log) logEl.textContent = data.last_log;
        if (smtpEl && data.smtp_available !== null) smtpEl.textContent = data.smtp_available ? "SMTP port reachable" : "SMTP port blocked or unavailable";
        ["valid", "invalid", "risky", "unknown"].forEach(function (key) {
          const counter = document.getElementById("count-" + key);
          if (counter) counter.textContent = data[key] || 0;
        });
        if (data.finished) {
          jobPanel.dataset.finished = "true";
          if (timer) window.clearInterval(timer);
          window.setTimeout(function () { window.location.reload(); }, 650);
        }
      } catch (error) {
        if (logEl) logEl.textContent = "Trying to reconnect to the job worker…";
      } finally {
        polling = false;
      }
    }
    pollJob();
    timer = window.setInterval(pollJob, 2000);
  }
})();
