/**
 * PDF Split & Merge Studio - Logique Applicative Frontend
 * 100% Hors-ligne, réactif et sans dépendance externe
 */

// État global de l'application
const state = {
  currentFile: null,            // Fichier source actif pour découpe/organisation
  splitMode: 'page_by_page',    // Mode de découpe actif
  selectedPages: new Set(),     // Indices des pages sélectionnées (0-indexed)
  pageRotations: {},            // { [pageIndex]: degrees }
  thumbnails: {},               // Cache local { [pageIndex]: data_url }
  qualityMode: 'original',      // 'original', 'high', 'medium', 'low', 'custom'
  outputDirMode: 'source',      // 'source', 'custom'
  customOutputDir: null,        // Chemin du dossier choisi
  
  // File de fusion
  mergeQueue: [],               // [{ file_path, file_name, file_size_formatted, page_count, pages: 'all', rotation: 0 }]
  mergeDirMode: 'first_file',
  mergeCustomDir: null,

  lastResultOutputDir: null     // Dernier dossier d'export pour ouverture directe
};

// Initialisation au chargement du DOM
document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initSplitView();
  initMergeView();
  initOrganizeView();
  initModals();
  initDragAndDrop();
});

/* ==========================================================================
   NAVIGATION ENTRE ONGLETS
   ========================================================================== */
function initNavigation() {
  const tabButtons = document.querySelectorAll('.tab-btn');
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');
      
      // Mise à jour visuelle des boutons
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Affichage du panneau correspondant
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      const activePane = document.getElementById(targetId);
      if (activePane) activePane.classList.add('active');

      // Si passage sur l'onglet Organiser, rafraîchir la vue
      if (targetId === 'tab-organize') {
        refreshOrganizeView();
      }
    });
  });
}

/* ==========================================================================
   NOTIFICATIONS TOAST
   ========================================================================== */
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span>
    <div>${message}</div>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* ==========================================================================
   GESTION DU GLISSER-DÉPOSER (DRAG & DROP)
   ========================================================================== */
function initDragAndDrop() {
  const dropzone = document.getElementById('split-dropzone');
  if (!dropzone) return;

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.name.toLowerCase().endsWith('.pdf')) {
        uploadPdfFile(file);
      } else {
        showToast('Veuillez déposer un document au format PDF (.pdf).', 'error');
      }
    }
  });

  // Glisser-déposer global pour la fenêtre
  window.addEventListener('dragover', (e) => e.preventDefault());
  window.addEventListener('drop', (e) => e.preventDefault());
}

/* ==========================================================================
   VUE DÉCOUPER (SPLIT)
   ========================================================================== */
