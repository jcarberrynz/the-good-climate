(function () {
  "use strict";

  const FAV_KEY = "goodNewsFavorites";
  const grid = document.getElementById("story-grid");
  const tabsNav = document.getElementById("tabs");
  const emptyState = document.getElementById("empty-state");
  const updatedLine = document.getElementById("updated-line");
  const favCount = document.getElementById("fav-count");

  let allStories = [];
  let activeFilter = "all";

  function loadFavorites() {
    try {
      const raw = localStorage.getItem(FAV_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveFavorites(favs) {
    try {
      localStorage.setItem(FAV_KEY, JSON.stringify(favs));
    } catch (e) {
      /* localStorage unavailable; favorites just won't persist */
    }
  }

  function isFavorite(link) {
    return loadFavorites().includes(link);
  }

  function toggleFavorite(link) {
    const favs = loadFavorites();
    const idx = favs.indexOf(link);
    if (idx === -1) {
      favs.push(link);
    } else {
      favs.splice(idx, 1);
    }
    saveFavorites(favs);
    updateFavCount();
  }

  function updateFavCount() {
    favCount.textContent = String(loadFavorites().length);
  }

  function formatDate(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    } catch (e) {
      return "";
    }
  }

  function formatUpdated(iso, count) {
    if (!iso) return "";
    const d = new Date(iso);
    const dateStr = d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
    const timeStr = d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
    return `Updated ${dateStr} at ${timeStr} · ${count} stories · refreshes every 3 days`;
  }

  function cardTemplate(story) {
    const fav = isFavorite(story.link);
    const card = document.createElement("article");
    card.className = "card";
    card.dataset.category = story.category;
    card.dataset.link = story.link;

    card.innerHTML = `
      <div class="card-top">
        <span class="category-pill">${escapeHtml(story.category)}</span>
        <button class="fav-btn" aria-pressed="${fav}" aria-label="Save story" title="Save story">
          ${fav ? "★" : "☆"}
        </button>
      </div>
      <h2><a href="${escapeAttr(story.link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(story.title)}</a></h2>
      <p class="card-meta">${escapeHtml(story.source)} · ${formatDate(story.published)}</p>
    `;

    const btn = card.querySelector(".fav-btn");
    btn.addEventListener("click", () => {
      toggleFavorite(story.link);
      const nowFav = isFavorite(story.link);
      btn.setAttribute("aria-pressed", String(nowFav));
      btn.textContent = nowFav ? "★" : "☆";
      if (activeFilter === "favorites") {
        render();
      }
    });

    return card;
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escapeAttr(str) {
    return escapeHtml(str);
  }

  function render() {
    grid.innerHTML = "";
    let list = allStories;

    if (activeFilter === "favorites") {
      const favs = loadFavorites();
      list = allStories.filter((s) => favs.includes(s.link));
    } else if (activeFilter !== "all") {
      list = allStories.filter((s) => s.category === activeFilter);
    }

    if (list.length === 0) {
      emptyState.hidden = false;
      emptyState.textContent =
        activeFilter === "favorites"
          ? "You haven't saved any stories yet. Click the star on a story to save it here."
          : "No stories in this category right now.";
      return;
    }

    emptyState.hidden = true;
    const frag = document.createDocumentFragment();
    list.forEach((story) => frag.appendChild(cardTemplate(story)));
    grid.appendChild(frag);
  }

  function setActiveTab(filter) {
    activeFilter = filter;
    document.querySelectorAll(".tab").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.filter === filter);
    });
    render();
  }

  tabsNav.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab");
    if (!btn) return;
    setActiveTab(btn.dataset.filter);
  });

  async function init() {
    updateFavCount();
    try {
      const res = await fetch("data/stories.json", { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to load stories.json");
      const data = await res.json();
      allStories = Array.isArray(data.stories) ? data.stories : [];
      updatedLine.textContent = formatUpdated(data.updated, data.count ?? allStories.length);
      render();
    } catch (err) {
      grid.innerHTML = "";
      updatedLine.textContent = "";
      emptyState.hidden = false;
      emptyState.textContent = "Couldn't load stories right now. Please try again later.";
      console.error(err);
    }
  }

  init();
})();
