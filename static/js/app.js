(() => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const canvas = document.getElementById('waveform');
  const ctx = canvas.getContext('2d');
  const dropPrompt = document.getElementById('dropPrompt');
  const fileMeta = document.getElementById('fileMeta');
  const fileNameEl = document.getElementById('fileName');
  const fileSizeEl = document.getElementById('fileSize');
  const backendSelect = document.getElementById('backendSelect');
  const backendHint = document.getElementById('backendHint');
  const transcribeBtn = document.getElementById('transcribeBtn');
  const statusEl = document.getElementById('status');
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const resultStrip = document.getElementById('resultStrip');
  const resultText = document.getElementById('resultText');
  const metaDuration = document.getElementById('metaDuration');
  const metaBackend = document.getElementById('metaBackend');
  const metaElapsed = document.getElementById('metaElapsed');
  const errorStrip = document.getElementById('errorStrip');
  const errorText = document.getElementById('errorText');
  const copyBtn = document.getElementById('copyBtn');

  const BACKEND_HINTS = {
    sphinx: 'Sphinx runs fully offline, no setup required.',
    google: 'Google Web Speech needs an internet connection.',
    whisper: 'Whisper needs the optional openai-whisper package installed.',
  };

  let selectedFile = null;
  let selectedBackend = 'sphinx';
  let currentPeaks = null;
  let sweepFrame = null;

  function resizeCanvas() {
    const rect = dropzone.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (currentPeaks) drawWaveform(currentPeaks);
  }
  window.addEventListener('resize', resizeCanvas);

  function drawWaveform(peaks, opts = {}) {
    const { sweepX = null, color = '#e2a354' } = opts;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    if (!peaks || peaks.length === 0) return;

    const gap = 2;
    const barWidth = w / peaks.length - gap;
    const midY = h / 2;

    peaks.forEach((p, i) => {
      const barH = Math.max(2, p * (h * 0.78));
      const x = i * (barWidth + gap);
      const isPast = sweepX !== null && x <= sweepX;
      ctx.fillStyle = sweepX !== null ? (isPast ? color : '#3a2f22') : color;
      ctx.fillRect(x, midY - barH / 2, Math.max(1, barWidth), barH);
    });

    if (sweepX !== null) {
      ctx.fillStyle = 'rgba(243, 236, 224, 0.85)';
      ctx.fillRect(sweepX, 0, 1.5, h);
    }
  }

  function startSweep() {
    let x = 0;
    const w = canvas.clientWidth;
    const speed = w / 55; // px per frame, ~ full sweep in well under a second per pass
    function frame() {
      x += speed;
      if (x > w) x = 0;
      drawWaveform(currentPeaks || placeholderPeaks(48), { sweepX: x });
      sweepFrame = requestAnimationFrame(frame);
    }
    sweepFrame = requestAnimationFrame(frame);
  }

  function stopSweep() {
    if (sweepFrame) cancelAnimationFrame(sweepFrame);
    sweepFrame = null;
  }

  function placeholderPeaks(n) {
    return Array.from({ length: n }, () => 0.15 + Math.random() * 0.1);
  }

  function formatBytes(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function setStatus(mode, text) {
    statusEl.classList.remove('is-busy', 'is-error');
    if (mode === 'busy') statusEl.classList.add('is-busy');
    if (mode === 'error') statusEl.classList.add('is-error');
    statusText.textContent = text;
  }

  // Best-effort client-side waveform preview, drawn the instant a file is
  // chosen (before the server round-trip). Falls back silently if the
  // browser can't decode the format; the server-derived waveform (returned
  // alongside the transcript) becomes authoritative once available.
  async function previewWaveform(file) {
    try {
      const arrayBuffer = await file.arrayBuffer();
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioCtx();
      const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer.slice(0));
      const raw = audioBuffer.getChannelData(0);
      const numPeaks = 120;
      const chunkSize = Math.max(1, Math.floor(raw.length / numPeaks));
      const peaks = [];
      for (let i = 0; i < numPeaks; i++) {
        let max = 0;
        const start = i * chunkSize;
        for (let j = start; j < start + chunkSize && j < raw.length; j++) {
          max = Math.max(max, Math.abs(raw[j]));
        }
        peaks.push(max);
      }
      const loudest = Math.max(...peaks) || 1;
      currentPeaks = peaks.map((p) => Math.min(p / loudest, 1));
      drawWaveform(currentPeaks);
      audioCtx.close();
    } catch (err) {
      currentPeaks = null; // silent fallback — server peaks will fill this in
    }
  }

  function handleFile(file) {
    selectedFile = file;
    dropzone.classList.add('has-file');
    fileMeta.hidden = false;
    fileNameEl.textContent = file.name;
    fileSizeEl.textContent = formatBytes(file.size);
    transcribeBtn.disabled = false;
    resultStrip.hidden = true;
    errorStrip.hidden = true;
    setStatus('ready', 'ready');
    resizeCanvas();
    previewWaveform(file);
  }

  dropzone.addEventListener('click', () => fileInput.click());
  dropzone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
  });
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  ['dragenter', 'dragover'].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add('is-dragover');
    })
  );
  ['dragleave', 'drop'].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove('is-dragover');
    })
  );
  dropzone.addEventListener('drop', (e) => {
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });

  backendSelect.querySelectorAll('.segmented__option').forEach((btn) => {
    btn.addEventListener('click', () => {
      backendSelect.querySelectorAll('.segmented__option').forEach((b) => {
        b.classList.remove('is-active');
        b.setAttribute('aria-checked', 'false');
      });
      btn.classList.add('is-active');
      btn.setAttribute('aria-checked', 'true');
      selectedBackend = btn.dataset.backend;
      backendHint.textContent = BACKEND_HINTS[selectedBackend] || '';
    });
  });

  transcribeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    transcribeBtn.disabled = true;
    transcribeBtn.classList.add('is-busy');
    resultStrip.hidden = true;
    errorStrip.hidden = true;
    setStatus('busy', 'listening…');
    startSweep();

    const formData = new FormData();
    formData.append('audio', selectedFile);
    formData.append('backend', selectedBackend);

    try {
      const res = await fetch('/api/transcribe', { method: 'POST', body: formData });
      const data = await res.json();
      stopSweep();

      if (!res.ok) {
        throw new Error(data.error || 'Transcription failed.');
      }

      currentPeaks = data.peaks || currentPeaks;
      drawWaveform(currentPeaks);

      resultText.textContent = data.text || '(no speech detected)';
      metaDuration.textContent = `${data.duration_seconds}s clip`;
      metaBackend.textContent = data.backend;
      metaElapsed.textContent = `${data.elapsed_seconds}s to transcribe`;
      resultStrip.hidden = false;
      setStatus('ready', 'done');
    } catch (err) {
      stopSweep();
      drawWaveform(currentPeaks);
      errorText.textContent = err.message;
      errorStrip.hidden = false;
      setStatus('error', 'error');
    } finally {
      transcribeBtn.disabled = false;
      transcribeBtn.classList.remove('is-busy');
    }
  });

  copyBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(resultText.textContent);
      copyBtn.textContent = 'Copied';
      copyBtn.classList.add('is-copied');
      setTimeout(() => {
        copyBtn.textContent = 'Copy text';
        copyBtn.classList.remove('is-copied');
      }, 1500);
    } catch (err) {
      // Clipboard API unavailable (e.g. insecure context) — fail silently.
    }
  });

  resizeCanvas();
})();