function initSplitView() {
  const btnBrowse = document.getElementById('btn-browse-split');
  const fileInput = document.getElementById('input-split-file');
  const btnChange = document.getElementById('btn-change-split-file');

  // Clic sur Parcourir : essaye d'abord la boîte native Windows via backend
  btnBrowse.addEventListener('click', async () => {
    try {
      const resp = await fetch('/api/choose-file', { method: 'POST' });
      const data = await resp.json();
      if (data.selected && data.info) {
        loadPdfDocument(data.info);
      }
    } catch (err) {
      // Fallback si dialogue système inaccessible : sélecteur HTML standard
      fileInput.click();
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      uploadPdfFile(e.target.files[0]);
    }
  });

  btnChange.addEventListener('click', () => {
    btnBrowse.click();
  });

  // Sélection du mode de découpe
  const modeCards = document.querySelectorAll('.mode-card');
  modeCards.forEach(card => {
    card.addEventListener('click', () => {
      const mode = card.getAttribute('data-mode');
      setSplitMode(mode);
    });
  });

  // Sélection des filtres de miniatures
  document.getElementById('btn-select-all').addEventListener('click', () => {
    if (!state.currentFile) return;
    for (let i = 0; i < state.currentFile.page_count; i++) state.selectedPages.add(i);
    updateThumbnailsSelection();
  });

  document.getElementById('btn-deselect-all').addEventListener('click', () => {
    state.selectedPages.clear();
    updateThumbnailsSelection();
  });

  document.getElementById('btn-select-even').addEventListener('click', () => {
    if (!state.currentFile) return;
    state.selectedPages.clear();
    for (let i = 0; i < state.currentFile.page_count; i++) {
      if ((i + 1) % 2 === 0) state.selectedPages.add(i);
    }
    updateThumbnailsSelection();
  });

  document.getElementById('btn-select-odd').addEventListener('click', () => {
    if (!state.currentFile) return;
    state.selectedPages.clear();
    for (let i = 0; i < state.currentFile.page_count; i++) {
      if ((i + 1) % 2 !== 0) state.selectedPages.add(i);
    }
    updateThumbnailsSelection();
  });

  document.getElementById('btn-select-invert').addEventListener('click', () => {
    if (!state.currentFile) return;
    const inverted = new Set();
    for (let i = 0; i < state.currentFile.page_count; i++) {
      if (!state.selectedPages.has(i)) inverted.add(i);
    }
    state.selectedPages = inverted;
    updateThumbnailsSelection();
  });

  // Destination d'exportation
  const radioSource = document.getElementById('radio-dest-source');
  const radioCustom = document.getElementById('radio-dest-custom');
  const customPickerWrap = document.getElementById('custom-folder-picker-wrap');
  const btnBrowseFolder = document.getElementById('btn-browse-folder');

  radioSource.addEventListener('change', () => {
    if (radioSource.checked) {
      state.outputDirMode = 'source';
      customPickerWrap.style.display = 'none';
    }
  });

  radioCustom.addEventListener('change', () => {
    if (radioCustom.checked) {
      state.outputDirMode = 'custom';
      customPickerWrap.style.display = 'block';
      if (!state.customOutputDir) {
        btnBrowseFolder.click();
      }
    }
  });

  btnBrowseFolder.addEventListener('click', async () => {
    try {
      const resp = await fetch('/api/choose-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_dir: state.currentFile?.file_dir || '' })
      });
      const data = await resp.json();
      if (data.selected && data.folder_path) {
        state.customOutputDir = data.folder_path;
        document.getElementById('input-custom-folder-path').value = data.folder_path;
        document.getElementById('label-custom-folder').textContent = data.folder_path;
        radioCustom.checked = true;
        state.outputDirMode = 'custom';
      }
    } catch (err) {
      showToast("Impossible d'ouvrir le sélecteur de dossier.", "error");
    }
  });

  // Réglages qualité
  const qualityPills = document.querySelectorAll('.quality-pill');
  const slidersBox = document.getElementById('custom-quality-sliders');
  const sliderDpi = document.getElementById('slider-dpi');
  const sliderJpeg = document.getElementById('slider-jpeg');
  const valDpi = document.getElementById('val-dpi');
  const valJpeg = document.getElementById('val-jpeg');

  qualityPills.forEach(pill => {
    pill.addEventListener('click', () => {
      qualityPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const q = pill.getAttribute('data-quality');
      state.qualityMode = q;

      if (q === 'custom') {
        slidersBox.style.display = 'block';
      } else {
        slidersBox.style.display = 'none';
      }
    });
  });

  sliderDpi.addEventListener('input', (e) => {
    valDpi.textContent = `${e.target.value} DPI`;
  });

  sliderJpeg.addEventListener('input', (e) => {
    valJpeg.textContent = `${e.target.value}%`;
  });

  // Mot de passe pour la découpe
  const checkEncrypt = document.getElementById('check-encrypt-split');
  const splitPwdWrap = document.getElementById('split-password-input-wrap');
  checkEncrypt.addEventListener('change', () => {
    splitPwdWrap.style.display = checkEncrypt.checked ? 'block' : 'none';
  });

  // Calcul dynamique de prévisualisation par paquets
  document.getElementById('input-chunk-size').addEventListener('input', (e) => {
    updateChunkPreview();
  });

  // Bouton de lancement
  document.getElementById('btn-execute-split').addEventListener('click', executeSplit);
}

