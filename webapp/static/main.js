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

  const THEME_BG_COLOR = {
    blue: "#e5f4ff",
    pink: "#ffebf3",
  };

  function applyTheme(theme) {
    const normalized = theme === "pink" ? "pink" : "blue";
    const bgColor = THEME_BG_COLOR[normalized];

    document.body.classList.remove("theme-blue", "theme-pink");
    document.body.classList.add("theme-" + normalized);

    // html-фон совпадает с верхним цветом градиента — при overscroll не видно Telegram
    document.documentElement.style.background = bgColor;

    // Telegram рисует свой фон за WebApp — говорим ему использовать наш цвет
    if (tg && typeof tg.setBackgroundColor === "function") {
      tg.setBackgroundColor(bgColor);
    }
    // сверху при overscroll просвечивает headerColor, поэтому его тоже меняем
    if (tg && typeof tg.setHeaderColor === "function") {
      tg.setHeaderColor(bgColor);
    }

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
  if (tg && typeof tg.disableVerticalSwipes === "function") {
    tg.disableVerticalSwipes();
  }

  // помечаем, что запущено внутри Telegram WebApp
  if (tg) {
    document.body.classList.add("tg-app");
    const logo = document.getElementById("tg-top-logo");
    // логотип показываем только в полноэкранном режиме (не из меню)
    if (logo && tg.isFullscreen) logo.classList.remove("hidden");
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
  const pageNotes = document.getElementById("page-notes");
  const navMainBtn = document.querySelector('.nav-btn[data-page="main"]');
  const navWishlistBtn = document.querySelector('.nav-btn[data-page="wishlist"]');
  const navNotesBtn = document.querySelector('.nav-btn[data-page="notes"]');

  // заметки
  const notesCard = document.getElementById("notes-card");
  const notesNoPair = document.getElementById("notes-no-pair");
  const notesGroup = document.getElementById("notes-group");
  const notesListEl = document.getElementById("notes-list");
  const notesEmptyEl = document.getElementById("notes-empty");
  const notesAddForm = document.getElementById("notes-add-form");
  const notesInput = document.getElementById("notes-input");

  document.querySelectorAll(".bottom-nav .nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => haptic("select"));
});

  // элементы пары / дат / облака
  const WISHES = [
    "Пусть ваша любовь с каждым годом становится глубже, а счастье — тише и надёжнее.",
    "Желаю вам всегда находить повод улыбнуться друг другу — даже в самые обычные дни.",
    "Пусть дом ваш будет наполнен теплом, смехом и запахом чего-то вкусного.",
    "Любите друг друга так, чтобы даже молчание вместе было уютным.",
    "Желаю вам путешествий, которые вы будете вспоминать всю жизнь.",
    "Пусть разногласия заканчиваются объятиями, а не обидами.",
    "Желаю вам быть лучшими друзьями — не только влюблёнными.",
    "Пусть ваша история любви будет той, которую захочется рассказывать внукам.",
    "Желаю вам уважать молчание друг друга так же, как и слова.",
    "Пусть каждое утро начинается с благодарности за то, что вы вместе.",
    "Желаю вам смеяться над одними и теми же глупостями через двадцать лет.",
    "Пусть ваша любовь не нуждается в доказательствах — она просто есть.",
    "Желаю вам танцевать на кухне без всякого повода.",
    "Пусть вы никогда не перестанете удивлять друг друга.",
    "Желаю вам мягких слов в трудные минуты и крепких объятий, когда слова не нужны.",
    "Пусть ваш союз будет тихим портом в любую бурю.",
    "Желаю вам доверять друг другу безоговорочно — это редкое сокровище.",
    "Пусть совместный быт станет не рутиной, а ежедневным маленьким приключением.",
    "Желаю вам встречать закаты вместе — сначала с бокалом вина, потом с чашкой чая.",
    "Пусть ваши мечты совпадают — а если нет, пусть вы умеете договариваться.",
    "Желаю вам никогда не ложиться спать, не помирившись.",
    "Пусть каждый день приносит что-то, за что вы благодарны друг другу.",
    "Желаю вам обниматься крепко и часто — это лечит.",
    "Пусть ваши планы сбываются, а неожиданности оказываются приятными.",
    "Желаю вам быть командой, которая не проигрывает — потому что поддерживает друг друга.",
    "Пусть любовь делает вас лучшими версиями самих себя.",
    "Желаю вам совместных традиций, которые станут вашей тайной историей.",
    "Пусть ваши объятия всегда пахнут домом.",
    "Желаю вам не бояться говорить «прости» первым.",
    "Пусть между вами всегда будет место для шутки — даже в серьёзный момент.",
    "Желаю вам совместных поездок, где хоть раз заблудитесь и найдёте что-то прекрасное.",
    "Пусть ваш холодильник всегда будет полон — а сердца ещё больше.",
    "Желаю вам смотреть друг на друга с теплом и через тридцать лет.",
    "Пусть ваш союз будет прочнее, чем икея — и без лишних инструкций.",
    "Желаю вам принимать недостатки друг друга как часть любимого пейзажа.",
    "Пусть первый кофе утром будет сделан с любовью — и выпит вместе.",
    "Желаю вам не терять интереса друг к другу никогда.",
    "Пусть ваши ссоры будут редкими, а примирения — страстными.",
    "Желаю вам поддерживать мечты друг друга, даже самые странные.",
    "Пусть дом наполняется детским смехом — или хотя бы вашим собственным.",
    "Желаю вам быть друг для друга якорем и парусом одновременно.",
    "Пусть вы никогда не забываете, почему влюбились.",
    "Желаю вам тихих вечеров и громких праздников в равной мере.",
    "Пусть ваш GPS всегда ведёт в одном направлении — домой, к друг другу.",
    "Желаю вам спорить только о том, что смотреть вечером.",
    "Пусть нежность в ваших отношениях живёт дольше влюблённости.",
    "Желаю вам совместных проектов — будь то ремонт или огород.",
    "Пусть каждое «я люблю тебя» звучит так, будто говорится впервые.",
    "Желаю вам не принимать друг друга как должное — ни единого дня.",
    "Пусть ваша любовь будет тихой рекой, а не только бурным водопадом.",
    "Желаю вам находить романтику в обычных вещах — в пробке, в очереди, в дожде.",
    "Пусть вы всегда знаете, что сказать, когда другому грустно.",
    "Желаю вам вместе встречать зиму у камина и лето у моря.",
    "Пусть ваш брак будет не финишной лентой, а стартом.",
    "Желаю вам не переставать ухаживать друг за другом — это важнее цветов.",
    "Пусть вы умеете просить о помощи и с радостью помогать.",
    "Желаю вам нечаянных поцелуев в середине обычного дня.",
    "Пусть вокруг вас будут люди, которые рады вашему счастью.",
    "Желаю вам делиться не только радостями, но и трудностями — пополам.",
    "Пусть ваша любовь переживёт ремонт, переезд и IKEA в одни выходные.",
    "Желаю вам сохранить детское восхищение друг другом.",
    "Пусть даже совместная готовка в маленькой кухне приносит удовольствие.",
    "Желаю вам праздновать маленькие победы не меньше, чем большие.",
    "Пусть ваши взгляды говорят больше, чем слова.",
    "Желаю вам не бояться перемен — вместе любые перемены к лучшему.",
    "Пусть ваша совместная жизнь будет такой, что завидуют тихо и по-доброму.",
    "Желаю вам успевать говорить «спасибо» за мелочи — именно из них жизнь.",
    "Пусть вы всегда найдёте время для свидания, даже прожив вместе двадцать лет.",
    "Желаю вам уметь молчать вместе — это высшая близость.",
    "Пусть ваши праздники будут шумными, а будни — уютными.",
    "Желаю вам встречать любые трудности лицом к лицу — а не друг против друга.",
    "Пусть вы никогда не перестанете делать друг другу сюрпризы.",
    "Желаю вам быть той парой, на которую смотрят и улыбаются незнакомые люди.",
    "Пусть каждая годовщина будет поводом вспомнить, как всё начиналось.",
    "Желаю вам совместных походов в кино — даже если кто-то уснёт на половине.",
    "Пусть ваши разные вкусы дополняют, а не мешают друг другу.",
    "Желаю вам держаться за руки — и в самолёте, и в больнице, и просто так.",
    "Пусть ваша любовь будет практичной — той, что помогает жить, а не только красивой.",
    "Желаю вам читать книги вслух и слушать музыку вместе.",
    "Пусть ваши родители гордятся тем, что получилось.",
    "Желаю вам подушек побольше и одеяла на двоих.",
    "Пусть вы будете бережны с настроением друг друга в конце тяжёлого дня.",
    "Желаю вам совместного словаря — тех слов и шуток, которые понятны только вам.",
    "Пусть ваши дети — если они будут — видят, как родители любят друг друга.",
    "Желаю вам уметь прощать — быстро и без условий.",
    "Пусть даже скучный вторник с вами становится особенным.",
    "Желаю вам всегда иметь, куда вернуться — и к кому.",
    "Пусть ваши объятия в аэропорту будут такими, как в кино.",
    "Желаю вам быть честными — даже когда это неудобно.",
    "Пусть любовь не требует от вас быть идеальными.",
    "Желаю вам вместе стареть — весело, достойно и держась за руки.",
    "Пусть ваши воспоминания будут богаче, чем любое имущество.",
    "Желаю вам видеть в партнёре лучшее — особенно тогда, когда сам он этого не видит.",
    "Пусть ваша любовь будет той, которая придаёт сил, а не отнимает.",
    "Желаю вам засыпать с улыбкой — потому что рядом тот, кто нужен.",
    "Пусть каждый ваш день будет достаточно хорош, чтобы его помнить.",
    "Желаю вам оставаться собой — и любить друг друга именно такими.",
    "Пусть ваша история любви пишется медленно, подробно и с хорошим концом.",
    "Желаю вам быть друг для друга и праздником, и тихой гаванью.",
    "Пусть ваша любовь живёт дольше вас — в детях, воспоминаниях и улыбках тех, кто вас знал.",
  ];

  const HEARTS = ["🩷","❤️","💜","💕","💞","💓","💗","💖","💝","💟"];

  const wishCard = document.getElementById("wish-card");
  const wishText = document.getElementById("wish-text");
  if (wishText) {
    const heart = HEARTS[Math.floor(Math.random() * HEARTS.length)];
    const wish = WISHES[Math.floor(Math.random() * WISHES.length)];
    wishText.textContent = heart + " «" + wish + "»";
  }

  const anniversaryBanner = document.getElementById("anniversary-banner");
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

  const faqBtn = document.getElementById("faq-btn");
  const faqOverlay = document.getElementById("faq-overlay");
  const faqSheet = faqOverlay && faqOverlay.querySelector(".faq-sheet");
  const faqSheetHeader = document.getElementById("faq-sheet-header");

  function openFaq() {
    if (!faqOverlay || !faqSheet) return;
    document.body.style.overflow = "hidden";
    faqSheet.style.transition = "none";
    faqSheet.style.transform = "translateY(100%)";
    faqOverlay.classList.remove("hidden");
    requestAnimationFrame(() => {
      faqSheet.style.transition = "transform 0.3s ease";
      faqSheet.style.transform = "translateY(0)";
    });
  }

  function closeFaq() {
    if (!faqOverlay || !faqSheet) return;
    faqSheet.style.transition = "transform 0.3s ease";
    faqSheet.style.transform = "translateY(100%)";
    setTimeout(() => {
      faqOverlay.classList.add("hidden");
      document.body.style.overflow = "";
    }, 300);
  }

  faqBtn && faqBtn.addEventListener("click", () => { haptic("light"); openFaq(); });
  faqOverlay && faqOverlay.addEventListener("click", (e) => {
    if (e.target === faqOverlay) closeFaq();
  });

  // свайп вниз за пальцем
  if (faqSheetHeader && faqSheet) {
    let startY = 0, lastT = 0;

    faqSheetHeader.addEventListener("touchstart", (e) => {
      startY = e.touches[0].clientY;
      lastT = Date.now();
      faqSheet.style.transition = "none";
    }, { passive: true });

    faqSheetHeader.addEventListener("touchmove", (e) => {
      e.preventDefault();
      const dy = e.touches[0].clientY - startY;
      lastT = Date.now();
      if (dy > 0) faqSheet.style.transform = `translateY(${dy}px)`;
    }, { passive: false });

    faqSheetHeader.addEventListener("touchend", (e) => {
      const dy = e.changedTouches[0].clientY - startY;
      const dt = Date.now() - lastT;
      const velocity = dt > 0 ? dy / dt : 0;
      if (dy > 120 || velocity > 0.5) {
        haptic("light");
        closeFaq();
      } else {
        faqSheet.style.transition = "transform 0.25s ease";
        faqSheet.style.transform = "translateY(0)";
      }
    }, { passive: true });
  }

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

  function updateNotesScrollHeight() {
    if (!notesGroup) return;
    const viewportHeight = window.visualViewport?.height || window.innerHeight;
    const bottomNavHeight = bottomNav ? bottomNav.offsetHeight + 26 : 0;
    const rect = notesGroup.getBoundingClientRect();
    const freeHeight = viewportHeight - rect.top - bottomNavHeight - 16;
    notesGroup.style.maxHeight = `${Math.max(140, Math.floor(freeHeight))}px`;
  }

  // === STATE ====================================================

  let state = {
    has_pair: false,
    pair: null,
    partner: null,
    my_wishlist: [],
    partner_wishlist: [],
    notes: [],
  };

  let sortField = "priority";
  let sortDir = "desc";

  const PRIORITY_ORDER = { high: 3, medium: 2, low: 1 };

  function cmpPriority(a, b) {
    return (PRIORITY_ORDER[b.priority] || 2) - (PRIORITY_ORDER[a.priority] || 2);
  }

  function cmpTitle(a, b) {
    const ta = (a.title || "").toLowerCase();
    const tb = (b.title || "").toLowerCase();
    return ta < tb ? -1 : ta > tb ? 1 : 0;
  }

  function cmpDate(a, b) {
    const da = a.created_at ? new Date(a.created_at).getTime() : 0;
    const db = b.created_at ? new Date(b.created_at).getTime() : 0;
    return db - da; // новые первыми по умолчанию
  }

  function sortedWishlist(list) {
    const ORDER = {
      priority: [cmpPriority, cmpTitle, cmpDate],
      title:    [cmpTitle, cmpPriority, cmpDate],
      date:     [cmpDate, cmpPriority, cmpTitle],
    };
    const comparators = ORDER[sortField] || ORDER.priority;

    return [...list].sort((a, b) => {
      for (let i = 0; i < comparators.length; i++) {
        let cmp = comparators[i](a, b);
        // направление применяется только к первичному полю
        if (i === 0) cmp = sortDir === "asc" ? -cmp : cmp;
        if (cmp !== 0) return cmp;
      }
      return 0;
    });
  }

  // === УТИЛИТЫ ==================================================

  function pluralRu(n, forms) {
    // forms: [1 год, 2 года, 5 лет]
    const abs = Math.abs(n);
    const mod10 = abs % 10;
    const mod100 = abs % 100;
    if (mod100 >= 11 && mod100 <= 19) return forms[2];
    if (mod10 === 1) return forms[0];
    if (mod10 >= 2 && mod10 <= 4) return forms[1];
    return forms[2];
  }

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
    if (!pageMain || !pageWishlist) return;

    pageMain.classList.toggle("hidden", page !== "main");
    pageWishlist.classList.toggle("hidden", page !== "wishlist");
    if (pageNotes) pageNotes.classList.toggle("hidden", page !== "notes");

    document.querySelectorAll(".bottom-nav .nav-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.page === page);
    });

    requestAnimationFrame(() => {
      updateWishlistScrollHeights();
      updateNotesScrollHeight();
    });
  }

  if (navMainBtn) {
    navMainBtn.addEventListener("click", () => setPage("main"));
  }

  if (navWishlistBtn) {
    navWishlistBtn.addEventListener("click", () => setPage("wishlist"));
  }

  if (navNotesBtn) {
    navNotesBtn.addEventListener("click", () => setPage("notes"));
  }

  // свайп влево/вправо для смены страницы
  (function () {
    let startX = 0, startY = 0, dirLocked = null;

    document.addEventListener("touchstart", (e) => {
      // не перехватывать если FAQ открыт или свайп в элементе вишлиста или инпут
      if (faqOverlay && !faqOverlay.classList.contains("hidden")) return;
      if (e.target.closest("input, textarea, [contenteditable]")) return;
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      dirLocked = null;
    }, { passive: true });

    document.addEventListener("touchmove", (e) => {
      if (faqOverlay && !faqOverlay.classList.contains("hidden")) return;
      if (dirLocked === "vertical") return;
      if (e.target.closest(".wl-swipe-track")) return;

      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;

      if (dirLocked === null) {
        if (Math.abs(dx) < 8 && Math.abs(dy) < 8) return;
        dirLocked = Math.abs(dx) > Math.abs(dy) ? "horizontal" : "vertical";
      }

      if (dirLocked === "horizontal") e.preventDefault();
    }, { passive: false });

    document.addEventListener("touchend", (e) => {
      if (dirLocked !== "horizontal") return;
      if (faqOverlay && !faqOverlay.classList.contains("hidden")) return;

      const dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) < 60) return;

      const onMain = !pageMain.classList.contains("hidden");
      const onWishlist = pageWishlist && !pageWishlist.classList.contains("hidden");
      const onNotes = pageNotes && !pageNotes.classList.contains("hidden");

      if (dx < 0 && onMain) { haptic("select"); setPage("wishlist"); }
      else if (dx < 0 && onWishlist) { haptic("select"); setPage("notes"); }
      else if (dx > 0 && onNotes) { haptic("select"); setPage("wishlist"); }
      else if (dx > 0 && onWishlist) { haptic("select"); setPage("main"); }
    }, { passive: true });
  })();

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
      wishCard && wishCard.classList.add("hidden");
      anniversaryBanner && anniversaryBanner.classList.add("hidden");
      pairCard.classList.add("hidden");
      cloudCard.classList.add("hidden");
      wishlistCard.classList.add("hidden");
      notesCard && notesCard.classList.add("hidden");
      notesNoPair && notesNoPair.classList.remove("hidden");
      noPairCard.classList.remove("hidden");
      return;
    }

    noPairCard.classList.add("hidden");
    wishCard && wishCard.classList.remove("hidden");
    pairCard.classList.remove("hidden");
    cloudCard.classList.remove("hidden");
    wishlistCard.classList.remove("hidden");
    notesCard && notesCard.classList.remove("hidden");
    notesNoPair && notesNoPair.classList.add("hidden");

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

    if (anniversaryBanner) {
      if (stats && !stats.future && (stats.is_anniversary_today || stats.days_until_next <= 7)) {
        const nextYear = stats.years + 1;
        const d = stats.days_until_next;
        let bannerText;
        if (stats.is_anniversary_today) {
          const yearsWord = pluralRu(stats.years, ["год", "года", "лет"]);
          bannerText = `🎉 Сегодня ваша годовщина — ${stats.years} ${yearsWord} вместе!`;
        } else if (d === 1) {
          const yearsWord = pluralRu(nextYear, ["год", "года", "лет"]);
          bannerText = `💍 Завтра годовщина — исполнится ${nextYear} ${yearsWord} вместе!`;
        } else {
          const daysWord = pluralRu(d, ["день", "дня", "дней"]);
          const yearsWord = pluralRu(nextYear, ["год", "года", "лет"]);
          bannerText = `🗓 До годовщины ${d} ${daysWord} — исполнится ${nextYear} ${yearsWord} вместе`;
        }
        anniversaryBanner.textContent = bannerText;
        anniversaryBanner.classList.remove("hidden");
      } else {
        anniversaryBanner.classList.add("hidden");
      }
    }

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

  const PRIORITY_COLORS = { high: "#ff3b30", medium: "#34c759", low: "#007aff" };
  const PRIORITY_LABELS = { high: "Очень хочу", medium: "Хочу", low: "Несрочно" };

  function makeWishlistItemHTML(item, canEdit) {
    const titleHtml = sanitizeText(item.title || "");
    const hasLink = !!item.url;
    const discussUrl = !canEdit ? buildPartnerDiscussLink(item) : null;
    const priority = item.priority || "medium";
    const dotColor = PRIORITY_COLORS[priority] || PRIORITY_COLORS.medium;

    const priorityDot = canEdit
      ? `<span class="wl-priority-dot wl-priority-clickable" data-priority="${priority}" style="background:${dotColor}" title="${PRIORITY_LABELS[priority]}"></span>`
      : `<span class="wl-priority-dot" style="background:${dotColor}" title="${PRIORITY_LABELS[priority]}"></span>`;

    const linkPart = hasLink
      ? `<button class="wl-link-btn" data-url="${encodeURI(
          item.url
        )}">Открыть</button>`
      : canEdit
      ? `<button class="wish-add-link" type="button">Добавить ссылку</button>`
      : "";

    const discussPart = discussUrl
      ? `<button class="wl-chat-btn" data-chat-url="${discussUrl}">Обсудить</button>`
      : "";

    const deleteReveal = canEdit
      ? `<button class="wl-delete-reveal" type="button" aria-label="Удалить">✕</button>`
      : "";

    return `
      <div class="wl-swipe-track">
        <div class="wl-swipe-content">
          <div class="wl-main">
            ${priorityDot}
            <div class="wl-text">
              <div class="wl-title wish-title">${titleHtml}</div>
            </div>
            <div class="wl-actions">
              ${linkPart}
              ${discussPart}
            </div>
          </div>
        </div>
        ${deleteReveal}
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
        attachWishSwipe(li);
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

  // === NOTES РЕНДЕР =============================================

  function makeNoteItemHTML(note) {
    const textHtml = sanitizeText(note.text || "");
    const authorLabel = note.is_mine ? "Я" : getPartnerDisplayName();
    const dateStr = note.created_at ? formatDate(note.created_at) : "";
    const deleteReveal = note.is_mine
      ? `<button class="wl-delete-reveal" type="button" aria-label="Удалить">✕</button>`
      : "";

    return `
      <div class="wl-swipe-track">
        <div class="wl-swipe-content">
          <div class="note-main">
            <div class="note-text">${textHtml}</div>
            <div class="note-meta">
              <span class="note-author-badge${note.is_mine ? " note-mine" : ""}">${authorLabel}</span>
              <span class="note-date">${dateStr}</span>
            </div>
          </div>
        </div>
        ${deleteReveal}
      </div>
    `;
  }

  function renderNotes() {
    if (!notesListEl || !notesEmptyEl) return;

    notesListEl.innerHTML = "";
    if (!state.notes || state.notes.length === 0) {
      notesEmptyEl.classList.remove("hidden");
    } else {
      notesEmptyEl.classList.add("hidden");
      state.notes.forEach((note) => {
        const li = document.createElement("li");
        li.className = "wl-item";
        li.dataset.id = note.id;
        li.innerHTML = makeNoteItemHTML(note);
        if (note.is_mine) attachWishSwipe(li);
        notesListEl.appendChild(li);
      });
    }

    requestAnimationFrame(updateNotesScrollHeight);
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
      state.notes = data.notes || [];

      if (myListBlock && partnerListBlock) {
        myListBlock.classList.add("hidden");
        partnerListBlock.classList.remove("hidden");
      }
      renderTabs();
      renderPairBlock();
      renderWishlist();
      renderNotes();
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

  // свайп-удаление желания
  function attachWishSwipe(li) {
    const track = li.querySelector(".wl-swipe-track");
    if (!track) return;
    const REVEAL_WIDTH = 68;
    let startX = 0, startY = 0, currentX = 0, swiping = false, dirLocked = false;

    function snapOpen() {
      track.style.transition = "transform 0.22s ease";
      track.style.transform = `translateX(-${REVEAL_WIDTH}px)`;
      li.classList.add("wl-swiped");
    }
    function snapClose() {
      track.style.transition = "transform 0.22s ease";
      track.style.transform = "translateX(0)";
      li.classList.remove("wl-swiped");
    }

    li._snapClose = snapClose;

    li.addEventListener("touchstart", (e) => {
      document.querySelectorAll(".wl-swiped").forEach((el) => {
        if (el !== li && el._snapClose) el._snapClose();
      });
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      currentX = li.classList.contains("wl-swiped") ? -REVEAL_WIDTH : 0;
      swiping = false;
      dirLocked = false;
      track.style.transition = "none";
    }, { passive: true });

    li.addEventListener("touchmove", (e) => {
      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;
      if (!dirLocked) {
        if (Math.abs(dy) > Math.abs(dx)) return;
        dirLocked = true;
      }
      swiping = true;
      const base = li.classList.contains("wl-swiped") ? -REVEAL_WIDTH : 0;
      currentX = Math.min(0, Math.max(-REVEAL_WIDTH, base + dx));
      track.style.transform = `translateX(${currentX}px)`;
    }, { passive: true });

    li.addEventListener("touchend", () => {
      if (!swiping) return;
      if (currentX < -REVEAL_WIDTH / 2) snapOpen();
      else snapClose();
    });
  }

  // подтверждение удаления через нативный confirm
  async function showWishDeleteConfirm(id, li) {
    const track = li.querySelector(".wl-swipe-track");
    function snapClose() {
      if (track) { track.style.transition = "transform 0.22s ease"; track.style.transform = "translateX(0)"; }
      li.classList.remove("wl-swiped");
    }
    const item = state.my_wishlist.find((i) => i.id === id);
    const title = item ? item.title : "";
    if (!confirm(`Точно удалить желание: «${title}»?`)) {
      snapClose();
      return;
    }
    try {
      await apiPost("/api/wishlist/delete", { user, item_id: id });
      state.my_wishlist = state.my_wishlist.filter((i) => i.id !== id);
      renderWishlist();
    } catch (err) {
      console.error(err);
      showError("Ошибка удаления: " + err.message);
      snapClose();
    }
  }

  // клики по моему wishlist
  if (myWishlistEl) {
    myWishlistEl.addEventListener("click", async (e) => {
      const li = e.target.closest("li");
      if (!li) return;
      const id = parseInt(li.dataset.id, 10);
      if (!id) return;

      // удаление через свайп
      if (e.target.closest(".wl-delete-reveal")) {
        showWishDeleteConfirm(id, li);
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

  // выпадающий список приоритетов
  function showPriorityDropdown(dot, itemId) {
    // закрыть уже открытый
    const existing = document.querySelector(".wl-priority-dropdown");
    if (existing) existing.remove();

    const dropdown = document.createElement("div");
    dropdown.className = "wl-priority-dropdown";

    const options = [
      { value: "high", label: "Очень хочу", color: PRIORITY_COLORS.high },
      { value: "medium", label: "Хочу", color: PRIORITY_COLORS.medium },
      { value: "low", label: "Несрочно", color: PRIORITY_COLORS.low },
    ];

    options.forEach((opt) => {
      const row = document.createElement("div");
      row.className = "wl-priority-option";
      row.innerHTML = `<span class="wl-priority-dot-small" style="background:${opt.color}"></span> ${opt.label}`;
      row.addEventListener("click", async (e) => {
        e.stopPropagation();
        dropdown.remove();
        try {
          await apiPost("/api/wishlist/set_priority", { user, item_id: itemId, priority: opt.value });
          const item = state.my_wishlist.find((i) => i.id === itemId);
          if (item) item.priority = opt.value;
          renderWishlist();
          haptic("select");
        } catch (err) {
          console.error(err);
          showError("Ошибка смены приоритета: " + err.message);
        }
      });
      dropdown.appendChild(row);
    });

    // позиционируем рядом с точкой
    const rect = dot.getBoundingClientRect();
    dropdown.style.position = "fixed";
    dropdown.style.left = rect.left + "px";
    dropdown.style.top = (rect.bottom + 4) + "px";
    dropdown.style.zIndex = "9999";

    document.body.appendChild(dropdown);

    // закрыть при клике снаружи
    setTimeout(() => {
      const closeHandler = (ev) => {
        if (!dropdown.contains(ev.target)) {
          dropdown.remove();
          document.removeEventListener("click", closeHandler, true);
        }
      };
      document.addEventListener("click", closeHandler, true);
    }, 0);
  }

  if (myWishlistEl) {
    myWishlistEl.addEventListener("click", (e) => {
      const dot = e.target.closest(".wl-priority-clickable");
      if (!dot) return;
      const li = dot.closest("li");
      if (!li) return;
      const id = parseInt(li.dataset.id, 10);
      if (!id) return;
      e.stopPropagation();
      showPriorityDropdown(dot, id);
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

  // === ЗАМЕТКИ =================================================

  if (notesAddForm && notesInput) {
    notesAddForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = notesInput.value.trim();
      if (!text) return;

      try {
        const data = await apiPost("/api/notes/add", { user, text });
        state.notes.unshift(data.note);
        notesInput.value = "";
        renderNotes();
        haptic("success");
      } catch (err) {
        console.error(err);
        showError("Не удалось добавить заметку: " + err.message);
        haptic("error");
      }
    });
  }

  if (notesListEl) {
    notesListEl.addEventListener("click", async (e) => {
      if (!e.target.closest(".wl-delete-reveal")) return;
      const li = e.target.closest("li");
      if (!li) return;
      const id = parseInt(li.dataset.id, 10);
      if (!id) return;

      const note = state.notes.find((n) => n.id === id);
      const preview = note ? note.text.substring(0, 40) : "";
      const track = li.querySelector(".wl-swipe-track");

      if (!confirm(`Удалить заметку: «${preview}»?`)) {
        if (track) { track.style.transition = "transform 0.22s ease"; track.style.transform = "translateX(0)"; }
        li.classList.remove("wl-swiped");
        return;
      }

      try {
        await apiPost("/api/notes/delete", { user, note_id: id });
        state.notes = state.notes.filter((n) => n.id !== id);
        renderNotes();
      } catch (err) {
        console.error(err);
        showError("Ошибка удаления: " + err.message);
      }
    });
  }

  // === СОРТИРОВКА WISHLIST =====================================

  const sortDateBtn = document.getElementById("sort-date-btn");
  const sortTitleBtn = document.getElementById("sort-title-btn");
  const sortPriorityBtn = document.getElementById("sort-priority-btn");
  const filterToggleBtn = document.getElementById("filter-toggle-btn");
  const filterLabel = document.getElementById("filter-label");
  const sortBar = document.querySelector(".wl-sort-bar");

  const FILTER_LABELS = {
    priority: { desc: "сначала важные", asc: "сначала несрочные" },
    title:    { asc:  "сначала А-Я",   desc: "сначала Я-А" },
    date:     { desc: "сначала новые",  asc:  "сначала старые" },
  };

  function updateFilterLabel() {
    if (filterLabel) {
      filterLabel.textContent = FILTER_LABELS[sortField]?.[sortDir] || "";
    }
  }

  const SORT_LABELS = {
    priority: { desc: "(важные)", asc: "(несрочные)" },
    title:    { asc:  "(А-Я)",    desc: "(Я-А)" },
    date:     { desc: "(новые)",  asc:  "(старые)" },
  };

  function updateSortUI() {
    [sortDateBtn, sortTitleBtn, sortPriorityBtn].forEach((btn) => {
      if (!btn) return;
      const field = btn.dataset.field;
      const arrow = btn.querySelector(".sort-arrow");
      const isActive = field === sortField;
      btn.classList.toggle("wl-sort-active", isActive);
      if (arrow) {
        const dir = isActive ? sortDir : (field === "title" ? "asc" : "desc");
        arrow.textContent = SORT_LABELS[field]?.[dir] || "";
      }
    });
  }

  function closeSortBar() {
    if (!sortBar) return;
    sortBar.classList.add("hidden");
    if (filterToggleBtn) filterToggleBtn.classList.remove("wl-filter-active");
  }

  function handleSortClick(field) {
    if (sortField === field) {
      sortDir = sortDir === "asc" ? "desc" : "asc";
    } else {
      sortField = field;
      sortDir = field === "date" || field === "priority" ? "desc" : "asc";
    }
    updateSortUI();
    updateFilterLabel();
    renderWishlist();
    haptic("select");
    closeSortBar();
  }

  updateFilterLabel();

  if (filterToggleBtn && sortBar) {
    filterToggleBtn.addEventListener("click", () => {
      const isOpen = !sortBar.classList.contains("hidden");
      if (isOpen) {
        closeSortBar();
      } else {
        sortBar.classList.remove("hidden");
        filterToggleBtn.classList.add("wl-filter-active");
      }
      haptic("light");
    });
  }

  if (sortDateBtn) sortDateBtn.addEventListener("click", () => handleSortClick("date"));
  if (sortTitleBtn) sortTitleBtn.addEventListener("click", () => handleSortClick("title"));
  if (sortPriorityBtn) sortPriorityBtn.addEventListener("click", () => handleSortClick("priority"));

  // старт
  init();
})();