(function () {
  const tg = window.Telegram?.WebApp || null;
  const user = tg?.initDataUnsafe?.user || null;

  function haptic(type = "medium") {
  // Telegram haptics (лучший вариант)
  const hf = tg?.HapticFeedback;
  if (hf) {
    if (type === "select") return hf.selectionChanged();
    if (type === "success" || type === "error" || type === "warning") {
      return hf.notificationOccurred(type);
    }
    return hf.impactOccurred(type); // light | medium | heavy | rigid | soft
  }

  // fallback для браузера (в основном Android)
  if (navigator.vibrate) navigator.vibrate(15);
}

  // === ТЕМЫ (blue / pink) =====================================

  const THEME_KEY = "fambot_theme";
  const themeToggleBtn = document.getElementById("theme-toggle-btn");

  function getSavedTheme() {
    try {
      return localStorage.getItem(THEME_KEY);
    } catch (e) {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch (e) {
      // ignore
    }
  }

  function updateThemeToggleUI(theme) {
    if (!themeToggleBtn) return;

    const isPink = theme === "pink";
    const textEl = themeToggleBtn.querySelector(".theme-toggle-text");

    if (textEl) {
      textEl.textContent = isPink ? "Роза" : "Вода";
    }
    // svg-пути в кружке переключаются через CSS по body.theme-*
  }

  function applyTheme(theme) {
    const normalized = theme === "pink" ? "pink" : "blue";

    document.body.classList.remove("theme-blue", "theme-pink");
    document.body.classList.add("theme-" + normalized);

    updateThemeToggleUI(normalized);
    saveTheme(normalized);
  }

  const initialTheme = getSavedTheme() || "blue";
  applyTheme(initialTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const current = document.body.classList.contains("theme-pink")
        ? "pink"
        : "blue";
      const next = current === "blue" ? "pink" : "blue";
      applyTheme(next);
    });
  }

  if (tg && typeof tg.expand === "function") {
    tg.expand();
  }
  if (tg && typeof tg.expand === "function") {
    tg.expand();
  }

  // помечаем, что запущено внутри Telegram WebApp
  if (tg) {
    document.body.classList.add("tg-app");
    const logo = document.getElementById("tg-top-logo");
    if (logo) logo.classList.remove("hidden");
  }

  // === КЛИКИ МИМО / КЛАВИАТУРА ===============================

  function blurOnOutsideTap(e) {
    // Если клик по инпуту / textarea / contenteditable — игнорируем
    if (e.target.closest("input, textarea, [contenteditable='true']")) {
      return;
    }

    // Если клик по таббару — тоже игнорируем
    if (e.target.closest(".bottom-nav")) {
      return;
    }

    const active = document.activeElement;
    if (
      active &&
      (active.tagName === "INPUT" ||
        active.tagName === "TEXTAREA" ||
        active.isContentEditable)
    ) {
      active.blur();
    }
  }

  document.addEventListener("click", blurOnOutsideTap);
  document.addEventListener("touchstart", blurOnOutsideTap, { passive: true });

  // прячем таббар при поднятой клавиатуре
  const bottomNav = document.querySelector(".bottom-nav");
  let baseViewportHeight =
    window.visualViewport?.height || window.innerHeight;

  function updateKeyboardState() {
    const currentHeight =
      window.visualViewport?.height || window.innerHeight;
    const keyboardNow = baseViewportHeight - currentHeight > 150;

    document.body.classList.toggle("keyboard-open", keyboardNow);
  }

  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", () => {
      updateKeyboardState();
      updateWishlistScrollHeights();
    });
  } else {
    window.addEventListener("resize", () => {
      updateKeyboardState();
      updateWishlistScrollHeights();
    });
  }

  // === DOM-ЭЛЕМЕНТЫ ============================================

  const errorEl = document.getElementById("error");

  // страницы
  const pageMain = document.getElementById("page-main");
  const pageWishlist = document.getElementById("page-wishlist");
  const navMainBtn = document.querySelector('.nav-btn[data-page="main"]');
  const navWishlistBtn = document.querySelector(
    '.nav-btn[data-page="wishlist"]'
  );

  document.querySelectorAll(".bottom-nav .nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => haptic("select"));
});

  // элементы пары / дат / облака
  const pairCard = document.getElementById("pair-card");
  const partnerLine = document.getElementById("partner-line");
  const relSummary = document.getElementById("rel-summary");
  const relProgress = document.getElementById("rel-progress");
  const relMilestone = document.getElementById("rel-milestone");
  const relBig = document.getElementById("rel-big");

  const cloudCard = document.getElementById("cloud-card");
  const cloudCurrent = document.getElementById("cloud-current");

  const wishlistCard = document.getElementById("wishlist-card");

  const noPairCard = document.getElementById("no-pair");
  const partnerNameSpan = document.getElementById("partner-name");
  const partnerAvatar = document.getElementById("partner-avatar"); // может отсутствовать

  // редактирование даты
  const startdateEditBtn = document.getElementById("startdate-edit-btn");
  const startdateInput = document.getElementById("startdate-input");
  const startdateSaveBtn = document.getElementById("startdate-save-btn");

  // редактирование отображаемого имени партнёра
  const partnerNameEditBtn = document.getElementById("partner-name-edit-btn");
  const partnerNameForm = document.getElementById("partner-name-form");
  const partnerNameInput = document.getElementById("partner-name-input");

  // редактирование облака
  const cloudEditBtn = document.getElementById("cloud-edit-btn");
  const cloudInput = document.getElementById("cloud-input");
  const cloudSaveBtn = document.getElementById("cloud-save-btn");

    // формы редактирования даты и облака
  const startdateForm = document.getElementById("startdate-form");
  const cloudForm = document.getElementById("cloud-form");

  // кнопка "Открыть" для облака
  const cloudOpenBtn = document.getElementById("cloud-open-btn");

  // wishlist
  const clearWishlistBtn = document.getElementById("clear-my-wishlist-btn");
  const tabMy = document.getElementById("tab-my");
  const tabPartner = document.getElementById("tab-partner");
  const myListBlock = document.getElementById("my-list-block");
  const partnerListBlock = document.getElementById("partner-list-block");

  const myWishlistEl = document.getElementById("my-wishlist");
  const myEmptyEl = document.getElementById("my-empty");

  const partnerWishlistEl = document.getElementById("partner-wishlist");
  const partnerEmptyEl = document.getElementById("partner-empty");

  const addForm = document.getElementById("add-form");
  const titleInput = document.getElementById("title-input");

  const deletePairBtn = document.getElementById("delete-pair-btn");

  const exportWishlistBtn = document.getElementById("export-wishlist-btn");

  function updateWishlistScrollHeights() {
    const viewportHeight = window.visualViewport?.height || window.innerHeight;
    const bottomNavHeight = bottomNav ? bottomNav.offsetHeight + 26 : 0;

    const fitBlock = (block) => {
      if (!block) return;
      const group = block.querySelector(".wl-group");
      if (!group) return;

      const rect = block.getBoundingClientRect();
      const freeHeight = viewportHeight - rect.top - bottomNavHeight - 16;
      const maxHeight = Math.max(140, Math.floor(freeHeight));
      group.style.maxHeight = `${maxHeight}px`;
    };

    fitBlock(myListBlock);
    fitBlock(partnerListBlock);
  }

  // === STATE ====================================================

  let state = {
    has_pair: false,
    pair: null,
    partner: null,
    my_wishlist: [],
    partner_wishlist: [],
  };

  let sortField = "date";
  let sortDir = "desc";

  function sortedWishlist(list) {
    return [...list].sort((a, b) => {
      let cmp = 0;
      if (sortField === "date") {
        const da = a.created_at ? new Date(a.created_at).getTime() : 0;
        const db = b.created_at ? new Date(b.created_at).getTime() : 0;
        cmp = da - db;
      } else {
        const ta = (a.title || "").toLowerCase();
        const tb = (b.title || "").toLowerCase();
        cmp = ta < tb ? -1 : ta > tb ? 1 : 0;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
  }

  // === УТИЛИТЫ ==================================================

  function showError(msg) {
    if (!errorEl) return;
    errorEl.textContent = msg || "";
    if (!msg) {
      errorEl.classList.add("hidden");
    } else {
      errorEl.classList.remove("hidden");
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("ru-RU", {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  }

  function sanitizeText(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function getPartnerDisplayName() {
    const baseName =
      state.partner?.first_name ||
      state.partner?.username ||
      "Партнёр";
    const alias = state.pair?.partner_alias;
    return alias && alias.trim() ? alias.trim() : baseName;
  }

  function openLink(url) {
    if (!url) return;
    try {
      window.open(url, "_blank");
    } catch (e) {
      console.error(e);
    }
  }

  function openTelegramLink(url) {
    if (!url) return;
    try {
      if (tg && typeof tg.openTelegramLink === "function") {
        tg.openTelegramLink(url);
        return;
      }
      window.open(url, "_blank");
    } catch (e) {
      console.error(e);
    }
  }

  function buildPartnerDiscussLink(item) {
    const partnerUsername = state.partner?.username;
    if (!partnerUsername) return null;

    const title = item?.title || "Без названия";
    const link = item?.url || "не указана";
    const text = `🎁 Хочу обсудить подарок: ${title}\nСсылка: ${link}`;
    return `https://t.me/${encodeURIComponent(partnerUsername)}?text=${encodeURIComponent(
      text
    )}`;
  }

  // === ТАБЫ / НАВИГАЦИЯ =========================================

  function setPage(page) {
    if (!pageMain || !pageWishlist || !navMainBtn || !navWishlistBtn) return;

    if (page === "wishlist") {
      pageMain.classList.add("hidden");
      pageWishlist.classList.remove("hidden");
      navMainBtn.classList.remove("active");
      navWishlistBtn.classList.add("active");
    } else {
      pageMain.classList.remove("hidden");
      pageWishlist.classList.add("hidden");
      navMainBtn.classList.add("active");
      navWishlistBtn.classList.remove("active");
    }

    requestAnimationFrame(updateWishlistScrollHeights);
  }

  if (navMainBtn) {
    navMainBtn.addEventListener("click", () => setPage("main"));
  }

  if (navWishlistBtn) {
    navWishlistBtn.addEventListener("click", () => setPage("wishlist"));
  }

  function renderTabs() {
    if (!tabMy || !tabPartner || !myListBlock || !partnerListBlock) return;

    const myHidden = myListBlock.classList.contains("hidden");

    if (myHidden) {
      tabMy.classList.remove("active");
      tabPartner.classList.add("active");
      if (clearWishlistBtn) {
        clearWishlistBtn.classList.add("hidden");
      }
    } else {
      tabMy.classList.add("active");
      tabPartner.classList.remove("active");
      if (clearWishlistBtn) {
        clearWishlistBtn.classList.remove("hidden");
      }
    }
  }

  // === ОТРИСОВКА ПАРЫ / ОТНОШЕНИЙ ===============================

  function renderPairBlock() {
    if (
      !pairCard ||
      !cloudCard ||
      !wishlistCard ||
      !noPairCard ||
      !partnerLine ||
      !relSummary ||
      !relProgress ||
      !relMilestone ||
      !relBig ||
      !cloudCurrent
    ) {
      return;
    }

    if (!state.has_pair) {
      pairCard.classList.add("hidden");
      cloudCard.classList.add("hidden");
      wishlistCard.classList.add("hidden");
      noPairCard.classList.remove("hidden");
      return;
    }

    noPairCard.classList.add("hidden");
    pairCard.classList.remove("hidden");
    cloudCard.classList.remove("hidden");
    wishlistCard.classList.remove("hidden");

    if (state.partner && state.partner.id) {
      const name = getPartnerDisplayName();
      const partnerUsername =
          state.partner.username ||
          "t.me";

      if (partnerNameSpan) {
        partnerNameSpan.textContent = name;
      }

      if (state.partner.photo_url && partnerAvatar) {
        partnerAvatar.src = state.partner.photo_url;
        partnerAvatar.classList.remove("hidden");
      } else if (partnerAvatar) {
        partnerAvatar.classList.add("hidden");
      }

      partnerLine.innerHTML = `<a href="https://t.me/${partnerUsername}" target="_blank" class="user-ref"><b>${name}</b></a>`;
    } else {
      partnerLine.textContent = "Пара пока не найдена";
      if (partnerAvatar) {
        partnerAvatar.classList.add("hidden");
      }
    }

    const stats = state.pair?.start_stats;

    if (!stats || stats.future) {
      relSummary.innerHTML =
        "Дата начала отношений ещё не установлена.";
      relProgress.textContent = "";
      relMilestone.textContent = "";
      relBig.textContent = "";

      cloudCurrent.textContent =
        state.pair?.cloud_url || "Пока пусто";
      return;
    }

    relSummary.innerHTML = `
      <div class="pair-line"><hr class="hr-rel"></div>
      <div class="pair-line"><span class="emoji">📅</span> <strong>Дата начала:</strong> ${formatDate(stats.start_date_iso)}</div>
      <div class="pair-line"><span class="emoji">💞</span> <strong>Вместе:</strong> ${stats.days_together} д.</div>
      <div class="pair-line"><strong>Это уже: ${stats.years} г. ${stats.months} мес.</strong></div>
      <div class="pair-line"><hr class="hr-rel"></div>
    `;

    relProgress.innerHTML = `
      <div class="rel-progress-line">
        <span class="emoji">🥳</span>
        <span><b>До следующей годовщины: ${stats.days_until_next} дней</b></span>
      </div>
      <div class="rel-progress-line">
        <span class="emoji">🎯</span>
        <span><i>Пройдено <b>${stats.percent_to_next}%</b> текущего года вместе</i></span>
      </div>
      <div class="pair-line"><hr class="hr-rel"></div>
    `;

    if (stats.next_milestone_days) {
      relMilestone.innerHTML = `<b>Красивая дата:</b> ${stats.next_milestone_days} дней вместе через ${stats.next_milestone_days_left} дней`;
    } else {
      relMilestone.textContent = "";
    }

    if (stats.next_big_year) {
      relBig.innerHTML = `<b>Большой юбилей:</b> ${stats.next_big_year} лет через ${stats.next_big_year_days_left} дней`;
    } else {
      relBig.textContent = "";
    }

    cloudCurrent.textContent =
      state.pair?.cloud_url || "Пока пусто";
    if (cloudEditBtn) {
      const hasUrl = !!state.pair?.cloud_url;
      cloudEditBtn.textContent = hasUrl ? "Изменить ссылку" : "Добавить ссылку";
    }
    // управление видимостью кнопки "Открыть"
    if (cloudOpenBtn) {
      const hasUrl = !!state.pair?.cloud_url;
      if (hasUrl) {
        cloudOpenBtn.classList.remove("hidden");
      } else {
        cloudOpenBtn.classList.add("hidden");
      }
    }
  }

  // === WISHLIST РЕНДЕР ==========================================

  function makeWishlistItemHTML(item, canEdit) {
    const titleHtml = sanitizeText(item.title || "");
    const hasLink = !!item.url;
    const discussUrl = !canEdit ? buildPartnerDiscussLink(item) : null;

    const linkPart = hasLink
      ? `<button class="wl-link-btn" data-url="${encodeURI(
          item.url
        )}">Открыть</button>`
      : canEdit
      ? `<button class="wish-add-link" type="button">Добавить ссылку</button>`
      : "";

    const editPart = canEdit
      ? `<br><button class="wish-delete" type="button" aria-label="Удалить">Удалить</button>`
      : "";

    const discussPart = discussUrl
      ? `<button class="wl-chat-btn" data-chat-url="${discussUrl}">Обсудить</button>`
      : "";

    return `
      <div class="wl-main">
        <div class="wl-text">
          <div class="wl-title wish-title">${titleHtml}</div>
          
        </div>
        <div class="wl-actions">
          ${linkPart}
          ${discussPart}
          ${editPart}
        </div>
      </div>
    `;
  }

  function renderWishlist() {
    if (
      !myWishlistEl ||
      !myEmptyEl ||
      !partnerWishlistEl ||
      !partnerEmptyEl
    ) {
      return;
    }

    // мой список
    myWishlistEl.innerHTML = "";
    if (!state.my_wishlist || state.my_wishlist.length === 0) {
      myEmptyEl.classList.remove("hidden");
    } else {
      myEmptyEl.classList.add("hidden");

      sortedWishlist(state.my_wishlist).forEach((item) => {
        const li = document.createElement("li");
        li.className = "wl-item";
        li.dataset.id = item.id;
        li.innerHTML = makeWishlistItemHTML(item, true);
        myWishlistEl.appendChild(li);
      });
    }

    // список партнёра
    partnerWishlistEl.innerHTML = "";
    if (!state.partner_wishlist || state.partner_wishlist.length === 0) {
      partnerEmptyEl.classList.remove("hidden");
    } else {
      partnerEmptyEl.classList.add("hidden");

      sortedWishlist(state.partner_wishlist).forEach((item) => {
        const li = document.createElement("li");
        li.className = "wl-item";
        li.dataset.id = item.id;
        li.innerHTML = makeWishlistItemHTML(item, false);
        partnerWishlistEl.appendChild(li);
      });
    }

    requestAnimationFrame(updateWishlistScrollHeights);
  }

  // === API-ХЕЛПЕР ===============================================

  async function apiPost(path, payload) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    let data;
    try {
      data = await res.json();
    } catch (e) {
      throw new Error("INVALID_JSON");
    }

    // если backend не прислал ok — считаем, что всё ок, если HTTP-статус ok
    const okField =
      typeof data.ok === "undefined" ? true : !!data.ok;

    if (!res.ok || !okField) {
      const err =
        (data && data.error) || `HTTP_${res.status}`;
      throw new Error(err);
    }

    return data;
  }

  // === INIT =====================================================

  async function init() {
    if (!user) {
      showError("Не удалось получить пользователя из Telegram WebApp API.");
      return;
    }

    try {
      const data = await apiPost("/api/init", { user });
      state.has_pair = data.has_pair;
      state.pair = data.pair;
      state.partner = data.partner;
      state.my_wishlist = data.my_wishlist || [];
      state.partner_wishlist = data.partner_wishlist || [];

      if (myListBlock && partnerListBlock) {
        myListBlock.classList.add("hidden");
        partnerListBlock.classList.remove("hidden");
      }
      renderTabs();
      renderPairBlock();
      renderWishlist();
      renderTabs();
    } catch (e) {
      console.error(e);
      showError("Ошибка инициализации: " + e.message);
    }
  }

  // === ОБРАБОТЧИКИ UI ==========================================

  if (tabMy && myListBlock && partnerListBlock) {
    tabMy.addEventListener("click", () => {
      myListBlock.classList.remove("hidden");
      partnerListBlock.classList.add("hidden");
      renderTabs();
      requestAnimationFrame(updateWishlistScrollHeights);
    });
  }

  if (tabPartner && myListBlock && partnerListBlock) {
    tabPartner.addEventListener("click", () => {
      myListBlock.classList.add("hidden");
      partnerListBlock.classList.remove("hidden");
      renderTabs();
      requestAnimationFrame(updateWishlistScrollHeights);
    });
  }

  // добавление желания
  if (addForm && titleInput) {
    addForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const title = titleInput.value.trim();
      if (!title) return;

      try {
        const data = await apiPost("/api/wishlist/add", { user, title });
        state.my_wishlist.push(data.item);
        titleInput.value = "";
        renderWishlist();
      } catch (e) {
        console.error(e);
        showError("Не удалось добавить желание: " + e.message);
      }
    });
  }

  function getCurrentWishlistTarget() {
    if (!myListBlock || !partnerListBlock) return "me";
    return myListBlock.classList.contains("hidden") ? "partner" : "me";
  }

  if (exportWishlistBtn) {
  exportWishlistBtn.addEventListener("click", async () => {
    const target = getCurrentWishlistTarget(); // "me" | "partner"

    try {
      await apiPost("/api/wishlist/send_to_bot", {
        user,
        target,
      });
      haptic("success");
    } catch (e) {
      console.error(e);
      showError("Не удалось отправить список в бот: " + e.message);
      haptic("error");
    }
  });
}

  // клики по моему wishlist
  if (myWishlistEl) {
    myWishlistEl.addEventListener("click", async (e) => {
      const li = e.target.closest("li");
      if (!li) return;
      const id = parseInt(li.dataset.id, 10);
      if (!id) return;

      // удаление
      if (e.target.closest(".wish-delete")) {
        if (!confirm("Удалить это желание?")) return;
        try {
          await apiPost("/api/wishlist/delete", { user, item_id: id });
          state.my_wishlist = state.my_wishlist.filter((i) => i.id !== id);
          renderWishlist();
        } catch (err) {
          console.error(err);
          showError("Ошибка удаления: " + err.message);
        }
        return;
      }

      // добавить/обновить ссылку
      if (e.target.classList.contains("wish-add-link")) {
        const url = prompt("Вставьте ссылку на товар\nНапример: https://example.com");
        if (!url) return;
        try {
          await apiPost("/api/wishlist/set_link", { user, item_id: id, url });
          const item = state.my_wishlist.find((i) => i.id === id);
          if (item) item.url = url;
          renderWishlist();
        } catch (err) {
          console.error(err);
          showError("Ошибка сохранения ссылки: " + err.message);
        }
        return;
      }
    });
  }

  // клики по wishlist партнёра (открытие ссылок)
  if (partnerWishlistEl) {
    partnerWishlistEl.addEventListener("click", (e) => {
      const chatBtn = e.target.closest(".wl-chat-btn");
      if (chatBtn) {
        const chatUrl = chatBtn.dataset.chatUrl;
        if (!chatUrl) {
          showError("У партнера нет @username, не могу открыть личный чат.");
          haptic("warning");
          return;
        }
        openTelegramLink(chatUrl);
        haptic("success");
        return;
      }

      const btn = e.target.closest(".wl-link-btn");
      if (!btn) return;
      const url = btn.dataset.url;
      if (url) openLink(url);
    });
  }

  if (myWishlistEl) {
    myWishlistEl.addEventListener("click", (e) => {
      const btn = e.target.closest(".wl-link-btn");
      if (!btn) return;
      const url = btn.dataset.url;
      if (url) openLink(url);
    });
  }

  // облако


  if (cloudEditBtn && cloudForm && cloudInput) {
    cloudEditBtn.addEventListener("click", () => {
      cloudForm.classList.toggle("hidden");
      if (!cloudForm.classList.contains("hidden")) {
        cloudInput.value = state.pair?.cloud_url || "";
        cloudInput.focus();
      }
    });
  }


  if (cloudOpenBtn) {
    cloudOpenBtn.addEventListener("click", () => {
      const url = state.pair?.cloud_url;
      if (!url) {
        showError("Ссылка на диск не указана.");
        return;
      }
      openLink(url);
    });
  }




  // дата начала отношений
  if (startdateEditBtn && startdateForm && startdateInput) {
    startdateEditBtn.addEventListener("click", () => {
      startdateForm.classList.toggle("hidden");
      if (!startdateForm.classList.contains("hidden")) {
        if (state.pair?.start_stats?.start_date_human) {
          startdateInput.value = state.pair.start_stats.start_date_human;
        }
        startdateInput.focus();
      }
    });
  }

  if (startdateForm && startdateInput) {
    startdateForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const dateStr = startdateInput.value.trim();
      if (!dateStr) {
        showError("Введите дату в формате ДД.ММ.ГГГГ");
        return;
      }
      try {
        const data = await apiPost("/api/startdate/set", {
          user,
          date_str: dateStr,
        });
        if (!state.pair) state.pair = {};
        state.pair.start_date = data.start_date;
        state.pair.start_stats = data.start_stats;
        renderPairBlock();
        startdateForm.classList.add("hidden");
      } catch (e) {
        console.error(e);
        let msg = "Не удалось сохранить дату: ";
        if (e.message === "BAD_FORMAT") msg += "ожидается формат ДД.ММ.ГГГГ";
        else if (e.message === "INVALID_DATE") msg += "некорректная дата";
        else msg += e.message;
        showError(msg);
      }
    });
  }

  // отображаемое имя партнёра (без изменения ссылки на чат)
  if (partnerNameEditBtn && partnerNameForm && partnerNameInput) {
    partnerNameEditBtn.addEventListener("click", () => {
      partnerNameForm.classList.toggle("hidden");
      if (!partnerNameForm.classList.contains("hidden")) {
        partnerNameInput.value = getPartnerDisplayName();
        partnerNameInput.focus();
      }
    });
  }

  if (partnerNameForm && partnerNameInput) {
    partnerNameForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const alias = partnerNameInput.value.trim();
      if (!state.partner?.id) {
        showError("Партнёр не найден.");
        return;
      }
      try {
        const data = await apiPost("/api/partner_alias/set", {
          user,
          alias,
        });
        if (!state.pair) state.pair = {};
        state.pair.partner_alias = data.alias || null;
      } catch (err) {
        console.error(err);
        showError("Не удалось сохранить имя партнёра: " + err.message);
        return;
      }
      renderPairBlock();
      partnerNameForm.classList.add("hidden");
    });
  }

  if (cloudForm && cloudInput) {
    cloudForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const url = cloudInput.value.trim();
      try {
        await apiPost("/api/cloud/set", { user, url });
        if (!state.pair) state.pair = {};
        state.pair.cloud_url = url || null;
        renderPairBlock();
        cloudForm.classList.add("hidden");
      } catch (e) {
        console.error(e);
        showError("Не удалось сохранить ссылку на диск: " + e.message);
      }
    });
  }

  // очистка моего wishlist целиком
  if (clearWishlistBtn) {
    clearWishlistBtn.addEventListener("click", async () => {
      if (!state.my_wishlist || state.my_wishlist.length === 0) {
        return;
      }

      if (!confirm("Очистить весь ваш список желаний?")) {
        return;
      }

      try {
        await apiPost("/api/wishlist/clear", { user });
        state.my_wishlist = [];
        renderWishlist();
      } catch (e) {
        console.error(e);
        showError("Не удалось очистить список: " + e.message);
      }
    });
  }

  // удаление пары
  if (deletePairBtn) {
    deletePairBtn.addEventListener("click", async () => {
      if (
        !confirm(
          "Точно разорвать пару? Будут удалены все ваши данные и настройки."
        )
      ) {
        return;
      }
      try {
        await apiPost("/api/pair/delete", { user });
        state.has_pair = false;
        state.pair = null;
        state.partner = null;
        state.my_wishlist = [];
        state.partner_wishlist = [];
        renderPairBlock();
        renderWishlist();
        renderTabs();
      } catch (e) {
        console.error(e);
        showError("Ошибка удаления пары: " + e.message);
      }
    });
  }

  // === СОРТИРОВКА WISHLIST =====================================

  const sortDateBtn = document.getElementById("sort-date-btn");
  const sortTitleBtn = document.getElementById("sort-title-btn");

  function updateSortUI() {
    [sortDateBtn, sortTitleBtn].forEach((btn) => {
      if (!btn) return;
      const field = btn.dataset.field;
      const arrow = btn.querySelector(".sort-arrow");
      const isActive = field === sortField;
      btn.classList.toggle("wl-sort-active", isActive);
      if (arrow) arrow.textContent = (isActive && sortDir === "desc") ? "↓" : "↑";
    });
  }

  function handleSortClick(field) {
    if (sortField === field) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortField = field;
      sortDir = field === "date" ? "desc" : "asc";
    }
    updateSortUI();
    renderWishlist();
    haptic("select");
  }

  if (sortDateBtn) sortDateBtn.addEventListener("click", () => handleSortClick("date"));
  if (sortTitleBtn) sortTitleBtn.addEventListener("click", () => handleSortClick("title"));

  // старт
  init();
})();