function setSplitMode(mode) {
  state.splitMode = mode;

  // Mise à jour de la carte active
  document.querySelectorAll('.mode-card').forEach(c => {
    c.classList.toggle('active', c.getAttribute('data-mode') === mode);
  });

  // Mise à jour du panneau de configuration
  document.querySelectorAll('.mode-config-item').forEach(item => {
    item.style.display = 'none';
  });

  const activeConfig = document.getElementById(`config-${mode}`);
  if (activeConfig) activeConfig.style.display = 'block';

  updateChunkPreview();
}

function updateChunkPreview() {
  if (!state.currentFile) return;
  const chunkInput = document.getElementById('input-chunk-size');
  const chunkCalc = document.getElementById('preview-chunk-calc');
  const sz = parseInt(chunkInput.value, 10) || 1;
  const total = state.currentFile.page_count;
  const count = Math.ceil(total / sz);
  chunkCalc.textContent = `Générera ~${count} fichier(s) (1-${Math.min(sz, total)}.pdf, etc.)`;
}

// Téléversement d'un fichier via API (drag & drop)
async function uploadPdfFile(file) {
  showToast("Chargement du document PDF en cours...", "info");
  const formData = new FormData();
  formData.append('file', file);

  try {
    const resp = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await resp.json();
    if (data.success && data.info) {
      loadPdfDocument(data.info);
    } else {
      showToast(data.detail || "Erreur de lecture du PDF.", "error");
    }
  } catch (err) {
    showToast("Erreur lors de l'import du PDF.", "error");
  }
}

// Chargement complet du document dans l'interface
async function loadPdfDocument(info) {
  state.currentFile = info;
  state.selectedPages.clear();
  state.pageRotations = {};
  state.thumbnails = {};

  // Par défaut toutes les pages sont sélectionnées
  for (let i = 0; i < info.page_count; i++) {
    state.selectedPages.add(i);
  }

  // Affichage des informations
  document.getElementById('split-dropzone-section').style.display = 'none';
  document.getElementById('split-workspace').style.display = 'block';

  document.getElementById('split-file-name').textContent = info.file_name;
  document.getElementById('split-file-pages').textContent = `${info.page_count} page(s)`;
  document.getElementById('split-file-size').textContent = info.file_size_formatted;
  document.getElementById('split-file-folder').textContent = info.file_dir;
  document.getElementById('label-source-folder').textContent = info.file_dir;
  document.getElementById('input-naming-prefix').value = info.stem;

  updateChunkPreview();
  renderThumbnailsGrid();

  // Chargement asynchrone des miniatures par lot
  loadBatchThumbnails(info.file_path, info.page_count);

  showToast(`Document « ${info.file_name} » chargé (${info.page_count} pages).`, "success");
}

// Rendu du squelette de la grille des miniatures
function renderThumbnailsGrid() {
  const container = document.getElementById('split-thumbnails-grid');
  if (!container || !state.currentFile) return;

  container.innerHTML = '';
  const total = state.currentFile.page_count;

  for (let i = 0; i < total; i++) {
    const card = document.createElement('div');
    card.className = `page-card ${state.selectedPages.has(i) ? 'selected' : ''}`;
    card.id = `page-card-${i}`;
    card.dataset.page = i;

    card.innerHTML = `
      <div class="page-card-header">
        <span class="page-num-badge">P. ${i + 1}</span>
        <input type="checkbox" class="page-checkbox" ${state.selectedPages.has(i) ? 'checked' : ''}>
      </div>
      <div class="page-thumbnail-wrap shimmer" id="thumb-wrap-${i}" title="Cliquer pour agrandir">
        <img class="page-thumbnail-img" id="thumb-img-${i}" style="display:none;" alt="Page ${i + 1}">
      </div>
      <div class="page-card-actions">
        <button class="btn-icon-mini btn-rotate-page" title="Pivoter de 90°" data-page="${i}">
          <svg viewBox="0 0 24 24"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path></svg>
        </button>
        <button class="btn-icon-mini btn-preview-page" title="Aperçu grand format" data-page="${i}">
          <svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>
        </button>
      </div>
    `;

    // Événement clic sur la carte pour cocher / décocher
    card.addEventListener('click', (e) => {
      if (e.target.closest('.btn-rotate-page') || e.target.closest('.btn-preview-page')) {
        return;
      }
      togglePageSelection(i);
    });

    // Rotation individuelle
    const btnRotate = card.querySelector('.btn-rotate-page');
    btnRotate.addEventListener('click', (e) => {
      e.stopPropagation();
      rotatePage(i, 90);
    });

    // Aperçu grande taille
    const btnPreview = card.querySelector('.btn-preview-page');
    btnPreview.addEventListener('click', (e) => {
      e.stopPropagation();
      openHighResPreview(i);
    });

    container.appendChild(card);
  }

  updateSelectionCountBadge();
}

