(function () {
  const root = document.documentElement;
  const canEdit = document.body.dataset.canEdit !== "false";
  const canManage = document.body.dataset.canManage !== "false";

  function applyTheme(theme) {
    root.dataset.theme = theme;
    localStorage.setItem("lm_theme", theme);
  }

  const savedTheme = localStorage.getItem("lm_theme") || "light";
  applyTheme(savedTheme);

  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      applyTheme(root.dataset.theme === "dark" ? "light" : "dark");
    });
  }

  function applySidebarState() {
    const collapsed = localStorage.getItem("lm_sidebar_collapsed") === "true";
    document.body.classList.toggle("sidebar-collapsed", collapsed);
  }

  applySidebarState();
  document.querySelectorAll("[data-sidebar-toggle]").forEach((button) => {
    button.addEventListener("click", function () {
      const next = !(localStorage.getItem("lm_sidebar_collapsed") === "true");
      localStorage.setItem("lm_sidebar_collapsed", String(next));
      applySidebarState();
    });
  });

  const filtersForm = document.getElementById("filtersForm");
  if (filtersForm) {
    const section = filtersForm.dataset.section || "default";
    const key = "lm_filters_" + section;
    const currentParams = new URLSearchParams(window.location.search);

    if (!currentParams.has("q") && !currentParams.has("status") && !currentParams.has("responsible")) {
      const saved = JSON.parse(localStorage.getItem(key) || "{}");
      const hasSaved = saved.q || saved.status || saved.responsible;
      if (hasSaved) {
        const target = new URL(window.location.href);
        target.searchParams.set("section", section);
        ["q", "status", "responsible"].forEach((name) => {
          if (saved[name]) target.searchParams.set(name, saved[name]);
        });
        window.location.replace(target.toString());
      }
    }

    filtersForm.addEventListener("submit", function () {
      const data = new FormData(filtersForm);
      localStorage.setItem(key, JSON.stringify({
        q: data.get("q") || "",
        status: data.get("status") || "",
        responsible: data.get("responsible") || "",
      }));
    });

    const reset = document.getElementById("resetFilters");
    if (reset) {
      reset.addEventListener("click", function () {
        localStorage.removeItem(key);
      });
    }
  }

  function sortTable(table, columnIndex, direction) {
    const tbody = table.tBodies[0];
    const rows = Array.from(tbody.querySelectorAll("tr")).filter((row) => !row.querySelector(".empty"));

    rows.sort((a, b) => {
      const aCell = a.children[columnIndex];
      const bCell = b.children[columnIndex];
      const aValue = (aCell?.dataset.sort || aCell?.innerText || "").trim();
      const bValue = (bCell?.dataset.sort || bCell?.innerText || "").trim();
      const aNum = Number(aValue.replace(",", "."));
      const bNum = Number(bValue.replace(",", "."));

      let result;
      if (!Number.isNaN(aNum) && !Number.isNaN(bNum) && aValue !== "" && bValue !== "") {
        result = aNum - bNum;
      } else {
        result = aValue.localeCompare(bValue, "ru", { numeric: true, sensitivity: "base" });
      }
      return direction === "asc" ? result : -result;
    });

    rows.forEach((row) => tbody.appendChild(row));
  }

  document.querySelectorAll(".sortable-table").forEach((table) => {
    table.querySelectorAll("thead th").forEach((th, index) => {
      if (th.dataset.noSort === "true") return;
      th.classList.add("sortable");
      th.addEventListener("click", function () {
        const current = th.dataset.direction === "asc" ? "desc" : "asc";
        table.querySelectorAll("th").forEach((x) => {
          x.classList.remove("sort-asc", "sort-desc");
          delete x.dataset.direction;
        });
        th.dataset.direction = current;
        th.classList.add(current === "asc" ? "sort-asc" : "sort-desc");
        sortTable(table, index, current);
      });
    });
  });


  function initResizableColumns(table) {
    const headers = Array.from(table.querySelectorAll("thead th"));
    if (!headers.length) return;

    const tableKey = "lm_col_widths_" + (table.dataset.tableId || window.location.pathname + "_" + (new URLSearchParams(window.location.search).get("section") || "default"));
    const savedWidths = JSON.parse(localStorage.getItem(tableKey) || "{}");

    let colgroup = table.querySelector("colgroup");
    if (!colgroup) {
      colgroup = document.createElement("colgroup");
      headers.forEach(() => colgroup.appendChild(document.createElement("col")));
      table.insertBefore(colgroup, table.firstChild);
    }

    const cols = Array.from(colgroup.children);

    function currentWidths() {
      return headers.map((th, index) => {
        const saved = Number(savedWidths[index]);
        return saved > 0 ? saved : Math.max(80, Math.round(th.getBoundingClientRect().width));
      });
    }

    function applyWidths(widths) {
      let total = 0;
      widths.forEach((width, index) => {
        const px = Math.max(70, Math.round(width));
        total += px;
        if (cols[index]) cols[index].style.width = px + "px";
      });
      table.style.width = Math.max(total, table.parentElement.clientWidth) + "px";
    }

    applyWidths(currentWidths());

    headers.forEach((th, index) => {
      if (th.querySelector(".col-resizer")) return;
      th.classList.add("resizable-th");
      const handle = document.createElement("span");
      handle.className = "col-resizer";
      handle.title = "Потяни, чтобы изменить ширину столбца";
      th.appendChild(handle);

      handle.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
      });

      handle.addEventListener("dblclick", function (event) {
        event.preventDefault();
        event.stopPropagation();
        delete savedWidths[index];
        localStorage.setItem(tableKey, JSON.stringify(savedWidths));
        table.style.width = "";
        cols[index].style.width = "";
        applyWidths(currentWidths());
      });

      handle.addEventListener("pointerdown", function (event) {
        event.preventDefault();
        event.stopPropagation();

        const startX = event.clientX;
        const widths = currentWidths();
        const startWidth = widths[index];
        document.body.classList.add("resizing-column");
        handle.setPointerCapture(event.pointerId);

        function onMove(moveEvent) {
          const nextWidth = Math.max(70, startWidth + moveEvent.clientX - startX);
          widths[index] = nextWidth;
          applyWidths(widths);
        }

        function onUp() {
          widths.forEach((width, i) => savedWidths[i] = Math.round(width));
          localStorage.setItem(tableKey, JSON.stringify(savedWidths));
          document.body.classList.remove("resizing-column");
          handle.removeEventListener("pointermove", onMove);
          handle.removeEventListener("pointerup", onUp);
          handle.removeEventListener("pointercancel", onUp);
        }

        handle.addEventListener("pointermove", onMove);
        handle.addEventListener("pointerup", onUp);
        handle.addEventListener("pointercancel", onUp);
      });
    });
  }

  document.querySelectorAll(".resizable-table").forEach(initResizableColumns);

  const modal = document.getElementById("detailModal");
  const modalTitle = document.getElementById("modalTitle");
  const modalDetails = document.getElementById("modalDetails");
  const modalActions = document.getElementById("modalActions");

  function normalizeHeader(text) {
    return (text || "").replace(/\s+/g, " ").trim();
  }

  function collectEditableFields(row) {
    const table = row.closest("table");
    const headers = Array.from(table.querySelectorAll("thead th"));
    const cells = Array.from(row.children);
    return headers.map((headerCell, index) => {
      const normalizedHeader = normalizeHeader(headerCell.innerText);
      const normalizedLower = normalizedHeader.toLowerCase();
      const cell = cells[index];
      if (!cell || !normalizedHeader) return null;
      if (headerCell?.dataset.detailExclude === "true") return null;
      if (headerCell?.classList.contains("actions-col")) return null;
      if (normalizedLower.includes("действ")) return null;

      return {
        label: normalizedHeader,
        field: headerCell.dataset.field || "",
        input: headerCell.dataset.input || "text",
        value: cell.dataset.value ?? cell.innerText.trim(),
        readonly: !headerCell.dataset.field,
      };
    }).filter(Boolean);
  }

  function renderView(fields) {
    modalDetails.innerHTML = "";
    fields.forEach((field) => {
      const block = document.createElement("div");
      block.className = "detail-item";
      const label = document.createElement("span");
      label.innerText = field.label;
      const value = document.createElement("strong");
      if (field.input === "checkbox") {
        value.innerText = field.value === "true" ? "да" : "нет";
      } else {
        value.innerText = field.value || "—";
      }
      block.appendChild(label);
      block.appendChild(value);
      modalDetails.appendChild(block);
    });
  }

  function renderEditForm(fields, updateUrl) {
    modalDetails.innerHTML = "";
    const form = document.createElement("form");
    form.method = "post";
    form.action = updateUrl;
    form.className = "detail-grid detail-edit-form";
    form.id = "modalEditForm";

    fields.forEach((field) => {
      const block = document.createElement("label");
      block.className = "detail-edit-item";
      const label = document.createElement("span");
      label.innerText = field.label;
      block.appendChild(label);

      if (field.readonly) {
        const readonly = document.createElement("strong");
        readonly.innerText = field.value || "—";
        block.appendChild(readonly);
        form.appendChild(block);
        return;
      }

      let input;
      if (field.input === "textarea") {
        input = document.createElement("textarea");
      } else {
        input = document.createElement("input");
        input.type = field.input === "checkbox" ? "checkbox" : field.input;
      }

      input.name = field.field;
      if (field.input === "checkbox") {
        input.value = "true";
        input.checked = field.value === "true";
        block.classList.add("detail-edit-checkbox");
      } else {
        input.value = field.value || "";
      }
      block.appendChild(input);
      form.appendChild(block);
    });

    modalDetails.appendChild(form);
  }

  function openModal(row) {
    if (!modal || !modalDetails) return;
    modalTitle.innerText = row.dataset.title || "Карточка объекта";
    const fields = collectEditableFields(row);
    const updateUrl = row.dataset.updateUrl;
    const deleteUrl = row.dataset.deleteUrl;

    renderView(fields);

    if (modalActions) {
      modalActions.innerHTML = "";

      if (updateUrl && canEdit) {
        const editButton = document.createElement("button");
        editButton.type = "button";
        editButton.className = "button secondary";
        editButton.innerText = "Редактировать";
        editButton.addEventListener("click", function () {
          renderEditForm(fields, updateUrl);
          modalActions.innerHTML = "";

          const saveButton = document.createElement("button");
          saveButton.type = "submit";
          saveButton.className = "button";
          saveButton.innerText = "Сохранить";
          saveButton.setAttribute("form", "modalEditForm");

          const cancelButton = document.createElement("button");
          cancelButton.type = "button";
          cancelButton.className = "button secondary";
          cancelButton.innerText = "Отмена";
          cancelButton.addEventListener("click", function () {
            renderView(fields);
            openModal(row);
          });

          modalActions.appendChild(saveButton);
          modalActions.appendChild(cancelButton);
        });
        modalActions.appendChild(editButton);
      }

      if (deleteUrl && canManage) {
        const form = document.createElement("form");
        form.method = "post";
        form.action = deleteUrl;
        form.onsubmit = function () {
          return confirm("Удалить запись?");
        };

        const button = document.createElement("button");
        button.type = "submit";
        button.className = "danger";
        button.innerText = "Удалить запись";

        form.appendChild(button);
        modalActions.appendChild(form);
      }
    }

    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
  }

  document.querySelectorAll(".clickable-row").forEach((row) => {
    row.addEventListener("click", function (event) {
      if (event.target.closest("button, a, form, input, select, textarea")) return;
      openModal(row);
    });
  });

  document.querySelectorAll("[data-modal-close]").forEach((el) => {
    el.addEventListener("click", function () {
      modal.classList.remove("open");
      modal.setAttribute("aria-hidden", "true");
    });
  });
})();
