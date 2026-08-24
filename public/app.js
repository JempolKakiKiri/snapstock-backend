const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const imagePreview = document.getElementById('image-preview');
const uploadContent = document.querySelector('.upload-content');
const uploadBtn = document.getElementById('upload-btn');
const loadingSection = document.getElementById('loading');
const resultSection = document.getElementById('result-section');
const resultBody = document.getElementById('result-body');
const totalPriceEl = document.getElementById('total-price');

// Prediksi Elements
const predictBtn = document.getElementById('predict-btn');
const predictLoading = document.getElementById('predict-loading');
const predictionSection = document.getElementById('prediction-section');
const predictionBody = document.getElementById('prediction-body');
const backBtn = document.getElementById('back-btn');

let currentFile = null;

// Handle Drag and Drop
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) {
    handleFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener('change', (e) => {
  if (e.target.files.length) {
    handleFile(e.target.files[0]);
  }
});

function handleFile(file) {
  if (!file.type.startsWith('image/')) {
    alert('Tolong unggah file gambar yang valid.');
    return;
  }

  currentFile = file;

  // Show preview
  const reader = new FileReader();
  reader.onload = (e) => {
    imagePreview.src = e.target.result;
    imagePreview.classList.remove('hidden');
    uploadContent.classList.add('hidden');
    uploadBtn.disabled = false;

    // Reset results
    resultSection.classList.add('hidden');
    predictionSection.classList.add('hidden');
  };
  reader.readAsDataURL(file);
}

// Format Rupiah
const formatRp = (angka) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
  }).format(angka);
};

// Handle Upload
uploadBtn.addEventListener('click', async () => {
  if (!currentFile) return;

  // UI States
  uploadBtn.disabled = true;
  loadingSection.classList.remove('hidden');
  resultSection.classList.add('hidden');

  const formData = new FormData();
  formData.append('image', currentFile); // Backend expects 'image' based on the route

  try {
    const response = await fetch('/api/notes/upload', {
      method: 'POST',
      body: formData,
    });

    const result = await response.json();

    if (response.ok) {
      renderResults(result.data); // using .data from backend response
    } else {
      alert('Gagal memproses nota: ' + (result.message || 'Server Error'));
    }
  } catch (error) {
    console.error('Error:', error);
    alert('Terjadi kesalahan saat menghubungi server.');
  } finally {
    loadingSection.classList.add('hidden');
    uploadBtn.disabled = false;
  }
});

function renderResults(items) {
  resultBody.innerHTML = '';
  let total = 0;

  if (!items || items.length === 0) {
    resultBody.innerHTML =
      '<tr><td colspan="5" style="text-align: center">Tidak ada barang yang terdeteksi</td></tr>';
  } else {
    items.forEach((item) => {
      const subtotal = item.price * item.receipt_qty; // Gunakan qty asli dari nota
      total += subtotal;

      // Assume success if it got here, you could add logic for warnings if backend returns it
      const statusClass = 'status-success';
      const statusText = 'Tersimpan';

      const tr = document.createElement('tr');
      tr.innerHTML = `
                <td><strong>${item.name}</strong></td>
                <td>${formatRp(item.price)}</td>
                <td>${item.receipt_qty}</td>
                <td>${formatRp(subtotal)}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            `;
      resultBody.appendChild(tr);
    });
  }

  totalPriceEl.textContent = formatRp(total);
  resultSection.classList.remove('hidden');

  // Smooth scroll to results
  resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Handle Predict Button
predictBtn.addEventListener('click', async () => {
  // Hide current sections
  dropZone.classList.add('hidden');
  uploadBtn.classList.add('hidden');
  resultSection.classList.add('hidden');

  // Show loading
  predictLoading.classList.remove('hidden');

  try {
    const response = await fetch('/api/inventory/top-recommendations');
    const result = await response.json();

    if (response.ok) {
      renderPredictions(result.data);
    } else {
      alert('Gagal memproses prediksi: ' + (result.message || 'Server Error'));
      // Revert UI on error
      resultSection.classList.remove('hidden');
      dropZone.classList.remove('hidden');
      uploadBtn.classList.remove('hidden');
    }
  } catch (error) {
    console.error('Error:', error);
    alert('Terjadi kesalahan saat menghubungi server ML.');
    resultSection.classList.remove('hidden');
    dropZone.classList.remove('hidden');
    uploadBtn.classList.remove('hidden');
  } finally {
    predictLoading.classList.add('hidden');
  }
});

function renderPredictions(items) {
  predictionBody.innerHTML = '';

  if (!items || items.length === 0) {
    predictionBody.innerHTML =
      '<tr><td colspan="4" style="text-align: center">Tidak ada barang yang perlu di-restock</td></tr>';
  } else {
    items.forEach((item) => {
      const runoutText =
        item.runout_days === 0
          ? 'Data kurang'
          : item.runout_days === '>90'
            ? '>90 Hari'
            : `${item.runout_days} Hari`;
      const statusClass =
        item.runout_days && item.runout_days <= 7 && item.runout_days !== 0
          ? 'status-danger'
          : 'status-info';

      const tr = document.createElement('tr');
      tr.innerHTML = `
                <td><strong>${item.name}</strong></td>
                <td>${item.current_stock}</td>
                <td><span class="status-badge ${statusClass}">${runoutText}</span></td>
                <td><strong>${item.recommended_restock_qty}</strong></td>
            `;
      predictionBody.appendChild(tr);
    });
  }

  predictionSection.classList.remove('hidden');
  predictionSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Handle Back Button
backBtn.addEventListener('click', () => {
  predictionSection.classList.add('hidden');
  dropZone.classList.remove('hidden');
  uploadBtn.classList.remove('hidden');
  resultSection.classList.remove('hidden');

  // reset upload to clean slate? Let's just keep the OCR result visible
});