// Chargement en arrière-plan des miniatures par lot (ultra-rapide avec pypdfium2)
async function loadBatchThumbnails(filePath, totalPages) {
  try {
    const resp = await fetch('/api/thumbnails-batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath, scale: 0.35 })
    });
    const data = await resp.json();
    if (data.success && data.thumbnails) {
      Object.entries(data.thumbnails).forEach(([idxStr, dataUrl]) => {
        const idx = parseInt(idxStr, 10);
        state.thumbnails[idx] = dataUrl;

        const img = document.getElementById(`thumb-img-${idx}`);
        const wrap = document.getElementById(`thumb-wrap-${idx}`);
        if (img && wrap) {
          img.src = dataUrl;
          img.style.display = 'block';
          wrap.classList.remove('shimmer');
        }
      });
    }
  } catch (err) {
    console.error("Erreur de rendu des miniatures :", err);
  }
}

function togglePageSelection(pageIdx) {
  if (state.selectedPages.has(pageIdx)) {
    state.selectedPages.delete(pageIdx);
  } else {
    state.selectedPages.add(pageIdx);
  }
  updateThumbnailsSelection();
}

function updateThumbnailsSelection() {
  document.querySelectorAll('.page-card').forEach(card => {
    const p = parseInt(card.dataset.page, 10);
    const isSelected = state.selectedPages.has(p);
    card.classList.toggle('selected', isSelected);
    const cb = card.querySelector('.page-checkbox');
    if (cb) cb.checked = isSelected;
  });
  updateSelectionCountBadge();
}

function updateSelectionCountBadge() {
  const badge = document.getElementById('count-selected-pages');
  if (badge) badge.textContent = state.selectedPages.size;
}

function rotatePage(pageIdx, angleDelta) {
  const current = state.pageRotations[pageIdx] || 0;
  const newAngle = (current + angleDelta) % 360;
  state.pageRotations[pageIdx] = newAngle;

  const img = document.getElementById(`thumb-img-${pageIdx}`);
  if (img) {
    img.style.transform = `rotate(${newAngle}deg)`;
  }
}

// Aperçu haute résolution d'une page
async function openHighResPreview(pageIdx) {
  if (!state.currentFile) return;
  const modal = document.getElementById('modal-preview');
  const modalTitle = document.getElementById('preview-modal-title');
  const modalImg = document.getElementById('preview-modal-img');

  modalTitle.textContent = `Aperçu grand format — Page ${pageIdx + 1} / ${state.currentFile.page_count}`;
  modal.classList.add('active');

  // Si on a déjà une vignette, on l'affiche tout de suite en attendant le grand rendu
  if (state.thumbnails[pageIdx]) {
    modalImg.src = state.thumbnails[pageIdx];
  }

  // Chargement en haute résolution (scale = 1.3)
  try {
    const resp = await fetch('/api/thumbnail', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        file_path: state.currentFile.file_path,
        page_index: pageIdx,
        scale: 1.3
      })
    });
    const data = await resp.json();
    if (data.success && data.data_url) {
      modalImg.src = data.data_url;
    }
  } catch (err) {
    console.error("Erreur d'aperçu haute résolution :", err);
  }
}

// Exécution du découpage
async function executeSplit() {
  if (!state.currentFile) {
    showToast("Veuillez d'abord importer un document PDF.", "error");
    return;
  }

  const btn = document.getElementById('btn-execute-split');
  const originalBtnHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> Traitement en cours...`;

  try {
    // Préparation de la configuration de qualité
    const qualityCfg = { mode: state.qualityMode };
    if (state.qualityMode === 'custom') {
      qualityCfg.max_dpi = parseInt(document.getElementById('slider-dpi').value, 10);
      qualityCfg.jpeg_quality = parseInt(document.getElementById('slider-jpeg').value, 10);
      qualityCfg.recompress_images = true;
    }

    // Récupération des paramètres de découpe
    const chunkSize = parseInt(document.getElementById('input-chunk-size').value, 10) || 1;
    const numParts = parseInt(document.getElementById('input-num-parts').value, 10) || 2;
    const rangeString = document.getElementById('input-custom-ranges').value;
    const mergeRanges = document.getElementById('check-merge-ranges').checked;
    const selectionAction = document.querySelector('input[name="selection_action"]:checked')?.value || 'extract_separate';
    const breakpointsStr = document.getElementById('input-breakpoints').value;
    const breakpoints = breakpointsStr ? breakpointsStr.split(',').map(s => parseInt(s.trim(), 10)).filter(n => !isNaN(n)) : [];

    const createSubfolder = document.getElementById('check-subfolder').checked;
    const namingPrefix = document.getElementById('input-naming-prefix').value.trim() || state.currentFile.stem;
    const stripMetadata = document.getElementById('check-strip-meta').checked;

    const checkEncrypt = document.getElementById('check-encrypt-split').checked;
    const outputPassword = checkEncrypt ? document.getElementById('input-split-password').value : null;

    const payload = {
      file_path: state.currentFile.file_path,
      mode: state.splitMode,
      chunk_size: chunkSize,
      num_parts: numParts,
      range_string: rangeString,
      merge_ranges: mergeRanges,
      selected_pages: Array.from(state.selectedPages),
      selection_action: selectionAction,
      breakpoints: breakpoints,
      output_dir_mode: state.outputDirMode,
      custom_output_dir: state.customOutputDir,
      create_subfolder: createSubfolder,
      naming_prefix: namingPrefix,
      rotations: state.pageRotations,
      metadata_config: { strip_metadata: stripMetadata },
      quality_config: qualityCfg,
      output_password: outputPassword
    };

    const resp = await fetch('/api/split', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await resp.json();

    if (!resp.ok || !result.success) {
      throw new Error(result.detail || "Échec du découpage.");
    }

    // Succès : affichage du modal de résultat
    showResultModal({
      title: "Découpage terminé avec succès !",
      filesCount: result.files_count,
      totalPages: result.total_pages_processed,
      outputSizeFormatted: result.total_output_size_formatted,
      outputDir: result.output_dir,
      files: result.files
    });

  } catch (err) {
    showToast(`Erreur : ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalBtnHtml;
  }
}

/* ==========================================================================
   VUE FUSIONNER (MERGE)
   ========================================================================== */
function initMergeView() {
  const btnAdd = document.getElementById('btn-add-merge-files');
  const btnClear = document.getElementById('btn-clear-merge-queue');
  const btnMerge = document.getElementById('btn-execute-merge');

  btnAdd.addEventListener('click', async () => {
    try {
      const resp = await fetch('/api/choose-files', { method: 'POST' });
      const data = await resp.json();
      if (data.selected && data.files) {
        data.files.forEach(item => {
          if (item.info) {
            state.mergeQueue.push({
              file_path: item.file_path,
              file_name: item.info.file_name,
              file_size_formatted: item.info.file_size_formatted,
              page_count: item.info.page_count,
              pages: 'all',
              rotation: 0
            });
          }
        });
        renderMergeQueue();
      }
    } catch (err) {
      showToast("Impossible d'ajouter les fichiers.", "error");
    }
  });

  btnClear.addEventListener('click', () => {
    state.mergeQueue = [];
    renderMergeQueue();
  });

  // Gestion du dossier personnalisé pour la fusion
  const radioMergeFirst = document.getElementById('radio-merge-first-file');
  const radioMergeCustom = document.getElementById('radio-merge-custom');
  const mergeCustomWrap = document.getElementById('merge-custom-folder-wrap');
  const btnBrowseMergeFolder = document.getElementById('btn-browse-merge-folder');

  radioMergeFirst.addEventListener('change', () => {
    if (radioMergeFirst.checked) {
      state.mergeDirMode = 'first_file';
      mergeCustomWrap.style.display = 'none';
    }
  });

  radioMergeCustom.addEventListener('change', () => {
    if (radioMergeCustom.checked) {
      state.mergeDirMode = 'custom';
      mergeCustomWrap.style.display = 'block';
      if (!state.mergeCustomDir) {
        btnBrowseMergeFolder.click();
      }
    }
  });

  btnBrowseMergeFolder.addEventListener('click', async () => {
    try {
      const resp = await fetch('/api/choose-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initial_dir: state.mergeQueue[0]?.file_path || '' })
      });
      const data = await resp.json();
      if (data.selected && data.folder_path) {
        state.mergeCustomDir = data.folder_path;
        document.getElementById('input-merge-custom-folder').value = data.folder_path;
        document.getElementById('label-merge-custom-folder').textContent = data.folder_path;
        radioMergeCustom.checked = true;
        state.mergeDirMode = 'custom';
      }
    } catch (err) {
      showToast("Impossible de sélectionner le dossier.", "error");
    }
  });

  // Mot de passe de fusion
  const checkMergeEncrypt = document.getElementById('check-merge-encrypt');
  const mergePwdWrap = document.getElementById('merge-password-wrap');
  checkMergeEncrypt.addEventListener('change', () => {
    mergePwdWrap.style.display = checkMergeEncrypt.checked ? 'block' : 'none';
  });

  btnMerge.addEventListener('click', executeMerge);
}

function renderMergeQueue() {
  const container = document.getElementById('merge-files-queue');
  const emptyState = document.getElementById('merge-empty-state');
  const summaryBar = document.getElementById('merge-summary-bar');
  const labelFirstFolder = document.getElementById('label-merge-first-folder');

  if (state.mergeQueue.length === 0) {
    container.innerHTML = '';
    container.appendChild(emptyState);
    emptyState.style.display = 'block';
    if (summaryBar) summaryBar.style.display = 'none';
    labelFirstFolder.textContent = "Automatique";
    return;
  }

  emptyState.style.display = 'none';
  if (summaryBar) summaryBar.style.display = 'flex';

  container.innerHTML = '';
  let totalEstimatedPages = 0;

  state.mergeQueue.forEach((item, index) => {
    totalEstimatedPages += item.page_count;

    const row = document.createElement('div');
    row.className = 'merge-item';
    row.innerHTML = `
      <div class="merge-item-order">${index + 1}</div>
      <div class="merge-item-info">
        <div class="merge-item-name" title="${item.file_path}">${item.file_name}</div>
        <div class="merge-item-sub">
          <span>${item.page_count} pages</span>
          <span>•</span>
          <span>${item.file_size_formatted}</span>
        </div>
      </div>
      <div class="merge-item-controls">
        <div style="display:flex; flex-direction:column; gap:2px;">
          <label style="font-size:0.68rem; color:var(--text-muted);">Pages :</label>
          <input type="text" class="merge-pages-input" value="${item.pages}" placeholder="Ex: all ou 1-3" data-idx="${index}">
        </div>
        <div style="display:flex; flex-direction:column; gap:2px;">
          <label style="font-size:0.68rem; color:var(--text-muted);">Rotation :</label>
          <select class="input-select merge-rotate-select" style="padding:4px 8px; font-size:0.75rem;" data-idx="${index}">
            <option value="0" ${item.rotation === 0 ? 'selected' : ''}>0°</option>
            <option value="90" ${item.rotation === 90 ? 'selected' : ''}>90°</option>
            <option value="180" ${item.rotation === 180 ? 'selected' : ''}>180°</option>
            <option value="270" ${item.rotation === 270 ? 'selected' : ''}>270°</option>
          </select>
        </div>
        <button class="btn-icon-mini btn-move-up" title="Monter" ${index === 0 ? 'disabled' : ''}>⬆️</button>
        <button class="btn-icon-mini btn-move-down" title="Descendre" ${index === state.mergeQueue.length - 1 ? 'disabled' : ''}>⬇️</button>
        <button class="btn-icon-mini btn-remove-item" title="Supprimer" style="color:#f87171;">🗑️</button>
      </div>
    `;

    // Événements de contrôle
    row.querySelector('.merge-pages-input').addEventListener('input', (e) => {
      state.mergeQueue[index].pages = e.target.value.trim() || 'all';
    });

    row.querySelector('.merge-rotate-select').addEventListener('change', (e) => {
      state.mergeQueue[index].rotation = parseInt(e.target.value, 10);
    });

    row.querySelector('.btn-move-up').addEventListener('click', () => {
      if (index > 0) {
        const temp = state.mergeQueue[index];
        state.mergeQueue[index] = state.mergeQueue[index - 1];
        state.mergeQueue[index - 1] = temp;
        renderMergeQueue();
      }
    });

    row.querySelector('.btn-move-down').addEventListener('click', () => {
      if (index < state.mergeQueue.length - 1) {
        const temp = state.mergeQueue[index];
        state.mergeQueue[index] = state.mergeQueue[index + 1];
        state.mergeQueue[index + 1] = temp;
        renderMergeQueue();
      }
    });

    row.querySelector('.btn-remove-item').addEventListener('click', () => {
      state.mergeQueue.splice(index, 1);
      renderMergeQueue();
    });

    container.appendChild(row);
  });

  document.getElementById('merge-total-files').textContent = `${state.mergeQueue.length} fichier(s)`;
  document.getElementById('merge-total-pages').textContent = `~${totalEstimatedPages} pages`;

  if (state.mergeQueue.length > 0) {
    const firstDir = state.mergeQueue[0].file_path;
    labelFirstFolder.textContent = firstDir.substring(0, firstDir.lastIndexOf('\\') || firstDir.lastIndexOf('/'));
  }
}

async function executeMerge() {
  if (state.mergeQueue.length === 0) {
    showToast("Veuillez ajouter des fichiers PDF à fusionner.", "error");
    return;
  }

  const btn = document.getElementById('btn-execute-merge');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> Fusion en cours...`;

  try {
    const filename = document.getElementById('input-merge-filename').value.trim() || 'Document_fusionne.pdf';
    const qualityMode = document.getElementById('select-merge-quality').value;
    const stripMeta = document.getElementById('check-merge-strip-meta').checked;
    const checkEncrypt = document.getElementById('check-merge-encrypt').checked;
    const outputPassword = checkEncrypt ? document.getElementById('input-merge-password').value : null;

    const payload = {
      files: state.mergeQueue.map(item => ({
        file_path: item.file_path,
        pages: item.pages || 'all',
        rotation: item.rotation || 0
      })),
      output_dir_mode: state.mergeDirMode,
      custom_output_dir: state.mergeCustomDir,
      output_filename: filename,
      metadata_config: { strip_metadata: stripMeta },
      quality_config: { mode: qualityMode },
      output_password: outputPassword
    };

    const resp = await fetch('/api/merge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const result = await resp.json();

    if (!resp.ok || !result.success) {
      throw new Error(result.detail || "Échec de la fusion.");
    }

    showResultModal({
      title: "Fusion effectuée avec succès !",
      filesCount: 1,
      totalPages: result.total_pages,
      outputSizeFormatted: result.output_size_formatted,
      outputDir: result.output_dir,
      files: [{
        filename: result.output_file,
        file_path: result.output_path,
        file_size_formatted: result.output_size_formatted,
        page_count: result.total_pages
      }]
    });

  } catch (err) {
    showToast(`Erreur : ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

/* ==========================================================================
   VUE ORGANISER & PIVOTER
   ========================================================================== */
function initOrganizeView() {
  document.getElementById('btn-rotate-all-right').addEventListener('click', () => {
    if (!state.currentFile) return;
    for (let i = 0; i < state.currentFile.page_count; i++) {
      rotatePage(i, 90);
    }
    refreshOrganizeView();
  });

  document.getElementById('btn-reset-rotations').addEventListener('click', () => {
    state.pageRotations = {};
    document.querySelectorAll('.page-thumbnail-img').forEach(img => {
      img.style.transform = 'rotate(0deg)';
    });
    refreshOrganizeView();
  });
}

function refreshOrganizeView() {
  const empty = document.getElementById('organize-workspace-empty');
  const content = document.getElementById('organize-workspace-content');
  const container = document.getElementById('organize-thumbnails-grid');

  if (!state.currentFile) {
    empty.style.display = 'block';
    content.style.display = 'none';
    return;
  }

  empty.style.display = 'none';
  content.style.display = 'block';
  container.innerHTML = '';

  for (let i = 0; i < state.currentFile.page_count; i++) {
    const card = document.createElement('div');
    card.className = 'page-card';
    const rot = state.pageRotations[i] || 0;

    card.innerHTML = `
      <div class="page-card-header">
        <span class="page-num-badge">Page ${i + 1}</span>
        <span style="font-size:0.7rem; color:var(--text-muted);">${rot}°</span>
      </div>
      <div class="page-thumbnail-wrap">
        <img class="page-thumbnail-img" src="${state.thumbnails[i] || ''}" style="transform:rotate(${rot}deg);" alt="Page ${i + 1}">
      </div>
      <div class="page-card-actions">
        <button class="btn-icon-mini btn-rotate-org" title="Pivoter +90°" data-page="${i}">
          <svg viewBox="0 0 24 24"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path></svg>
        </button>
      </div>
    `;

    card.querySelector('.btn-rotate-org').addEventListener('click', () => {
      rotatePage(i, 90);
      refreshOrganizeView();
    });

    container.appendChild(card);
  }
}

/* ==========================================================================
   MODALS DE RÉSULTAT ET APERÇU
   ========================================================================== */
function initModals() {
  // Modal de résultat
  const resultModal = document.getElementById('modal-result');
  document.getElementById('btn-close-result-modal').addEventListener('click', () => {
    resultModal.classList.remove('active');
  });
  document.getElementById('btn-dismiss-result').addEventListener('click', () => {
    resultModal.classList.remove('active');
  });

  // Bouton Ouvrir le dossier dans l'Explorateur Windows
  document.getElementById('btn-open-result-folder').addEventListener('click', async () => {
    if (state.lastResultOutputDir) {
      try {
        await fetch('/api/open-folder', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ folder_path: state.lastResultOutputDir })
        });
      } catch (err) {
        showToast("Impossible d'ouvrir l'explorateur.", "error");
      }
    }
  });

  // Modal d'aperçu haute résolution
  const previewModal = document.getElementById('modal-preview');
  document.getElementById('btn-close-preview-modal').addEventListener('click', () => {
    previewModal.classList.remove('active');
  });

  // Fermeture des modaux par clic sur l'arrière-plan ou touche Échap
  [resultModal, previewModal].forEach(m => {
    m.addEventListener('click', (e) => {
      if (e.target === m) m.classList.remove('active');
    });
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      resultModal.classList.remove('active');
      previewModal.classList.remove('active');
    }
  });
}

function showResultModal(data) {
  state.lastResultOutputDir = data.outputDir;

  document.getElementById('result-headline').textContent = data.title;
  document.getElementById('result-subline').textContent = `Enregistré dans : ${data.outputDir}`;

  document.getElementById('stat-files-count').textContent = data.filesCount;
  document.getElementById('stat-total-pages').textContent = data.totalPages;
  document.getElementById('stat-output-size').textContent = data.outputSizeFormatted;

  const filesContainer = document.getElementById('result-files-container');
  filesContainer.innerHTML = '';

  data.files.forEach(f => {
    const item = document.createElement('div');
    item.className = 'result-file-item';
    item.innerHTML = `
      <span style="font-weight:600; color:var(--text-primary);">${f.filename}</span>
      <span style="color:var(--text-muted);">${f.page_count} p. • ${f.file_size_formatted}</span>
    `;
    filesContainer.appendChild(item);
  });

  document.getElementById('modal-result').classList.add('active');
}
